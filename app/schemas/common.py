from pydantic import BaseModel


class ErrorDetail(BaseModel):
    code: str
    message: str


class EnvelopeMeta(BaseModel):
    request_id: str | None = None


class ErrorEnvelope(BaseModel):
    data: dict[str, object] | None = None
    meta: EnvelopeMeta | None = None
    error: ErrorDetail | None = None
