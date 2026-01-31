from datetime import datetime

from pydantic import BaseModel, ConfigDict

from src.prompts.models import OutputSchemaType


class CreatePromptRequest(BaseModel):
    name: str
    description: str | None = None


class CreatePromptResponse(BaseModel):
    id: int
    name: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PromptSummary(BaseModel):
    id: int
    name: str
    description: str | None
    latest_version: int | None
    version_count: int
    created_at: datetime


class CreateVersionRequest(BaseModel):
    system_instruction: str
    user_template: str
    model: str = "gpt-4"
    temperature: float = 1.0
    output_schema: OutputSchemaType = OutputSchemaType.JSON_OBJECT
    memo: str | None = None


class VersionSummary(BaseModel):
    id: int
    version_number: int
    model: str
    memo: str | None
    user_template: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)





class VersionDetailResponse(BaseModel):
    id: int
    prompt_id: int
    version_number: int
    system_instruction: str
    user_template: str
    model: str
    temperature: float
    output_schema: OutputSchemaType
    memo: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
