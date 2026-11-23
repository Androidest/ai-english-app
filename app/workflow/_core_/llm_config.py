from pydantic import Field

from app.workflow._core_.ai_config import AIConfig
from app.utils.types import ProviderType

class LLMConfig(AIConfig):
    alias: str = Field(default="", description="Alias")
    model_provider: ProviderType = Field(default=ProviderType.__args__[0], description="Provider")
    model: str = Field(default="", description="Model")
    base_url: str = Field(default="", description="Base Url")
    api_key: str = Field(default="", description="API Key")

    def validate_to_error(self):
        self.error = ""
        
        if self.alias == "":
            self.error = "Alias is required"

        elif self.model == "":
            self.error = "Model is required"
            
        elif self.base_url == "":
            self.error = "Base URL is required"
            
        elif self.api_key == "":
            self.error = "API Key is required"
            
        