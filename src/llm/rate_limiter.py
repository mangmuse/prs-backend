import asyncio

PROVIDER_CONCURRENCY: dict[str, int] = {
    "anthropic": 5,
    "openai": 50,
    "gemini": 15,
}

_semaphores: dict[str, asyncio.Semaphore] = {}


def get_semaphore(provider: str) -> asyncio.Semaphore:
    """Provider별 Semaphore 반환 (싱글톤)."""
    if provider not in _semaphores:
        limit = PROVIDER_CONCURRENCY.get(provider, 10)
        _semaphores[provider] = asyncio.Semaphore(limit)
    return _semaphores[provider]


def extract_provider(model: str) -> str:
    """'provider/model-name'에서 provider 추출."""
    return model.split("/", 1)[0] if "/" in model else model
