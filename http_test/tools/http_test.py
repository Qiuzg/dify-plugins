import re
import json
from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage
import requests
import base64
import logging
from dify_plugin.config.logger_format import plugin_logger_handler

# 使用自定义处理器设置日志
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(plugin_logger_handler)

class HttpTestTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        context = tool_parameters['file_name']
        url = tool_parameters['url']
        time_out = tool_parameters['time_out']
        query = tool_parameters['query']
        history_str = tool_parameters['history']

        # history = json.loads(history_str)
        #
        # _history = []
        # for item in history:
        #     try:
        #         if item['role'] == 'assistant':
        #             content = re.search(r'```python(.*)```', item.get('content', ''), re.DOTALL).group(1)
        #             _history.append({'role': item['role'], 'content': content})
        #         else:
        #             _history.append(item)
        #     except AttributeError:
        #         _history.append(item)
        #
        # files_list = []
        # for file in context:
        #     # 将文件内容编码为 Base64
        #     content_base64 = base64.b64encode(file.blob).decode('utf-8')
        #     files_list.append({
        #         'filename': file.filename,
        #         'content': content_base64
        #     })
        # 构建请求体

        # request_data = {
        #     'files': files_list,
        #     'input_text': query,
        #     'history': _history[0:-1] # 历史记录(可选)
        # }

        logger.info('----- start request ----- ')
        # 发送请求
        # response = requests.post(
        #     url,
        #     json=request_data,  # 使用 JSON 格式
        #     timeout=time_out,  # 5分钟超时
        #     headers={'Content-Type': 'application/json'}
        # )

        logger.info('----- request finish ----- ')
        # 检查响应状态
        # response.raise_for_status()

        # 解析结果
        # result = response.json()

        yield self.create_text_message("134")

