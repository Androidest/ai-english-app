from typing import Annotated, TypedDict, Literal

class StreamData(TypedDict, total=False):
    """Output through stream writer"""

    type: str
    processed_count: int
