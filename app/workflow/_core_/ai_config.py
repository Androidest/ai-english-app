from pydantic import BaseModel, Field

class AIConfig(BaseModel):
    editing: bool = Field(default=False, exclude=True)
    error: str = Field(default="", exclude=True)
    id: str = Field(default="", exclude=True)
    is_new: bool = Field(default=False, exclude=True)

    def validate_to_error(self):
        params = self.model_dump()
        for field, info in type(self).model_fields.items():
            if not info.exclude and not info.deprecated and not params[field]:
                # report the error if the field is an active field but has an empty value.
                self.error = f"{info.description} is required!"