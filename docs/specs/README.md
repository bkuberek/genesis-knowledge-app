# SDD Specifications

Spec-Driven Development (SDD) artifacts for the Knowledge App project. Phases 1–2 have
full SDD artifacts (exploration, proposal, spec, design, tasks). Phases 3–11 were
fast-tracked with implementation-first approach; their specs were written retroactively.

| Phase | Change | Status | Spec |
|-------|--------|--------|------|
| 1 | project-scaffold | ✅ Complete | [spec](project-scaffold/spec.md) |
| 2 | database-layer | ✅ Complete | [spec](database-layer/spec.md) |
| 3 | document-ingestion | ✅ Retroactive | [spec](document-ingestion/spec.md) |
| 4 | authentication | ✅ Retroactive | [spec](authentication/spec.md) |
| 5 | rest-api | ✅ Retroactive | [spec](rest-api/spec.md) |
| 6 | chat-agent | ✅ Retroactive | [spec](chat-agent/spec.md) |
| 7 | mcp-tools | ✅ Retroactive | [spec](mcp-tools/spec.md) |
| 8 | react-frontend | ✅ Retroactive | [spec](react-frontend/spec.md) |
| 9–10 | chat-persistence | ✅ Retroactive | [spec](chat-persistence/spec.md) |
| 11 | docker-polish | ✅ Retroactive | [spec](docker-polish/spec.md) |

## Full SDD Artifacts (Phases 1–2)

### Phase 1: Project Scaffold

Bootstrap the repository from greenfield to a buildable, lintable, testable, containerizable
Python monorepo.

| Artifact | Status | File |
|----------|--------|------|
| Exploration | Complete | [exploration.md](project-scaffold/exploration.md) |
| Proposal | Complete | [proposal.md](project-scaffold/proposal.md) |
| Specification | Complete | [spec.md](project-scaffold/spec.md) |
| Design | Complete | [design.md](project-scaffold/design.md) |
| Tasks | Complete (all implemented) | [tasks.md](project-scaffold/tasks.md) |

### Phase 2: Database Layer + ACL

PostgreSQL data layer — domain entities, port interfaces, SQLAlchemy async models, Alembic
migration with RLS policies, and repository adapters.

| Artifact | Status | File |
|----------|--------|------|
| Proposal | Complete | [proposal.md](database-layer/proposal.md) |
| Specification | Complete | [spec.md](database-layer/spec.md) |
| Design | Complete | [design.md](database-layer/design.md) |
| Tasks | Complete (all implemented) | [tasks.md](database-layer/tasks.md) |

## SDD Workflow

Each change follows the dependency graph:

```
exploration -> proposal -> specs --> tasks -> apply -> verify -> archive
                            ^
                            |
                          design
```

- **Exploration**: Investigate the codebase and clarify requirements
- **Proposal**: Define intent, scope, approach, and architecture decisions
- **Specification**: Verifiable requirements with GIVEN/WHEN/THEN scenarios
- **Design**: Technical approach, file layout, key implementation details
- **Tasks**: Implementation checklist broken into dependency-ordered batches

## Source

All artifacts were originally persisted to [Engram](https://github.com/bkuberek/engram)
persistent memory during SDD sessions and exported to this directory for version control.
