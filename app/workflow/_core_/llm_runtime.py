from typing import Any
import re
from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import Runnable
import threading

from app.workflow._core_.llm_config import LLMConfig

class LLMRuntime:
    """This is used to be passed to a workflow graph through a context."""

    def __init__(self, config: LLMConfig):
        self.config = config
        self._models: dict[tuple, BaseChatModel] = {}
        self.lock_model = threading.Lock()

    def get_model(
        self,
        *,
        temperature: float | None = None,
        **overrides: Any,
    ) -> BaseChatModel:
        
        """build a model or retrieve it from the cache"""

        if temperature is not None:
            overrides["temperature"] = temperature
            
        model_kargs = self.config.model_dump()
        model_kargs.update(overrides)
        del model_kargs['alias']

        if model_kargs['model_provider'] == 'deepseek':
            # deepseek does not support tools calling when using 'thinking'(by default)
            model_kargs['extra_body'] = {"thinking": {"type": "disabled"}}

        # generate a unique key for caching the model 
        key = tuple(
            sorted(
                (k,str(v)) for k,v in model_kargs.items()
            )
        )

        with self.lock_model:
            if key not in self._models:
                self._models[key] = init_chat_model(**model_kargs)

            return self._models[key]

    def validate(self):
        try:
            model = self.get_model()
            model.invoke("ping")
        except Exception as e:
            raise Exception(self._classify_invoke_error(e))

    @staticmethod
    def _classify_invoke_error(e: Exception) -> str:
        name = type(e).__name__.lower()
        msg = str(e)
        low = msg.lower()

        if "authentication" in name or "permission" in name or re.search(r"\b(401|403)\b", msg) \
                or "invalid api key" in low or "incorrect api key" in low:
            return "Invalid API key."
        if "notfound" in name or re.search(r"\b404\b", msg) or "model not found" in low \
                or "does not exist" in low:
            return "Invalid model or url."
        if "connection" in name or "timeout" in name or "connect" in low or "timeout" in low:
            return "Timeout or Connection error! Please check the `Base Url` or your network."
        
        return msg

if __name__ == "__main__":
    #region init LLMRuntime
    # ====================================================================
    config = LLMConfig(
        alias="ds",
        model_provider="deepseek",
        model="deepseek-flash",
        base_url="https://api.deepseek.com",
        api_key="sk-1c3d6fc60c2649a9bdcfa3982af93250",
    )
    runtime = LLMRuntime(config=config)

    #endregion init LLMRuntime

    #region test get_model
    # ====================================================================

    llm = runtime.get_model(temperature=1)
    o = llm.invoke('Hello')
    print(o.content)

    #endregion test get_model
 
    
