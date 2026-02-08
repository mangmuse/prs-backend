def test_settings_has_anthropic_api_key():
    """Settings에 ANTHROPIC_API_KEY 필드가 존재해야 한다."""
    from src.config import Settings

    settings = Settings()
    assert hasattr(settings, "ANTHROPIC_API_KEY")
