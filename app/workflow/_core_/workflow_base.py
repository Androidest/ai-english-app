from abc import ABC, abstractmethod
from typing import Any
from pydantic import BaseModel
from pathlib import Path

from app.workflow._core_.llm_config import LLMConfig


class WorkflowBase(ABC):
    def __init__(self):
        self.graph = self._build_graph()

    @abstractmethod
    def _build_graph(self):
        raise NotImplementedError("_build_graph not implemented.")

    @abstractmethod
    def invoke(
        self,
        input_data: BaseModel,
        llm_config: LLMConfig,
        user_id: str,
        *args,
    ) -> Any:
        raise NotImplementedError("invoke not implemented.")

    @abstractmethod
    async def ainvoke(
        self,
        input_data: BaseModel,
        llm_config: LLMConfig,
        user_id: str,
    ) -> Any:
        raise NotImplementedError("ainvoke not implemented.")


    def draw_graph_png(
        self,
        path: str|Path
    ):
        if type(path) != Path:
            path = Path(path)

        if not path.parent.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
        
        png_bytes = self.graph.get_graph(xray=True).draw_mermaid_png(max_retries=5, retry_delay=2.0)
        with open(path, "wb") as f:
            f.write(png_bytes)


    def draw_graph_mermaid(self):
        print(self.graph.get_graph(xray=True).draw_mermaid())