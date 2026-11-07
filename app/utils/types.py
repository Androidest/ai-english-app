from typing import Literal

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

CEFRLevel = Literal[
    "A1",
    "A2",
    "B1",
    "B2",
    "C1",
    "C2",
]

Language = Literal[
    "English",
    "Indonesian",
    "Chinese",
    "Spanish",
]
