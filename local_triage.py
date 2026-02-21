#!/usr/bin/env python3
"""
local_triage.py

Runs log triage via your local MCP server (no OpenAI calls):
- Calls MCP tools: analyze_levels, cluster_errors, make_graph
- Prints a table of log levels (counts + %)
- Prints top error clusters with examples
- Prints where the graph PNG was saved

Usage:
  python3 local_triage.py
  python3 local_triage.py --log ./sample.log --url http://localhost:8000/mcp
"""

import argparse
import asyncio
import json
import os
from typing import Any, Dict

import pandas as pd

from mcp.client.streamable_http import streamablehttp_client
from mcp import ClientSession


def extract_json(tool_result) -> Dict[str, Any]:
    content = getattr(tool_result, "content", None)
    if not content:
        raise RuntimeError(f"No content in tool_result: {tool_result!r}")

    last_err = None

    for block in content:
        try:
            # 1) MCP/Pydantic models: prefer model_dump()
            if hasattr(block, "model_dump"):
                val = block.model_dump()
                if isinstance(val, dict):
                    # Sometimes it's {"type": "...", "text": "..."} etc.
                    if "json" in val and isinstance(val["json"], dict):
                        return val["json"]
                    if "text" in val and isinstance(val["text"], str):
                        return json.loads(val["text"])
                    return val

            # 2) Newer MCP content blocks often have .json attribute (dict)
            if hasattr(block, "json"):
                val = getattr(block, "json")
                # If it's callable (older shape), call it
                if callable(val):
                    val = val()
                # val might be dict OR JSON string
                if isinstance(val, dict):
                    return val
                if isinstance(val, str) and val.strip():
                    return json.loads(val)

            # 3) Dict-like blocks
            if isinstance(block, dict):
                if "json" in block and isinstance(block["json"], dict):
                    return block["json"]
                if "text" in block and isinstance(block["text"], str):
                    return json.loads(block["text"])

            # 4) Text blocks
            if hasattr(block, "text") and isinstance(block.text, str) and block.text.strip():
                return json.loads(block.text)

        except Exception as e:
            last_err = e
            continue

    raise RuntimeError(f"Unable to extract JSON from tool_result. last_err={last_err!r} content={content!r}")


async def run_triage(log_path: str, mcp_url: str, bin_minutes: int, threshold: float, top_k: int, examples_each: int):
    if not os.path.exists(log_path):
        raise FileNotFoundError(f"Log file not found: {log_path}")

    # streamablehttp_client returns (read, write, get_session_id) in current SDKs
    async with streamablehttp_client(mcp_url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            levels_res = await session.call_tool(
                "analyze_levels",
                {"log_path": log_path, "bin_minutes": bin_minutes},
            )
            levels_obj = extract_json(levels_res)

            clusters_res = await session.call_tool(
                "cluster_errors",
                {
                    "log_path": log_path,
                    "threshold": threshold,
                    "top_k": top_k,
                    "examples_each": examples_each,
                },
            )
            clusters_obj = extract_json(clusters_res)

            graph_res = await session.call_tool(
                "make_graph",
                {"log_path": log_path, "out_path": "log_levels.png"},
            )
            graph_obj = extract_json(graph_res)

    return levels_obj, clusters_obj, graph_obj


def print_results(levels_obj: Dict[str, Any], clusters_obj: Dict[str, Any], graph_obj: Dict[str, Any]):
    counts = levels_obj.get("level_counts", {}) or {}
    total = sum(counts.values()) or 1

    df = pd.DataFrame(
        [{"level": k, "count": int(v), "pct": round((int(v) * 100) / total, 2)} for k, v in counts.items()]
    ).sort_values("count", ascending=False)

    print("\n=== LEVEL COUNTS ===")
    if len(df) == 0:
        print("(No level tags found in logs. Ensure your logs contain INFO/WARN/ERROR/etc.)")
    else:
        print(df.to_string(index=False))

    # Optional: time bins summary
    time_bins = levels_obj.get("time_bins", {})
    if time_bins:
        print("\n=== EVENT VOLUME BY TIME BIN ===")
        # show up to top 12 bins by count
        top_bins = sorted(time_bins.items(), key=lambda kv: kv[1], reverse=True)[:12]
        for ts, c in top_bins:
            print(f"{ts}  count={c}")

    print("\n=== TOP ERROR CLUSTERS ===")
    clusters = clusters_obj.get("clusters", [])
    if not clusters:
        print("(No error-ish lines found.)")
    else:
        for c in clusters:
            print(f"\n[{c.get('cluster_id')}] count={c.get('count')}")
            print(f"rep: {c.get('rep')}")
            for ex in c.get("examples", []) or []:
                print(f"  - {ex}")

    out_path = graph_obj.get("out_path")
    if out_path:
        print(f"\n=== GRAPH SAVED ===\n{out_path}")
    else:
        print("\n=== GRAPH SAVED ===\n(log_levels.png)")


def main():
    ap = argparse.ArgumentParser(description="Local MCP log triage client (no OpenAI calls).")
    ap.add_argument("--log", default=os.path.abspath("sample.log"), help="Path to log file (default: ./sample.log)")
    ap.add_argument("--url", default="http://localhost:8000/mcp", help="MCP server URL (default: http://localhost:8000/mcp)")
    ap.add_argument("--bin-minutes", type=int, default=5, help="Histogram bin size in minutes (default: 5)")
    ap.add_argument("--threshold", type=float, default=0.82, help="Clustering similarity threshold (default: 0.82)")
    ap.add_argument("--top-k", type=int, default=10, help="Top clusters to return (default: 10)")
    ap.add_argument("--examples", type=int, default=2, help="Examples per cluster (default: 2)")
    args = ap.parse_args()

    levels_obj, clusters_obj, graph_obj = asyncio.run(
        run_triage(
            log_path=os.path.abspath(args.log),
            mcp_url=args.url,
            bin_minutes=args.bin_minutes,
            threshold=args.threshold,
            top_k=args.top_k,
            examples_each=args.examples,
        )
    )

    print_results(levels_obj, clusters_obj, graph_obj)


if __name__ == "__main__":
    main()
