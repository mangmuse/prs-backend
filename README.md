# PRS Backend

프롬프트 품질 관리 및 회귀 분석 플랫폼 백엔드

## 요구사항

- Python 3.12+
- Docker
- [uv](https://docs.astral.sh/uv/) (Python 패키지 매니저)

## 개발 환경 설정

### 1. uv 설치

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. 의존성 설치

```bash
cd backend
uv sync
```

### 3. 환경 변수 설정

```bash
cp .env.example .env
```

### 4. PostgreSQL + pgvector 실행

```bash
docker-compose up -d
```

> 로컬에 PostgreSQL이 이미 실행 중이면 포트 충돌이 발생합니다.
> `brew services stop postgresql@16` 등으로 먼저 중지하세요.

### 5. DB 마이그레이션

```bash
uv run alembic upgrade head
```

### 6. 개발 서버 실행

```bash
uv run uvicorn src.main:app --reload
```

서버가 http://localhost:8000 에서 실행됩니다.

## 검증 명령어

```bash
# 테스트
uv run pytest

# 린트
uv run ruff check src/

# 포맷
uv run ruff format src/

# 타입 체크
uv run mypy src/
```

## 기술 스택

- FastAPI + SQLModel + Pydantic v2
- PostgreSQL 15 + pgvector
- Alembic (마이그레이션)
- uv (패키지 매니저)
- Ruff (린터/포매터), mypy (타입 체커)
