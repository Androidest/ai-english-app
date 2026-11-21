# app/ui/states/state_ai_base.py
import gradio as gr
import json
from pathlib import Path
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class State_AIBase(Generic[T]):
    PATH_MODEL: Path
    PATH_CUR_MODEL: Path

    def __init__(self, model_type: type[T]):
        self._model_type: type[T] = model_type
        self.configs = gr.State(value=[])
        self.cur_llm = gr.State(value=-1)

    def load_to_outputs(self) -> tuple[list[T], int]:
        configs: list[T] = []

        if self.PATH_MODEL.exists():
            for file_path in self.PATH_MODEL.rglob("*.json"):
                with open(file_path, "r", encoding="utf-8") as f:
                    config = self._model_type.model_validate_json(f.read())
                    config.id = file_path.stem
                    configs.append(config)

            configs.sort(key=lambda x: x.id)

        if self.PATH_CUR_MODEL.exists():
            with open(self.PATH_CUR_MODEL, "r", encoding="utf-8") as f:
                cur_llm = int(f.read())
        else:
            cur_llm = 0 if len(configs) > 0 else -1

        return configs, cur_llm

    def outputs(self) -> tuple[gr.State, gr.State]:
        return (
            self.configs,
            self.cur_llm,
        )

    def save_item(self, config: T) -> None:
        if not self.PATH_MODEL.exists():
            self.PATH_MODEL.mkdir(parents=True, exist_ok=True)

        with open(f"{self.PATH_MODEL}/{config.id}.json", "w", encoding="utf-8") as f:
            json.dump(
                config.model_dump(),
                f,
                ensure_ascii=False,
                indent=4,
            )

    def save_cur_llm(self, cur_llm: int) -> None:
        with open(self.PATH_CUR_MODEL, "w", encoding="utf-8") as f:
            f.write(str(cur_llm))

    def delete_item(self, config: T) -> None:
        path = self.PATH_MODEL / f"{config.id}.json"
        if path.exists():
            path.unlink()