from enum import Enum


class ValidStatus(Enum):
    """Routing status produced by a validation node."""

    SUCCESS = "success"
    FAIL = "fail"
    PENDING_BATCH = "pending_batch"
