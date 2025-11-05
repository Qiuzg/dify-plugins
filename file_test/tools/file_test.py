from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage
from dify_plugin.file.file import File
import pandas as pd
import io

class FileTestTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        print(tool_parameters)
        tmp = tool_parameters['query']
        print(tmp)
        # print(tmp.blob)
        print(pd.read_csv(io.BytesIO(tmp.blob)))
        yield self.create_json_message({
            "result": "Hello, world!"
        })
