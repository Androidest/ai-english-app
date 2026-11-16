from pydantic import BaseModel, Field
from typing import Literal

SeverityType = Literal["critical", "major", "minor"]
ConfidenceType = Literal["high", "low"]

class Issue(BaseModel):
    uid: str = Field(description="The UID of the sentence with a grammar error.")
    reason: str = Field(
        description="A reason describing each substantive defect found in this sentence."
    )
    severity: SeverityType = Field(
        description="To classify the severity of the issue."
    )
    confidence: ConfidenceType = Field(
        description="The verifiability of the defect from explicit textual evidence, not the model's subjective certainty."
    )


class IssueBatch(BaseModel):
    issues: list[Issue] = Field(
        description="The list of problematic sentences with uid and reason. Empty if none.",
    )