from pydantic import BaseModel, ConfigDict, Field


class DiversityBucket(BaseModel):
    """
    This is a category bucket.
    Plan the number of items and a concrete category to guide item generation for this set."""

    category: str = Field(min_length=1)
    desc: str = Field(min_length=1, description="A more precise description or guide for this category.")
    count: int = Field(ge=1)


class DiversityPlan(BaseModel):
    """
    This is a diversity plan to guide item generation to make the items more diverse.
    The plan consists of a list of category buckets, each with a different category, description and number of items.
    """

    buckets: list[DiversityBucket] = Field(min_length=1)