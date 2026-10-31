from pydantic import BaseModel
from app.utils.paths import PATH_LLMS
import json
from typing import Literal
from pydantic import BaseModel

ProviderType = Literal[
        "openai", 
        "deepseek", 
        "anthropic",
        "huggingface",
        "ollama",
        "azure_openai",
        "mistralai",
        "nvidia",
    ]

class LLMConfig(BaseModel):
    alias: str
    model_provider: ProviderType
    model: str
    base_url: str
    api_key: str

if __name__ == "__main__":
    test_file_path = PATH_LLMS/"test.json"
    
    if not test_file_path.exists():
        test = LLMConfig(
            alias="test",
            model_provider="",
            model="deepseek",
            base_url="https://api.deepseek.cn/v1",
            api_key="sk-xxxx",
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


