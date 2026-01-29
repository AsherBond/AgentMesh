# Workspace Configuration

AgentMesh uses a workspace-based file structure to organize agent data and memories.

## Default Workspace

By default, all agent data is stored in `~/agentmesh/`:

```
~/agentmesh/
├── memory/
│   ├── MEMORY.md                      # Long-term curated memory
│   ├── 2026-01-29.md                 # Daily memory (today)
│   ├── 2026-01-28.md                 # Daily memory (yesterday)
│   ├── long-term/                    # Vector index storage
│   │   └── index.db                  # SQLite database for search
│   ├── shared/                       # Shared knowledge (optional)
│   └── users/                        # User-specific memories (optional)
│       └── {user_id}/
│           ├── MEMORY.md
│           └── 2026-01-29.md
└── skills/                            # Shared skills (future)
```

## Global Workspace Configuration

### Quick Setup (Recommended for SDK usage)

Set the global workspace once at the start of your application:

```python
import agentmesh

# Set global workspace - all agents will use this
agentmesh.set_workspace("~/my_agents")

# Now create agents - they automatically use the workspace
from agentmesh import Agent
from agentmesh.memory import MemoryManager

# No need to specify workspace_root - uses global setting
memory_manager = MemoryManager()

agent = Agent(
    name="MyAgent",
    system_prompt="You are a helpful assistant",
    model=model,
    memory_manager=memory_manager
)
```

### Check Current Workspace

```python
import agentmesh

# Get current workspace
workspace = agentmesh.get_workspace()
print(f"Using workspace: {workspace}")
```

## Per-Agent Workspace Override

You can still override workspace for specific use cases:

```python
from agentmesh.memory import MemoryConfig, MemoryManager

# Override for specific memory manager
custom_config = MemoryConfig(workspace_root="~/special_workspace")
memory_manager = MemoryManager(config=custom_config)
```

## Advanced Configuration

For more control over memory settings:

```python
import agentmesh
from agentmesh.memory import MemoryConfig, set_global_memory_config

# Method 1: Use convenience function (simple)
agentmesh.set_workspace("~/my_agents")

# Method 2: Full control with MemoryConfig
config = MemoryConfig(
    workspace_root="~/my_agents",
    embedding_provider="openai",  # or "local"
    embedding_model="text-embedding-3-small",
    chunk_max_tokens=500,
    vector_weight=0.7,
    keyword_weight=0.3
)
set_global_memory_config(config)
```

## File Structure Details

### Memory Files

- **`memory/MEMORY.md`**: Long-term curated memories
  - Agent's "brain" - distilled knowledge
  - Loaded automatically at session start
  - Manually curated from daily logs

- **`memory/YYYY-MM-DD.md`**: Daily memory logs
  - Today's and yesterday's files loaded at session start
  - Raw chronological notes
  - Append-only during the day

- **`memory/long-term/index.db`**: Vector search index
  - SQLite database with embeddings
  - Auto-rebuilt when files change
  - Can be deleted and regenerated

- **`memory/users/{user_id}/`**: User-specific memories (optional)
  - Isolated memory for each user
  - Same structure as global memory

- **`memory/shared/`**: Shared knowledge base (optional)
  - Common knowledge accessible to all

### Skills Directory

- **`skills/`**: Reusable agent skills (future feature)
  - Shared across all agents
  - Version controlled capabilities

## Migration from Old Structure

If you have existing workspaces with per-agent directories:

```python
# Old structure (before v0.2.0):
# ~/.agentmesh/workspaces/{agent_id}/memory/
# ~/.agentmesh/workspaces/{agent_id}/.memory/index.db

# New structure (v0.2.0+):
# ~/agentmesh/memory/
# ~/agentmesh/memory/long-term/index.db

# The index will be automatically rebuilt in the new location
# You can manually migrate memory files or start fresh
```

## Environment-based Configuration

For different environments (dev, staging, prod):

```python
import os
import agentmesh

# Use environment variable
workspace = os.getenv("AGENTMESH_WORKSPACE", "~/agentmesh")
agentmesh.set_workspace(workspace)
```

## Best Practices

1. **Set workspace once**: Call `agentmesh.set_workspace()` at application startup
2. **Use global config**: Avoids repeating workspace path everywhere
3. **Separate environments**: Use different workspaces for dev/test/prod
4. **Git-friendly**: The `memory/` directory is designed to work well with version control
5. **Manual review**: Periodically review and curate `MEMORY.md` from daily logs
6. **Simple structure**: Single workspace for all agents keeps things organized
