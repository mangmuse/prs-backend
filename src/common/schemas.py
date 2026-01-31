from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelCaseModel(BaseModel):
    """API Request/Response용 camelCase 베이스 모델

    - Request: FE가 camelCase로 보내면 snake_case 필드에 매핑
    - Response: snake_case 필드를 camelCase로 직렬화
    - populate_by_name=True: snake_case도 허용 (테스트/내부용)
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
