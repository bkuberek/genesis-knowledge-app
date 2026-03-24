"""Unit tests for the ChatAgent tool-calling loop."""

import json
from unittest.mock import AsyncMock

import pytest

from knowledge_core.domain.entity import Entity
from knowledge_core.ports.database_repository_port import DatabaseRepositoryPort
from knowledge_core.ports.llm_port import LLMPort
from knowledge_workers.llm.chat_agent import MAX_TOOL_ROUNDS, ChatAgent

# -- Fixtures ---------------------------------------------------------------


@pytest.fixture
def mock_llm():
    return AsyncMock(spec=LLMPort)


@pytest.fixture
def mock_repository():
    return AsyncMock(spec=DatabaseRepositoryPort)


@pytest.fixture
def agent(mock_llm, mock_repository):
    return ChatAgent(llm_client=mock_llm, repository=mock_repository)


# -- Tests -------------------------------------------------------------------


class TestChatAgentInit:
    def test_initializes_with_dependencies(self, mock_llm, mock_repository):
        agent = ChatAgent(
            llm_client=mock_llm,
            repository=mock_repository,
        )
        assert agent._llm is mock_llm
        assert agent._repository is mock_repository


class TestToolDefinitions:
    def test_returns_four_tools(self, agent):
        tools = agent._get_tool_definitions()
        assert len(tools) == 4

    def test_tool_names_are_correct(self, agent):
        tools = agent._get_tool_definitions()
        names = {t["function"]["name"] for t in tools}
        assert names == {
            "describe_tables",
            "query_data",
            "aggregate_data",
            "search_entities",
        }

    def test_all_tools_have_function_type(self, agent):
        tools = agent._get_tool_definitions()
        for tool in tools:
            assert tool["type"] == "function"


class TestExecuteTool:
    @pytest.mark.asyncio
    async def test_unknown_tool_returns_error(self, agent):
        tool_call = {
            "id": "call_1",
            "function": {
                "name": "nonexistent_tool",
                "arguments": {},
            },
        }
        result = await agent._execute_tool(tool_call)
        assert "error" in result
        assert "Unknown tool" in result["error"]

    @pytest.mark.asyncio
    async def test_handles_string_arguments(self, agent, mock_repository):
        mock_repository.describe_entity_schema.return_value = {
            "person": {"count": 5},
        }
        tool_call = {
            "id": "call_1",
            "function": {
                "name": "describe_tables",
                "arguments": "{}",
            },
        }
        result = await agent._execute_tool(tool_call)
        assert "person" in result

    @pytest.mark.asyncio
    async def test_handles_dict_arguments(self, agent, mock_repository):
        mock_repository.describe_entity_schema.return_value = {
            "company": {"count": 3},
        }
        tool_call = {
            "id": "call_1",
            "function": {
                "name": "describe_tables",
                "arguments": {},
            },
        }
        result = await agent._execute_tool(tool_call)
        assert "company" in result

    @pytest.mark.asyncio
    async def test_tool_exception_returns_error(self, agent, mock_repository):
        mock_repository.describe_entity_schema.side_effect = RuntimeError("DB down")
        tool_call = {
            "id": "call_1",
            "function": {
                "name": "describe_tables",
                "arguments": {},
            },
        }
        result = await agent._execute_tool(tool_call)
        assert result == {"error": "DB down"}


class TestProcessMessage:
    @pytest.mark.asyncio
    async def test_returns_text_when_no_tool_calls(self, agent, mock_llm):
        mock_llm.complete_with_tools.return_value = {
            "role": "assistant",
            "content": "Hello! How can I help you?",
        }

        result = await agent.process_message("Hi", [])
        assert result == "Hello! How can I help you?"
        mock_llm.complete_with_tools.assert_called_once()

    @pytest.mark.asyncio
    async def test_executes_tool_call_then_returns_text(self, agent, mock_llm, mock_repository):
        """LLM returns one tool call, then a text response."""
        mock_repository.describe_entity_schema.return_value = {
            "person": {"count": 10, "properties": {"name": "str"}},
        }

        tool_call_response = {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "call_abc",
                    "type": "function",
                    "function": {
                        "name": "describe_tables",
                        "arguments": {},
                    },
                },
            ],
        }
        text_response = {
            "role": "assistant",
            "content": "You have 10 person entities.",
        }
        mock_llm.complete_with_tools.side_effect = [
            tool_call_response,
            text_response,
        ]

        result = await agent.process_message("What data do I have?", [])
        assert result == "You have 10 person entities."
        assert mock_llm.complete_with_tools.call_count == 2
        mock_repository.describe_entity_schema.assert_called_once()

    @pytest.mark.asyncio
    async def test_limits_tool_rounds(self, agent, mock_llm, mock_repository):
        """When the LLM always returns tool calls, the agent caps at MAX_TOOL_ROUNDS."""
        mock_repository.describe_entity_schema.return_value = {"x": {}}

        infinite_tool_response = {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "call_loop",
                    "type": "function",
                    "function": {
                        "name": "describe_tables",
                        "arguments": {},
                    },
                },
            ],
        }
        final_response = {
            "role": "assistant",
            "content": "Forced final answer.",
        }

        # MAX_TOOL_ROUNDS tool-call responses + 1 forced text response
        mock_llm.complete_with_tools.side_effect = [infinite_tool_response] * MAX_TOOL_ROUNDS + [
            final_response
        ]

        result = await agent.process_message("loop forever", [])
        assert result == "Forced final answer."

        # MAX_TOOL_ROUNDS in the loop + 1 final call with empty tools
        expected_calls = MAX_TOOL_ROUNDS + 1
        assert mock_llm.complete_with_tools.call_count == expected_calls

    @pytest.mark.asyncio
    async def test_passes_conversation_history(self, agent, mock_llm):
        mock_llm.complete_with_tools.return_value = {
            "role": "assistant",
            "content": "Got it.",
        }

        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]
        await agent.process_message("Follow up", history)

        call_args = mock_llm.complete_with_tools.call_args
        messages = call_args.kwargs["messages"]

        # system + 2 history + 1 user = 4
        assert len(messages) == 4
        assert messages[0]["role"] == "system"
        assert messages[1] == {"role": "user", "content": "Hello"}
        assert messages[2] == {"role": "assistant", "content": "Hi there!"}
        assert messages[3] == {"role": "user", "content": "Follow up"}


class TestQueryDataTool:
    @pytest.mark.asyncio
    async def test_query_entities_called_correctly(self, agent, mock_repository):
        entity = Entity(
            name="Acme Corp",
            canonical_name="acme_corp",
            type="company",
            properties={"industry": "tech"},
        )
        mock_repository.query_entities.return_value = [entity]

        tool_call = {
            "id": "call_q",
            "function": {
                "name": "query_data",
                "arguments": {
                    "entity_type": "company",
                    "limit": 10,
                },
            },
        }
        result = await agent._execute_tool(tool_call)
        assert result["count"] == 1
        assert result["results"][0]["name"] == "Acme Corp"
        mock_repository.query_entities.assert_called_once_with(
            entity_type="company",
            filters=None,
            sort_by=None,
            sort_order="asc",
            limit=10,
        )


class TestSearchEntitiesTool:
    @pytest.mark.asyncio
    async def test_search_entities_called_correctly(self, agent, mock_repository):
        entity = Entity(
            name="Jane Doe",
            canonical_name="jane_doe",
            type="person",
        )
        mock_repository.search_entities.return_value = [entity]

        tool_call = {
            "id": "call_s",
            "function": {
                "name": "search_entities",
                "arguments": json.dumps({"query": "Jane"}),
            },
        }
        result = await agent._execute_tool(tool_call)
        assert result["count"] == 1
        assert result["results"][0]["name"] == "Jane Doe"


class TestAggregateDataTool:
    @pytest.mark.asyncio
    async def test_aggregate_entities_called_correctly(self, agent, mock_repository):
        mock_repository.aggregate_entities.return_value = [
            {"value": 42},
        ]

        tool_call = {
            "id": "call_a",
            "function": {
                "name": "aggregate_data",
                "arguments": {
                    "entity_type": "company",
                    "operation": "count",
                },
            },
        }
        result = await agent._execute_tool(tool_call)
        assert result["results"] == [{"value": 42}]
        mock_repository.aggregate_entities.assert_called_once_with(
            entity_type="company",
            property_name=None,
            operation="count",
            group_by=None,
        )
