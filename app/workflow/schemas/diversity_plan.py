from pydantic import BaseModel, ConfigDict, Field


class DiversityBucket(BaseModel):
    """A concrete category of the planned English sentence set."""

    model_config = ConfigDict(extra="forbid")

    category: str = Field(min_length=1)
    description: str = Field(min_length=1)
    count: int = Field(ge=1)


class DiversityPlan(BaseModel):
    """Diversity plan used to generate the requested English sentences."""

    model_config = ConfigDict(extra="forbid")

    buckets: list[DiversityBucket] = Field(min_length=1)
