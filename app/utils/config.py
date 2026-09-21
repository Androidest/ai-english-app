from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from typing import List, Optional, Union, Dict

class BaseConfig(BaseSettings):
    ENVIRONMENT: str
    HOST: str
    PORT: int
    CORS_ORIGINS: Union[List[str], str] = Field(default=["*"], env="CORS_ORIGINS")
    
    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    class Config:
        env_file = None
        case_sensitive = True


class DevConfig(BaseConfig):
    class Config:
        env_file = ".env.dev"
        case_sensitive = True


class ProdConfig(BaseConfig):
    class Config:
        env_file = ".env.prod"
        case_sensitive = True


config: BaseConfig = None
config_dict = {
    "dev": DevConfig,
    "prod": ProdConfig,
}

def set_config(environment: str):
    global config
    config = config_dict[environment]()