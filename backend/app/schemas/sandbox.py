from pydantic import BaseModel, Field


class SandboxExecuteRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=8000)
    model: str = "gemini-2.0-flash"
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    top_p: float = Field(default=0.95, ge=0.0, le=1.0)
    max_output_tokens: int = Field(default=1024, ge=1, le=8192)


class SandboxExecuteResponse(BaseModel):
    attempt_id: int
    response_text: str
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float
    latency_ms: int
    served_from_cache: bool
