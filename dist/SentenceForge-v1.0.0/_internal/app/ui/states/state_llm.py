from pathlib import Path

from app.ui.states.state_ai_base import State_AIBase 
from app.workflow._core_.llm_config import LLMConfig
from app.utils.paths import PATH_LLM

class State_LLM(State_AIBase[LLMConfig]):
    PATH_MODEL: Path = PATH_LLM
    PATH_CUR_MODEL: Path = PATH_LLM / "cur_model.txt"

    def __init__(self):
        super().__init__(LLMConfig)
     