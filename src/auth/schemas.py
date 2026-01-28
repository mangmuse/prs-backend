from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class GuestSessionResponse(BaseModel):
    """POST /auth/guest 응답 - Notion API 명세 기준"""

    guest_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenPayload(BaseModel):
    """JWT 페이로드 구조"""

    sub: str
    type: str
    iat: datetime
    exp: datetime
