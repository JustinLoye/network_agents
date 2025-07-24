from pydantic import BaseModel
from typing import Literal


class ModelParams(BaseModel):
    base_url: str = "http://localhost:11434/v1"
    api_key: str = "ollama"
    model: Literal[
        "qwen3:4b",
        "llama3.2",
        "qwen2.5-coder:3b",
        "hf.co/unsloth/Qwen3-4B-GGUF:Q6_K_XL",
    ] = "qwen3:4b"
    temperature: float = 0.0