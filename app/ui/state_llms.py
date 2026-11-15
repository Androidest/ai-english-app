import gradio as gr
from app.workflow._core_.llm_config import LLMConfig
from app.utils.paths import PATH_LLMS
import json

PATH_CUR_LLM = PATH_LLMS / "cur_llm.txt"

class State_LLMs:

    def __init__(self):
        self.configs = gr.State(value=[])
        self.cur_llm = gr.State(value=-1)        

    def load_to_outputs(self) -> tuple[list[LLMConfig], int]:
        configs: list[LLMConfig] = []

        if PATH_LLMS.exists():
            for file_path in PATH_LLMS.rglob(f"*.json"):
                with open(file_path, "r", encoding="utf-8") as f:
                    config = LLMConfig.model_validate_json(f.read())
                    config.id = file_path.stem
                    configs.append(config)

            sorted(configs, key=lambda x: x.id)

        if PATH_CUR_LLM.exists():
            with open(PATH_CUR_LLM, "r", encoding="utf-8") as f:
                cur_llm = int(f.read())
        else:
            if len(configs) > 0:
                cur_llm = 0
            else:
                cur_llm = -1

        return configs, cur_llm

    def outputs(self) -> tuple[gr.State, gr.State]:
        return [
            self.configs, 
            self.cur_llm
        ]
    
    def save_item(
        self,
        config: LLMConfig
    ):
        if not PATH_LLMS.exists():
            PATH_LLMS.mkdir(parents=True, exist_ok=True)

        with open(f"{PATH_LLMS}/{config.id}.json", "w", encoding="utf-8") as f:
            json.dump(
                config.model_dump(), 
                f, 
                ensure_ascii=False, 
                indent=4
            )

    def save_cur_llm(
        self, 
        cur_llm: int
    ):
        with open(PATH_CUR_LLM, "w", encoding="utf-8") as f:
            f.write(str(cur_llm))

    def delete_item(
        self, 
        config: LLMConfig
    ):
        path = PATH_LLMS / f"{config.id}.json"
        if path.exists():
            path.unlink()
     