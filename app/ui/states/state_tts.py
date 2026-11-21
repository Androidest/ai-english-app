from pathlib import Path

from app.ui.states.state_ai_base import State_AIBase 
from app.workflow._core_.tts_config import TTSConfig
from app.utils.paths import PATH_TTS

class State_TTS(State_AIBase[TTSConfig]):
    PATH_MODEL: Path = PATH_TTS
    PATH_CUR_MODEL: Path = PATH_TTS / "cur_tts.txt"

    def __init__(self):
        super().__init__(TTSConfig)
     