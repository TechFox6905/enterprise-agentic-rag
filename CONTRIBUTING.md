## Commit Message Convention

This project follows the **Conventional Commits** specification.

### Format

```text
<type>(<scope>): <short summary>
```

### Types

| Type | Description |
|------|-------------|
| feat | New feature |
| fix | Bug fix |
| docs | Documentation changes |
| style | Formatting, linting, comments |
| refactor | Code restructuring without changing behavior |
| perf | Performance improvements |
| test | Add or update tests |
| build | Build system or dependency changes |
| ci | CI/CD workflow changes |
| chore | Maintenance tasks |
| revert | Revert a previous commit |

### Scopes

Use the module or component being changed.

Examples:

- api
- auth
- config
- database
- docker
- docs
- llm
- rag
- retrieval
- embeddings
- pipeline
- tests
- ui

### Examples

```text
feat(auth): implement JWT authentication

fix(database): handle connection timeout

docs(readme): update installation guide

refactor(rag): simplify retrieval pipeline

test(api): add health endpoint tests

build(deps): upgrade FastAPI to 0.139

ci(github): add lint workflow
```

### Guidelines

- Use the imperative mood ("add", not "added")
- Keep the summary under 72 characters
- Start with a lowercase type and scope
- Do not end the summary with a period
- Make each commit focused on a single logical change