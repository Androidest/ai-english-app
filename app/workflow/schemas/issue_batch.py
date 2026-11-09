from pydantic import BaseModel, Field


class Issue(BaseModel):
    uid: str = Field(description="The UID of the sentence with a grammar error.")
    reason: str = Field(
        description="A short reason describing the grammar error in this sentence."
    )


class IssueBatch(BaseModel):
    issues: list[Issue] = Field(
        description="The list of problematic sentences with uid and reason. Empty if none.",
    )