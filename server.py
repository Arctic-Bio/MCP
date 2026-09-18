"""
Hermes MCP Manager
Allows an agent to install, list, enable, disable, and remove MCP servers
from its own Hermes config.yaml.

Made with love by Fox, and his local agentic swarm.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from mcp.server import mcpserver
from mcp.server.mcpserver import MCPServer
# ──────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────

HERMES_HOME = Path(os.environ.get("HERMES_HOME", r"C:\Users\<Your directory here>\AppData\Local\hermes"))
CONFIG_PATH = HERMES_HOME / "config.yaml"
BACKUP_DIR = HERMES_HOME / "mcp-manager-backups"

mcp = MCPServer(
    "hermes-mcp-manager",
    description="Manage MCP servers in Hermes Agent's config.yaml"
)

# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────

def _load_config() -> Dict[str, Any]:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Config not found: {CONFIG_PATH}")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def _save_config(data: Dict[str, Any]) -> None:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    if CONFIG_PATH.exists():
        stamp = __import__("datetime").datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = BACKUP_DIR / f"config.yaml.{stamp}.bak"
        shutil.copy2(CONFIG_PATH, backup)

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

def _get_mcp_section(data: Dict[str, Any]) -> Dict[str, Any]:
    if "mcp_servers" not in data or data["mcp_servers"] is None:
        data["mcp_servers"] = {}
    return data["mcp_servers"]

def _run_hermes_cmd(args: List[str]) -> str:
    """Run a hermes CLI command and return stdout+stderr."""
    try:
        result = subprocess.run(
            ["hermes"] + args,
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(HERMES_HOME),
        )
        out = (result.stdout or "") + (result.stderr or "")
        return out.strip() or f"(exit code {result.returncode})"
    except FileNotFoundError:
        return "Error: 'hermes' command not found in PATH"
    except Exception as e:
        return f"Error running hermes: {e}"

# ──────────────────────────────────────────────────────────────
# Tools
# ──────────────────────────────────────────────────────────────

@mcp.tool()
def list_installed_mcps() -> str:
    """List all MCP servers currently configured in Hermes config.yaml."""
    data = _load_config()
    servers = _get_mcp_section(data)

    if not servers:
        return "No MCP servers are currently configured."

    lines = ["Installed MCP servers:\n"]
    for name, cfg in servers.items():
        enabled = cfg.get("enabled", True)
        status = "enabled" if enabled else "disabled"
        if "url" in cfg:
            transport = f"HTTP → {cfg['url']}"
        else:
            cmd = cfg.get("command", "?")
            args = " ".join(cfg.get("args", []))
            transport = f"stdio: {cmd} {args}"
        lines.append(f"• {name}  [{status}]\n  {transport}")
    return "\n".join(lines)

@mcp.tool()
def add_stdio_mcp(
    name: str,
    command: str,
    args: List[str],
    env: Optional[Dict[str, str]] = None,
    enabled: bool = True,
) -> str:
    """
    Add a local stdio MCP server to Hermes.

    Example:
      name="filesystem"
      command="npx"
      args=["-y", "@modelcontextprotocol/server-filesystem", "C:/Users/<Your Directory Here>/Projects"]
    """
    data = _load_config()
    servers = _get_mcp_section(data)

    if name in servers:
        return f"Server '{name}' already exists. Use remove_mcp first or choose a different name."

    entry: Dict[str, Any] = {
        "command": command,
        "args": args,
        "enabled": enabled,
    }
    if env:
        entry["env"] = env

    servers[name] = entry
    _save_config(data)
    return (
        f"Added stdio MCP server '{name}'.\n"
        f"Command: {command} {' '.join(args)}\n\n"
        f"Run /reload-mcp in Hermes (or restart) to activate it."
    )

@mcp.tool()
def add_http_mcp(
    name: str,
    url: str,
    headers: Optional[Dict[str, str]] = None,
    transport: str = "streamable-http",
    enabled: bool = True,
) -> str:
    """
    Add a remote HTTP / Streamable-HTTP MCP server.

    Example:
      name="jetbrains"
      url="http://127.0.0.1:64462/stream"
    """
    data = _load_config()
    servers = _get_mcp_section(data)

    if name in servers:
        return f"Server '{name}' already exists."

    entry: Dict[str, Any] = {
        "url": url,
        "transport": transport,
        "enabled": enabled,
    }
    if headers:
        entry["headers"] = headers

    servers[name] = entry
    _save_config(data)
    return (
        f"Added HTTP MCP server '{name}' → {url}\n\n"
        f"Run /reload-mcp in Hermes to activate it."
    )

@mcp.tool()
def remove_mcp(name: str) -> str:
    """Remove an MCP server from the config by name."""
    data = _load_config()
    servers = _get_mcp_section(data)

    if name not in servers:
        return f"Server '{name}' not found."

    del servers[name]
    _save_config(data)
    return f"Removed MCP server '{name}'. Run /reload-mcp to apply."

@mcp.tool()
def enable_mcp(name: str) -> str:
    """Enable a previously disabled MCP server."""
    data = _load_config()
    servers = _get_mcp_section(data)

    if name not in servers:
        return f"Server '{name}' not found."

    servers[name]["enabled"] = True
    _save_config(data)
    return f"Enabled '{name}'. Run /reload-mcp to apply."

@mcp.tool()
def disable_mcp(name: str) -> str:
    """Disable an MCP server without deleting it."""
    data = _load_config()
    servers = _get_mcp_section(data)

    if name not in servers:
        return f"Server '{name}' not found."

    servers[name]["enabled"] = False
    _save_config(data)
    return f"Disabled '{name}'. Run /reload-mcp to apply."

@mcp.tool()
def set_tool_filter(
    name: str,
    include: Optional[List[str]] = None,
    exclude: Optional[List[str]] = None,
) -> str:
    """
    Restrict which tools from an MCP server Hermes can see.
    Pass include=["tool1", "tool2"] or exclude=["dangerous_tool"].
    """
    data = _load_config()
    servers = _get_mcp_section(data)

    if name not in servers:
        return f"Server '{name}' not found."

    tools = servers[name].setdefault("tools", {})
    if include is not None:
        tools["include"] = include
    if exclude is not None:
        tools["exclude"] = exclude

    _save_config(data)
    return f"Updated tool filter for '{name}'. Run /reload-mcp to apply."

@mcp.tool()
def get_config_path() -> str:
    """Return the absolute path to the Hermes config.yaml this manager is editing."""
    return str(CONFIG_PATH)

@mcp.tool()
def install_via_cli(name: str) -> str:
    """
    Try to install a catalog MCP using the official Hermes CLI
    (hermes mcp install <name>). Prefer this for Nous-approved servers.
    """
    output = _run_hermes_cmd(["mcp", "install", name])
    return f"hermes mcp install {name}\n\n{output}"

@mcp.tool()
def list_catalog() -> str:
    """List MCP servers available in the Hermes curated catalog."""
    output = _run_hermes_cmd(["mcp", "catalog"])
    return output or "Could not retrieve catalog (is hermes on PATH?)."

# ──────────────────────────────────────────────────────────────
# Entrypoint
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run(transport="stdio")
