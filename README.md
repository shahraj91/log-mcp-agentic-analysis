# Log MCP -- Agentic Log Analysis System

![Python](https://img.shields.io/badge/python-3.12-blue)
![MCP](https://img.shields.io/badge/MCP-enabled-green)
![Status](https://img.shields.io/badge/status-working-success)

A local **Model Context Protocol (MCP)** server + client system for
analyzing large log files using a hybrid architecture:

-   Deterministic signal extraction (parsing, aggregation, clustering)
-   Tool abstraction via MCP
-   Optional agentic reasoning via OpenAI Agents SDK
-   Structured output + visual graph generation

This project simulates how modern production log triage systems are
built.

------------------------------------------------------------------------

## Why This Project Exists

Most AI demos throw raw logs into an LLM.

This system does the opposite:

1.  Extract structured signals deterministically\
2.  Expose capabilities as MCP tools\
3.  Allow optional agentic reasoning on top

This separation mirrors production-grade observability and AI-assisted
triage systems.

------------------------------------------------------------------------

## Features

-   Log level aggregation (INFO / WARN / ERROR / FATAL)
-   Time-bucketed event histogram
-   Error clustering via normalized string similarity
-   Graph generation (PNG)
-   Local-only mode (no API required)
-   Optional agentic integration (LLM-powered triage summaries)

------------------------------------------------------------------------

## Architecture

    local_triage.py (client)
            ↓
    MCP HTTP transport
            ↓
    server.py (tool layer)
            ↓
    Log analysis + graph generation

### MCP Tools Exposed

-   `analyze_levels`
-   `cluster_errors`
-   `make_graph`

The client calls these tools and formats the output.

------------------------------------------------------------------------

## Example Output (15k+ Line Log)

### Terminal Analysis Output

![Terminal Output](docs/terminal_output.png)

### Log Level Distribution Graph

![Log Levels Graph](docs/log_levels.png)

------------------------------------------------------------------------

## Setup

``` bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

------------------------------------------------------------------------

## Generate Large Synthetic Log

``` bash
python3 generate_large_log.py
```

This produces a 15,000+ line realistic production-style log.

------------------------------------------------------------------------

## Run MCP Server

``` bash
python3 server.py
```

------------------------------------------------------------------------

## Run Local Triage (No OpenAI Required)

In a separate terminal:

``` bash
python3 local_triage.py --log large_sample.log
```

Outputs:

-   Log level table (counts + %)
-   Top error clusters
-   Time-bucket summary
-   Graph saved as `log_levels.png`

------------------------------------------------------------------------

## Optional: Agentic Mode (Requires OpenAI API Key)

``` bash
export OPENAI_API_KEY="sk-..."
python3 agent_client.py
```

This allows the agent to: - Call MCP tools - Summarize root causes -
Suggest debugging steps - Classify severity

------------------------------------------------------------------------

## Tech Stack

-   Python 3.12
-   MCP (Model Context Protocol)
-   Pandas
-   Matplotlib
-   OpenAI Agents SDK (optional)

------------------------------------------------------------------------

## Project Structure

    log-mcp/
    │
    ├── server.py
    ├── local_triage.py
    ├── agent_client.py
    ├── generate_large_log.py
    ├── sample.log
    ├── requirements.txt
    ├── docs/
    │   ├── terminal_output.png
    │   └── log_levels.png
    └── README.md

------------------------------------------------------------------------

## Design Philosophy

-   Deterministic first
-   LLM second
-   Clear separation of capabilities and reasoning
-   Production-inspired architecture
-   Reproducible and inspectable outputs

------------------------------------------------------------------------

## Future Improvements

-   Streamlit dashboard UI
-   Docker containerization
-   GitHub Actions CI
-   Structured test coverage
-   Semantic clustering via embeddings
-   Real-time streaming log ingestion

------------------------------------------------------------------------

## License

MIT
