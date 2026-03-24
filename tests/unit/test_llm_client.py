import pytest

from knowledge_core.ports.llm_port import LLMPort


class TestLLMPort:
    def test_llm_port_is_abstract(self):
        with pytest.raises(TypeError, match="abstract"):
            LLMPort()  # type: ignore[abstract]
