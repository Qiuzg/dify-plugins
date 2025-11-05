import json
import logging
from abc import ABC
from collections.abc import Generator
from decimal import Decimal
from typing import Optional, Union, cast, Any

import httpx
from dify_plugin import LargeLanguageModel
from dify_plugin.entities import I18nObject
from dify_plugin.entities.model import (
    AIModelEntity,
    FetchFrom,
    ModelType, ParameterType, ParameterRule, DefaultParameterName, ModelPropertyKey, PriceConfig,
)
from dify_plugin.entities.model.llm import (
    LLMResult, LLMResultChunk, LLMResultChunkDelta,
)
from dify_plugin.entities.model.message import (
    PromptMessage,
    PromptMessageTool,
    UserPromptMessage,
    TextPromptMessageContent,
    ImagePromptMessageContent,
    AssistantPromptMessage,
    SystemPromptMessage,
    ToolPromptMessage
)
from openai import OpenAI
from openai.types.chat import ChatCompletion

logger = logging.getLogger(__name__)


def _to_credential_kwargs(credentials: dict) -> dict:
    if credentials.get("proxy"):
        credentials_kwargs = {
            'api_key': credentials['openai_api_key'],
            'max_retries': 1,
            'base_url': credentials['openai_api_base'],
            'http_client': httpx.Client(
                proxy=credentials.get('proxy_host', "http://squid02.aiapsuat.suningbank.com:18888"), verify=False, )
        }
    else:
        credentials_kwargs = {
            'api_key': credentials['openai_api_key'],
            'max_retries': 1,
            'base_url': credentials['openai_api_base']
        }
    return credentials_kwargs


def _convert_prompt_message_to_dict(message: PromptMessage) -> dict:
    if isinstance(message, UserPromptMessage):
        message_dict = {"role": "user", "content": message.content}
    elif isinstance(message, list):
        sub_messages = []
        for message_content in message.content:
            if isinstance(message_content, TextPromptMessageContent):
                sub_message_dict = {
                    "type": "text",
                    "text": message_content.data
                }
                sub_messages.append(sub_message_dict)
            elif isinstance(message_content, ImagePromptMessageContent):
                sub_message_dict = {
                    "type": "image_url",
                    "image_url": {
                        "url": message_content.data,
                        "detail": message_content.detail.value,
                    }
                }
                sub_messages.append(sub_message_dict)
            else:
                # 暂时不会出现其他模态的数据
                pass
        message_dict = {"role": "user", "content": sub_messages}
    elif isinstance(message, AssistantPromptMessage):
        message = cast(AssistantPromptMessage, message)
        message_dict = {"role": "assistant", "content": message.content}
    elif isinstance(message, SystemPromptMessage):
        message = cast(SystemPromptMessage, message)
        if isinstance(message.content, list):
            text_contents = filter(
                lambda c: isinstance(c, TextPromptMessageContent), message.content
            )
            message.content = "".join(c.data for c in text_contents)
        message_dict = {"role": "system", "content": message.content}
    elif isinstance(message, ToolPromptMessage):
        message = cast(ToolPromptMessage, message)
        message_dict = {"role": "function", "content": message.content, "name": message.tool_call_id}
    else:
        # print(message.content)
        # print(message)
        raise ValueError(f"Got unknown type {message}")

    if message.name:
        message_dict['name'] = message.name
    return message_dict


class VolNetworkLargeLanguageModel(LargeLanguageModel, ABC):
    """
    Model class for vol_network large language model.
    """

    def _invoke(
            self,
            model: str,
            credentials: dict,
            prompt_messages: list[PromptMessage],
            model_parameters: dict,
            tools: Optional[list[PromptMessageTool]] = None,
            stop: Optional[list[str]] = None,
            stream: bool = True,
            user: Optional[str] = None,
    ) -> Union[LLMResult, Generator]:
        """
        Invoke large language model

        :param model: model name
        :param credentials: model credentials
        :param prompt_messages: prompt messages
        :param model_parameters: model parameters
        :param tools: tools for tool calling
        :param stop: stop words
        :param stream: is stream response
        :param user: unique user id
        :return: full response or stream response chunk generator result
        """
        # print(f"credentials {credentials}")
        return self._chat_generate(
            model,
            credentials=credentials,
            prompt_messages=prompt_messages,
            model_parameters=model_parameters,
            tools=tools,
            stop=stop,
            stream=stream,
            user=user
        )

    def get_num_tokens(
            self,
            model: str,
            credentials: dict,
            prompt_messages: list[PromptMessage],
            tools: Optional[list[PromptMessageTool]] = None,
    ) -> int:
        """
        Get number of tokens for given prompt messages

        :param model: model name
        :param credentials: model credentials
        :param prompt_messages: prompt messages
        :param tools: tools for tool calling
        :return:
        """
        return 0

    def validate_credentials(self, model: str, credentials: dict) -> None:
        """
        Validate model credentials

        :param model: model name
        :param credentials: model credentials
        :return:
        """
        try:
            pass
        except Exception as ex:
            # raise CredentialsValidateFailedError(str(ex))
            logger.error('Model not exist ....')

    def get_customizable_model_schema(
            self, model: str, credentials: dict
    ) -> AIModelEntity:
        """
        If your model supports fine-tuning, this method returns the schema of the base model
        but renamed to the fine-tuned model name.

        :param model: model name
        :param credentials: credentials

        :return: model schema
        """
        entity = AIModelEntity(
            model=model,
            label=I18nObject(en_US=model),
            model_type=ModelType.LLM,
            fetch_from=FetchFrom.CUSTOMIZABLE_MODEL,
            features=[],
            model_properties={
                ModelPropertyKey.CONTEXT_SIZE: int(credentials.get("context_size", "4096")),
                ModelPropertyKey.MODE: credentials.get("mode"),
            },
            parameter_rules=[
                ParameterRule(
                    name=DefaultParameterName.TEMPERATURE.value,
                    label=I18nObject(en_US="Temperature", zh_Hans="温度"),
                    help=I18nObject(
                        en_US="Kernel sampling threshold. Used to determine the randomness of the results."
                              "The higher the value, the stronger the randomness."
                              "The higher the possibility of getting different answers to the same question.",
                        zh_Hans="核采样阈值。用于决定结果随机性，取值越高随机性越强即相同的问题得到的不同答案的可能性越高。",
                    ),
                    type=ParameterType.FLOAT,
                    default=float(credentials.get("temperature", 0.7)),
                    min=0,
                    max=2,
                    precision=2,
                ),
                ParameterRule(
                    name=DefaultParameterName.TOP_P.value,
                    label=I18nObject(en_US="Top P", zh_Hans="Top P"),
                    help=I18nObject(
                        en_US="The probability threshold of the nucleus sampling method during the generation process."
                              "The larger the value is, the higher the randomness of generation will be."
                              "The smaller the value is, the higher the certainty of generation will be.",
                        zh_Hans="生成过程中核采样方法概率阈值。取值越大，生成的随机性越高；取值越小，生成的确定性越高。",
                    ),
                    type=ParameterType.FLOAT,
                    default=float(credentials.get("top_p", 1)),
                    min=0,
                    max=1,
                    precision=2,
                ),
            ],
            pricing=PriceConfig(
                input=Decimal(credentials.get("input_price", 0)),
                output=Decimal(credentials.get("output_price", 0)),
                unit=Decimal(credentials.get("unit", 0)),
                currency=credentials.get("currency", "USD"),
            ),
        )

        return entity

    def _chat_generate(
            self,
            model: str,
            credentials: dict,
            prompt_messages: list[PromptMessage],
            model_parameters: dict,
            tools: Optional[list[PromptMessageTool]] = None,
            stop: Optional[list[str]] = None,
            stream: bool = True,
            user: Optional[str] = None, ):
        logger.info(f'Credential info: {credentials}')
        if 'bot_id' in credentials:
            model = credentials['bot_id']
            credentials.pop('bot_id')
        if 'reference' in credentials:
            reference = credentials['reference']
            credentials.pop('reference')

        credentials_kwargs = _to_credential_kwargs(credentials)

        logger.info(f'credentials_kwargs: {credentials_kwargs}')
        client = OpenAI(**credentials_kwargs)

        extra_model_kwargs = {}
        if stop:
            extra_model_kwargs['stop'] = stop
        if user:
            extra_model_kwargs['user'] = user

        messages: Any = [
            _convert_prompt_message_to_dict(m) for m in prompt_messages
        ]
        response = client.chat.completions.create(
            messages=messages,
            model=model,
            stream=stream,
            **model_parameters,
            **extra_model_kwargs
        )

        if stream:
            return self._handle_chat_generate_stream_response(
                model, credentials, response, prompt_messages, reference
            )
        return self._handle_chat_generate_response(
            model, credentials, response, prompt_messages, reference
        )

    def _handle_chat_generate_response(
            self,
            model: str,
            credentials: dict,
            response: ChatCompletion,
            prompt_messages: list[PromptMessage],
    ) -> LLMResult:
        assistant_message = response.choices[0].message
        assistant_prompt_message = AssistantPromptMessage(content=assistant_message)

        if response.usage:
            prompt_token = response.usage.prompt_token
            completion_token = response.usage.completion_token
        else:
            prompt_token = self.get_num_tokens(model, prompt_messages[0].content)
            completion_token = self.get_num_tokens(model, assistant_message.content)

        usage = self._calc_response_usage(model, credentials, prompt_token, completion_token)

        result = LLMResult(
            model=response.model,
            prompt_messages=prompt_messages,
            message=assistant_prompt_message,
            usage=usage,
            system_fingerprint=response.system_fingerprint,
        )
        return result

    def _handle_chat_generate_stream_response(self, model, credentials, response, prompt_messages, reference):
        logger.info(f'_handle_chat_generate_stream_response start')
        full_assistant_content = ""
        # delta_assistant_message_function_call_storage: ChoiceDeltaFunctionCall = None
        prompt_token = 0
        completion_token = 0
        # final_took_calls = []
        final_chunk = LLMResultChunk(
            model=model,
            prompt_messages=prompt_messages,
            delta=LLMResultChunkDelta(
                index=0,
                message=AssistantPromptMessage(content="")
            )
        )

        is_reasoning_started = False

        for chunk in response:
            if len(chunk.choices) == 0:
                if chunk.usage:
                    prompt_token = chunk.usage.prompt_token
                    completion_token = chunk.usage.completion_token
                continue
            # print(chunk)
            if hasattr(chunk, 'references') and reference != 0:
                references = chunk.references
                for ref in references:
                    ref.pop('extra')
                    site_name = ref['site_name']
                    if len(site_name) > 4 and "搜索引擎-" in site_name:
                        site_name = site_name.replace("搜索引擎-", "")
                        ref['site_name'] = site_name

                if reference == "1":
                    delta_content = ("@@@" + json.dumps(references, ensure_ascii=False) + "@@@")
                elif reference == "2":
                    delta_content = ("@@@" + str(len(references)) + "@@@")
                else:
                    delta_content = None

                delta = chunk.choices[0]
                assistant_prompt_message = AssistantPromptMessage(
                    content=delta_content or "",
                    tool_calls=[]
                )
                reference_chunk = LLMResultChunk(
                    model=chunk.model,
                    prompt_messages=prompt_messages,
                    system_fingerprint=chunk.system_fingerprint,
                    delta=LLMResultChunkDelta(
                        index=delta.index,
                        message=assistant_prompt_message
                    )
                )
                yield reference_chunk

            delta = chunk.choices[0]
            # print(delta.delta)
            delta_content, is_reasoning_started = (
                self._wrap_thinking_by_reasoning_content(delta.delta, is_reasoning_started)
            )

            # print(delta_content)
            has_finish_reason = delta.finish_reason is not None

            if (
                    not has_finish_reason
                    and (delta.delta.content is None or delta.delta.content == "")
                    and delta.delta.function_call is None
                    and delta_content == ""
            ):
                continue

            assistant_prompt_message = AssistantPromptMessage(content=delta_content or "", tool_calls=[])
            logger.info(f"{assistant_prompt_message}")
            full_assistant_content += delta.delta.content or ""

            if has_finish_reason:
                final_chunk = LLMResultChunk(
                    model=chunk.model,
                    prompt_messages=prompt_messages,
                    system_fingerprint=chunk.system_fingerprint,
                    delta=LLMResultChunkDelta(
                        index=delta.index,
                        message=assistant_prompt_message,
                        finish_reason=delta.finish_reason
                    )
                )
            else:
                yield LLMResultChunk(
                    model=chunk.model,
                    prompt_messages=prompt_messages,
                    system_fingerprint=chunk.system_fingerprint,
                    delta=LLMResultChunkDelta(
                        index=delta.index,
                        message=assistant_prompt_message,
                    )
                )
        if not prompt_token:
            prompt_token = self.get_num_tokens(model, credentials, prompt_messages, [])
        if not completion_token:
            final_assistant_prompt_message = AssistantPromptMessage(content=full_assistant_content, tool_calls=[])
            completion_token = self.get_num_tokens(model, credentials, [final_assistant_prompt_message], [])

        usage = self._calc_response_usage(model, credentials, prompt_token, completion_token)
        final_chunk.delta.usage = usage
        logger.info(f"other: {final_chunk.delta}")
        yield final_chunk

    def _invoke_error_mapping(self):
        logger.error("InvokeErrorMapping Error")

    def _wrap_thinking_by_reasoning_content(self, delta: dict, is_reasoning: bool) -> tuple[str, bool]:
        """
        If the reasoning response is from delta.get("reasoning_content"), we wrap
        it with HTML think tag.

        :param delta: delta dictionary from LLM streaming response
        :param is_reasoning: is reasoning
        :return: tuple of (processed_content, is_reasoning)
        """

        if delta.content:
            content = delta.content
        else:
            content = ""

        if hasattr(delta, 'reasoning_content'):
            reasoning_content = delta.reasoning_content
        else:
            reasoning_content = None

        if reasoning_content:
            if not is_reasoning:
                content = "<think>\n" + reasoning_content
                is_reasoning = True
            else:
                content = reasoning_content
        elif is_reasoning and content:
            content = "\n</think>" + content
            is_reasoning = False
        return content, is_reasoning
