from dataclasses import dataclass
from app.workflow._commons_.llm_runtime import LLMRuntime

@dataclass(frozen=True)
class BasicWorkflowContext:
    llm_runtime: LLMRuntime
    user_id: str