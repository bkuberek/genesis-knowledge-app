"""Unit tests for the WebSocket handler — title generation and helpers."""

from knowledge_api.routers.websocket_handler import (
    TITLE_MAX_LENGTH,
    generate_session_title,
)


class TestGenerateSessionTitle:
    def test_short_message_returned_as_is(self):
        title = generate_session_title("Hello world")

        assert title == "Hello world"

    def test_exact_length_message_not_truncated(self):
        message = "x" * TITLE_MAX_LENGTH
        title = generate_session_title(message)

        assert title == message
        assert "..." not in title

    def test_long_message_truncated_at_word_boundary(self):
        message = "What is the average ARR for fintech companies in the database right now today"
        title = generate_session_title(message)

        assert len(title) <= TITLE_MAX_LENGTH + 3  # +3 for ellipsis
        assert title.endswith("...")
        # Should not cut in the middle of a word
        assert not title[:-3].endswith(" ")  # no trailing space before ellipsis

    def test_strips_whitespace(self):
        title = generate_session_title("  Hello world  ")

        assert title == "Hello world"

    def test_replaces_newlines_with_spaces(self):
        title = generate_session_title("Hello\nworld\ntest")

        assert title == "Hello world test"

    def test_single_long_word_truncated(self):
        message = "a" * 100
        title = generate_session_title(message)

        assert title.endswith("...")
        assert len(title) == TITLE_MAX_LENGTH + 3  # truncated + ellipsis

    def test_empty_message_returns_empty(self):
        title = generate_session_title("")

        assert title == ""

    def test_whitespace_only_returns_empty(self):
        title = generate_session_title("   ")

        assert title == ""
