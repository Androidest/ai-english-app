from typing import TypedDict, NotRequired
import json
from pydantic import BaseModel, Field

from app.utils.paths import PATH_LLMS
from app.utils.types import ProviderType

class LLMConfig(BaseModel):
    alias: str = Field(default="")
    model_provider: ProviderType = Field(default=ProviderType.__args__[0])
    model: str = Field(default="")
    base_url: str = Field(default="")
    api_key: str = Field(default="")

    editing: bool = Field(default=False, exclude=True)
    error: str = Field(default="", exclude=True)
    id: str = Field(default="", exclude=True)
    is_new: bool = Field(default=False, exclude=True)

if __name__ == "__main__":
    test_file_path = PATH_LLMS/"test.json"
    
    if not test_file_path.exists():
        test = LLMConfig(
            alias="test",
            model_provider="deepseek",
            model="deepseek",
            base_url="https://api.deepseek.cn/v1",
            api_key="sk-xxxx",
            editing=True
        )

        with open(test_file_path, "w", encoding="utf-8") as f:
            json.dump(
                test.model_dump(),
                f,
                ensure_ascii=False,  
                indent=4            
            )
    

    with open(test_file_path, "r", encoding="utf-8") as f:
        config = LLMConfig.model_validate_json(f.read())    
        print(config)


