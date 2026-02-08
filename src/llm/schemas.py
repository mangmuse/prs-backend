"""LLM 모델 관련 스키마."""

from src.common.schemas import CamelCaseModel


class ModelInfo(CamelCaseModel):
    """개별 LLM 모델 정보."""

    id: str
    display_name: str
    provider: str


class ModelsResponse(CamelCaseModel):
    """LLM 모델 목록 응답."""

    models: list[ModelInfo]


class VerifyKeyRequest(CamelCaseModel):
    """API Key 검증 요청."""

    provider: str
    api_key: str


class VerifyKeyResponse(CamelCaseModel):
    """API Key 검증 응답."""

    valid: bool
    error: str | None = None
