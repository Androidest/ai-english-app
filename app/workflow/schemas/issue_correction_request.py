from pydantic import BaseModel, Field

from app.utils.types import Language


class IssueCorrectionRequest(BaseModel):
    """
    A request used for common dual-node check-and-fix subgraph
    """

    # current processing language
    language: Language
    # State key of the current processing batches
    target_batches_key: str
    # Max correction attempts
    max_attempts: int = 2
