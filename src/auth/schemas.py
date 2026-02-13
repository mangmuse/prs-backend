from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from src.common.schemas import CamelCaseModel


class GuestSessionResponse(CamelCaseModel):
    """POST /auth/guest 응답 - Notion API 명세 기준"""

    guest_id: UUID
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_camel,
        populate_by_name=True,
    )


class TokenPayload(BaseModel):
    """JWT 페이로드 구조"""

    sub: str
    type: str
    iat: datetime
    exp: datetime


class TokenResponse(CamelCaseModel):
    """FE에 반환하는 access token 응답"""

    access_token: str


class TokenExchangeRequest(CamelCaseModel):
    """임시코드 교환 요청 (Redis에서 access token 가져올 때)"""

    code: str
