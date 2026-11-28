from pathlib import Path
import json

from app.ui.states.state_ai_base import State_AIBase 
from app.workflow._core_.tts_config import TTSConfig
from app.workflow._core_.tts_runtime import PROVIDER_REGISTRY
from app.utils.paths import PATH_TTS

class State_TTS(State_AIBase[TTSConfig]):
    PATH_MODEL: Path = PATH_TTS
    PATH_CUR_MODEL: Path = PATH_TTS / "cur_tts.txt"

    def __init__(self):
        super().__init__(TTSConfig)

    def load_to_outputs(self) -> tuple[list[TTSConfig], int]:
        configs: list[TTSConfig] = []

        # load all configs
        if self.PATH_MODEL.exists():
            for file_path in self.PATH_MODEL.rglob("*.json"):
                with open(file_path, "r", encoding="utf-8") as f:
                    params = json.load(f)
                    provider = params.get("model_provider", "")

                    if provider not in PROVIDER_REGISTRY:
                        sub_config_type = self.model_type # base type
                    else:
                        sub_config_type = PROVIDER_REGISTRY[provider].config_type # sub-type

                    config = sub_config_type.model_validate(params)
                    config.id = file_path.stem
                    configs.append(config)

            configs.sort(key=lambda x: x.id)

        # load cur tts model index
        if self.PATH_CUR_MODEL.exists():
            with open(self.PATH_CUR_MODEL, "r", encoding="utf-8") as f:
                cur_model = int(f.read())
        else:
            cur_model = 0 if len(configs) > 0 else -1

        return configs, cur_model