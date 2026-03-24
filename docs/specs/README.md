# SDD Specifications Index

Spec-Driven Development (SDD) artifacts for the Knowledge App project.

## Changes

### Phase 1: Project Scaffold

Bootstrap the repository from greenfield to a buildable, lintable, testable, containerizable Python monorepo.

| Artifact | Status | File |
|----------|--------|------|
| Exploration | Complete | [exploration.md](project-scaffold/exploration.md) |
| Proposal | Complete | [proposal.md](project-scaffold/proposal.md) |
| Specification | Complete | [spec.md](project-scaffold/spec.md) |
| Design | Complete | [design.md](project-scaffold/design.md) |
| Tasks | Complete (all implemented) | [tasks.md](project-scaffold/tasks.md) |

### Phase 2: Database Layer + ACL

PostgreSQL data layer — domain entities, port interfaces, SQLAlchemy async models, Alembic migration with RLS policies, and repository adapters.

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

All artifacts were originally persisted to [Engram](https://github.com/bkuberek/engram) persistent memory during SDD sessions and exported to this directory for version control.
