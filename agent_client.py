# agent_client.py (safe cleanup)
import asyncio, os
from agents import Agent, Runner
from agents.mcp import MCPServerStreamableHttp

LOG_PATH = os.path.abspath("sample.log")

async def maybe_close(obj):
    # handle close/aclose variations across versions
    if hasattr(obj, "aclose"):
        await obj.aclose()
    elif hasattr(obj, "close"):
        res = obj.close()
        if asyncio.iscoroutine(res):
            await res

async def main():
    mcp_server = MCPServerStreamableHttp(
        name="log-mcp",
        params={"url": "http://localhost:8000/mcp"},
    )

    await mcp_server.connect()

    try:
        agent = Agent(
            name="Log Triage Agent",
            instructions=(
                "Use MCP tools to analyze the log. "
                "Return a markdown table of level counts, top error clusters, and the graph path."
            ),
            mcp_servers=[mcp_server],
        )

        result = await Runner.run(agent, f"Analyze this log: {LOG_PATH}")
        print(result.final_output)

    except Exception as e:
        print(f"Run failed: {e!r}")
        raise
    finally:
        await maybe_close(mcp_server)

if __name__ == "__main__":
    asyncio.run(main())
