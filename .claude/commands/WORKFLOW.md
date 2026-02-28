# Slash Commands & Workflows

## Backend Workflow
```
/be-prime → /be-planning → /be-execute → /be-validate → /commit
```

## Frontend Workflow
```
/fe-prime → /fe-execute → /fe-validate → /commit
```

## Available Commands

### Backend
| Command | Purpose |
|---------|---------|
| `/be-prime` | Load full backend context |
| `/be-planning` | Create implementation plan |
| `/be-execute` | Execute plan step by step |
| `/be-validate` | Run all quality checks |

### Frontend
| Command | Purpose |
|---------|---------|
| `/fe-prime` | Load full frontend context |
| `/fe-execute` | Execute frontend plan |
| `/fe-validate` | Run frontend quality checks |

### Cross-cutting
| Command | Purpose |
|---------|---------|
| `/commit` | Create conventional commit with safety checks |
| `/review` | Code review against 8 quality standards |
