# Hermes MCP Manager

An MCP server that lets a Hermes agent manage its **own** MCP configuration — installing, listing, enabling, disabling, and removing other MCP servers directly from `config.yaml`.

> Made with love by Fox, and his local agentic swarm.

---

## The idea behind it

The goal isn't just config editing — it's **self-extension**. Agents shouldn't be capped at whatever tools they happened to launch with.

The intended loop looks like this:

1. You ask an agent to do something it can't currently do — e.g. "dim my screen."
2. It doesn't have a tool for that, so instead of just failing, it **builds one**: writes a small MCP server (a script, a stdio tool, whatever fits) that exposes a `dim_screen` capability.
3. Using this manager, it registers that new server in `config.yaml` via `add_stdio_mcp` (or `add_http_mcp` if it's a hosted service).
4. From then on, `dim_screen` — and anything else it builds — is just a tool call away, for that agent and for any other agent sharing the same Hermes config.

In other words: if an agent hits a wall, it doesn't stop — it grows a new tool, saves it as an MCP server, and syncs it so the whole swarm can use it going forward. Over time the agents' collective toolset expands to match whatever you've actually asked of them, rather than staying fixed at install time.

This manager is the piece that makes that loop possible: it's the mechanism agents use to register (and later prune, disable, or filter) the tools they create for themselves.

---

## What it does

Hermes MCP Manager exposes a set of tools (via the Model Context Protocol) that read and write your Hermes `config.yaml` file. This lets an agent extend its own toolset at runtime — adding a filesystem server, connecting to a remote HTTP MCP endpoint, or trimming down which tools a noisy server exposes — without you hand-editing YAML.

Every write automatically creates a timestamped backup of the previous config before saving.

---

## Requirements

- Python 3.9+
- [`pyyaml`](https://pypi.org/project/PyYAML/)
- An MCP server framework providing `mcp.server.mcpserver.MCPServer` (bundled with your Hermes/MCP SDK install)
- Hermes installed, with `hermes` available on your `PATH` (only required for `install_via_cli` and `list_catalog`)

Install the Python dependency:

```bash
pip install pyyaml
```

---

## Configuration

By default, the manager looks for your config at:

```
C:\Users\<Your directory here>\AppData\Local\hermes\config.yaml
```

Override this by setting the `HERMES_HOME` environment variable to point at your Hermes home directory:

```bash
# Windows (PowerShell)
$env:HERMES_HOME = "C:\Users\yourname\AppData\Local\hermes"

# macOS / Linux
export HERMES_HOME=/home/yourname/.local/share/hermes
```

The manager reads/writes `$HERMES_HOME/config.yaml` and stores backups in `$HERMES_HOME/mcp-manager-backups/`.

---

## Running the server

```bash
python hermes_mcp_manager.py
```

This starts the server on **stdio** transport, ready to be registered as an MCP server inside Hermes itself (or any MCP-compatible client).

To register it with Hermes, add an entry to your `config.yaml` pointing at this script, e.g.:

```yaml
mcp_servers:
  mcp-manager:
    command: python
    args: ["C:/path/to/hermes_mcp_manager.py"]
    enabled: true
```

Then restart Hermes or run `/reload-mcp`.

---

## Available tools

| Tool | Description |
|---|---|
| `list_installed_mcps()` | Lists every MCP server currently configured, with status (enabled/disabled) and transport info. |
| `add_stdio_mcp(name, command, args, env=None, enabled=True)` | Adds a local stdio-based MCP server (e.g. an `npx`-launched server). |
| `add_http_mcp(name, url, headers=None, transport="streamable-http", enabled=True)` | Adds a remote HTTP / Streamable-HTTP MCP server. |
| `remove_mcp(name)` | Removes a server entry entirely. |
| `enable_mcp(name)` | Re-enables a previously disabled server. |
| `disable_mcp(name)` | Disables a server without deleting its config. |
| `set_tool_filter(name, include=None, exclude=None)` | Restricts which tools from a given server are visible to Hermes. |
| `get_config_path()` | Returns the absolute path to the `config.yaml` being managed. |
| `install_via_cli(name)` | Installs a catalog server via `hermes mcp install <name>` (requires `hermes` on `PATH`). |
| `list_catalog()` | Lists servers available in the Hermes curated catalog via `hermes mcp catalog`. |

After any change, Hermes needs to reload its MCP servers — either run `/reload-mcp` or restart the agent.

---

## Examples

**Add a local filesystem server:**

```python
add_stdio_mcp(
    name="filesystem",
    command="npx",
    args=["-y", "@modelcontextprotocol/server-filesystem", "C:/Users/yourname/Projects"],
)
```

**Add a remote HTTP server:**

```python
add_http_mcp(
    name="jetbrains",
    url="http://127.0.0.1:64462/stream",
)
```

**Temporarily disable a server:**

```python
disable_mcp(name="filesystem")
```

**Limit a server to specific tools:**

```python
set_tool_filter(name="filesystem", exclude=["delete_file"])
```

---

## Backups

Every time the config is saved, the previous version is copied to:

```
$HERMES_HOME/mcp-manager-backups/config.yaml.<YYYYMMDD-HHMMSS>.bak
```

If a change breaks your setup, restore the most recent backup by copying it back over `config.yaml`.

---

## Notes / caveats

- `install_via_cli` and `list_catalog` shell out to the `hermes` CLI and will fail gracefully (returning an error string) if `hermes` isn't found on `PATH`.
- Adding a server does not activate it immediately — Hermes must reload its MCP configuration.
- No validation is performed on `command`/`args`/`url` values beyond basic presence checks; double-check entries before reloading, since this tool can execute arbitrary commands defined in your config.

---

## License

MIT
