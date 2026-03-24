"""Tests for MCP server integration via fastapi-mcp."""

from knowledge_api.app import MCP_TOOL_OPERATIONS, create_app


class TestMcpMount:
    def test_mcp_tool_operations_list(self):
        """Exactly four operations are exposed as MCP tools."""
        expected = {
            "search_knowledge",
            "add_knowledge",
            "get_entity",
            "get_document_entities",
        }
        assert set(MCP_TOOL_OPERATIONS) == expected

    def test_app_has_mcp_route(self):
        """create_app registers a route at /mcp."""
        app = create_app()
        mcp_paths = [r.path for r in app.routes if hasattr(r, "path") and r.path == "/mcp"]
        assert len(mcp_paths) == 1, "Expected exactly one /mcp route"

    def test_mcp_route_accepts_post(self):
        """The /mcp endpoint accepts POST (streamable HTTP transport)."""
        app = create_app()
        mcp_routes = [
            r
            for r in app.routes
            if hasattr(r, "path") and r.path == "/mcp" and "POST" in getattr(r, "methods", set())
        ]
        assert len(mcp_routes) == 1

    def test_mcp_route_before_spa_catchall(self):
        """MCP route is registered before the SPA catch-all."""
        app = create_app()
        route_paths = [getattr(r, "path", None) for r in app.routes]
        mcp_indices = [i for i, p in enumerate(route_paths) if p == "/mcp"]
        spa_indices = [i for i, p in enumerate(route_paths) if p == "/{path:path}"]
        if spa_indices:
            assert mcp_indices[0] < spa_indices[0], "MCP route must come before SPA catch-all"

    def test_openapi_includes_mcp_operations(self, app):
        """The OpenAPI schema includes the four operation_ids used by MCP."""
        schema = app.openapi()
        operation_ids = set()
        for path_item in schema.get("paths", {}).values():
            for method_detail in path_item.values():
                if isinstance(method_detail, dict) and "operationId" in method_detail:
                    operation_ids.add(method_detail["operationId"])

        for op in MCP_TOOL_OPERATIONS:
            assert op in operation_ids, f"Operation '{op}' not in OpenAPI schema"
