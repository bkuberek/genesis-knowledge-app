Build me a web app called "Knowledge" where users can upload datasets and documents, then ask questions about them in plain English. Before you start, read `docs/product/initial-user-prompt.md` for the full engineering brief -- it has the complete architecture, data model, phased delivery plan, and gotchas. Also check `docs/product/user-requirements/` which has the original assignment PDF and the sample CSV of 500 fictional SaaS companies (columns: company name, industry, ARR, employee count, churn rate, growth rate, founding year). We are taking those initial requirements further to build a generic multi-user knowledge management tool, not just a pandas query interface.

The core idea: users upload CSVs, PDFs, Word docs, text files, or URLs. The system extracts entities and relationships using an LLM, resolves duplicates, and stores everything in PostgreSQL with JSONB columns for dynamic properties. The chat agent then queries the database using tool calling to answer questions. PostgreSQL handles everything -- entities, documents, relationships, chat sessions, and Keycloak persistence. JSONB gives us native SQL operators for structured queries like `(properties->>'arr_thousands')::float > 500`, GIN indexes for performance, and Row-Level Security for access control. No graph database needed.

Use hexagonal architecture with three packages: core (domain, ports, services -- zero framework deps), api (FastAPI, WebSocket, auth, DI), and workers (ingestion pipeline, LLM client, parsers, PostgreSQL adapters). One class per file, constructor injection, async everywhere. SQLAlchemy async with asyncpg for the database layer.

For auth, use Keycloak with two OAuth2 clients -- a confidential one for the backend and a public PKCE one for the React frontend. Self-registration enabled. Provide a realm-export.json so it auto-provisions on docker compose up. Chat sessions are persisted in PostgreSQL so users can resume conversations.

The chat agent should be a custom tool-calling loop, about 50 lines, no LangChain. Give it 3-4 focused tools: describe_tables (schema introspection), query_data (filter/sort with parameterized SQL against JSONB), aggregate_data (avg/sum/count grouped by properties), and search_entities (full-text search). Max 5 tool-call rounds per message. Also expose an MCP server via fastapi-mcp so external AI assistants can use the same tools.

Frontend is React + TypeScript + Vite + TailwindCSS v4. Chat page with WebSocket and markdown rendering, document upload with drag-and-drop and processing status, entity search, and a session sidebar for switching between conversations. Keycloak OIDC login with keycloak-js.

Docker Compose runs PostgreSQL, Keycloak, and the app. Multi-stage Dockerfile that builds the frontend too. Use LiteLLM with the `anthropic/` prefix for all LLM calls. Use dynaconf for config with a settings.toml. CLI via cyclopts.

For workflow: use Spec-Driven Development for each feature -- `/sdd-explore` to investigate, `/sdd-ff` to fast-forward through proposal/spec/design/tasks, then `/sdd-apply` to implement. Delegate all implementation to sub-agents and orchestrate. Apply clean code principles throughout (use the python-clean-code, clean-functions, clean-names, clean-tests skills). Use conventional commits, ruff for linting and formatting, pytest for testing (target around 50 focused tests). Work directly on main. Set up GitHub Actions for CI (ruff + pytest on every push) and semantic versioning on main (version bump, tag, changelog). Commit frequently with passing tests.

The sample CSV should be uploadable through the UI and the chatbot must be able to answer the four example questions: "What's the average ARR for fintech companies?", "Which company has the highest growth rate?", "Show me companies founded after 2020 with less than 5% churn", and "How many companies have more than 100 employees?"

You will find LLM PROXY credentials in .env

LITE_LLM_PROXY_API_URL=https://litellm-production-f079.up.railway.app
LITE_LLM_PROXY_API_KEY=*****

Use this api for running llm models.

Finally, you will maintain claude.md file as opposed to agents.md file for compatibility with Claude code.
