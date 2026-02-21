# Log MCP – Agentic Log Analysis with MCP

A local Model Context Protocol (MCP) server + client for analyzing large log files with:

- Log level aggregation (INFO/WARN/ERROR/FATAL)
- Error clustering
- Time-based event histogram
- Graph generation (PNG output)
- Optional agentic integration via OpenAI Agents SDK

## Architecture

local_triage.py (client)
        ↓
MCP HTTP transport
        ↓
server.py (tool layer)
        ↓
Log analysis + graph generation

The server exposes tools:

- `analyze_levels`
- `cluster_errors`
- `make_graph`

The client consumes these tools and formats results.

---

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
