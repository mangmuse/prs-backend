from src.llm.security import InMemoryRateLimiter, sanitize_error_message


class TestSanitizeErrorMessage:
    def test_openai_key_is_redacted(self):
        msg = "Invalid API key: sk-proj-abc123def456ghi789"
        result = sanitize_error_message(msg)
        assert "sk-proj-abc123def456ghi789" not in result
        assert "[REDACTED]" in result

    def test_anthropic_key_is_redacted(self):
        msg = "Error with key sk-ant-api03-abcdef123456"
        result = sanitize_error_message(msg)
        assert "sk-ant-api03-abcdef123456" not in result

    def test_google_key_is_redacted(self):
        msg = "Invalid key AIzaSyABCDEF1234567890"
        result = sanitize_error_message(msg)
        assert "AIzaSyABCDEF1234567890" not in result

    def test_message_without_key_unchanged(self):
        msg = "Connection timeout"
        assert sanitize_error_message(msg) == msg


class TestInMemoryRateLimiter:
    def test_allows_requests_within_limit(self):
        limiter = InMemoryRateLimiter(max_requests=3, window_seconds=60)
        assert limiter.is_allowed("user1") is True
        assert limiter.is_allowed("user1") is True
        assert limiter.is_allowed("user1") is True

    def test_blocks_requests_exceeding_limit(self):
        limiter = InMemoryRateLimiter(max_requests=2, window_seconds=60)
        assert limiter.is_allowed("user1") is True
        assert limiter.is_allowed("user1") is True
        assert limiter.is_allowed("user1") is False

    def test_different_keys_tracked_independently(self):
        limiter = InMemoryRateLimiter(max_requests=1, window_seconds=60)
        assert limiter.is_allowed("user1") is True
        assert limiter.is_allowed("user2") is True
        assert limiter.is_allowed("user1") is False
