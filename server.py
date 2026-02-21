# server.py
from __future__ import annotations

import base64
import io
import os
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import matplotlib.pyplot as plt

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Log MCP", json_response=True)

LEVEL_RE = re.compile(r"\b(INFO|WARN|WARNING|ERROR|FATAL|DEBUG|TRACE)\b", re.IGNORECASE)

TS_RE = re.compile(r"(?P<ts>\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2})")
ERROR_HINTS = ("error", "exception", "traceback", "fatal", "panic", "failed", "failure", "assert", "segfault")

def parse_level(line: str) -> Optional[str]:
    m = LEVEL_RE.search(line)
    return m.group(1).upper() if m else None

def parse_ts(line: str) -> Optional[datetime]:
    m = TS_RE.search(line)
    if not m:
        return None
    try:
        return datetime.strptime(m.group("ts"), "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None

def is_errorish(line: str) -> bool:
    lvl = parse_level(line)
    if lvl in ("ERROR", "FATAL"):
        return True
    low = line.lower()
    return any(h in low for h in ERROR_HINTS)

def normalize(line: str) -> str:
    s = line
    s = TS_RE.sub("<TS>", s)
    s = LEVEL_RE.sub("<LEVEL>", s)
    s = re.sub(r"\b0x[0-9a-fA-F]+\b", "<HEX>", s)
    s = re.sub(r"\b\d+\b", "<NUM>", s)
    s = re.sub(r"(https?://\S+)", "<URL>", s)
    s = re.sub(r"(/[A-Za-z0-9._-]+)+", "<PATH>", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()

@dataclass
class Cluster:
    cluster_id: int
    rep: str
    count: int
    examples: List[str]

def read_lines(log_path: str, max_lines: int = 200000) -> List[str]:
    with open(log_path, "r", errors="replace") as f:
        return [line.rstrip("\n") for _, line in zip(range(max_lines), f)]

@mcp.tool()
def analyze_levels(log_path: str, bin_minutes: int = 5) -> Dict[str, Any]:
    """Return counts by log level plus a time histogram (if timestamps exist)."""
    if not os.path.exists(log_path):
        raise FileNotFoundError(f"Log file not found: {log_path}")

    lines = read_lines(log_path)
    level_counts = Counter()
    time_bins = Counter()

    for line in lines:
        lvl = parse_level(line)
        if lvl:
            level_counts[lvl] += 1
        ts = parse_ts(line)
        if ts:
            # bucket to bin_minutes
            minute_bucket = (ts.minute // bin_minutes) * bin_minutes
            bucket = ts.replace(minute=minute_bucket, second=0)
            time_bins[bucket.isoformat(sep=" ")] += 1

    return {
        "log_path": log_path,
        "total_lines": len(lines),
        "level_counts": dict(level_counts),
        "time_bins": dict(time_bins),
        "bin_minutes": bin_minutes,
    }

@mcp.tool()
def cluster_errors(log_path: str, threshold: float = 0.82, top_k: int = 10, examples_each: int = 3) -> Dict[str, Any]:
    """Cluster error-ish lines by normalized string similarity."""
    if not os.path.exists(log_path):
        raise FileNotFoundError(f"Log file not found: {log_path}")

    lines = read_lines(log_path)
    error_lines = [ln for ln in lines if is_errorish(ln)]

    clusters: List[Cluster] = []

    for ln in error_lines:
        n = normalize(ln)
        best_i = None
        best_sc = 0.0
        for i, c in enumerate(clusters):
            sc = similarity(n, c.rep)
            if sc > best_sc:
                best_sc = sc
                best_i = i
        if best_i is not None and best_sc >= threshold:
            c = clusters[best_i]
            c.count += 1
            if len(c.examples) < examples_each:
                c.examples.append(ln)
        else:
            clusters.append(Cluster(cluster_id=len(clusters) + 1, rep=n, count=1, examples=[ln]))

    clusters.sort(key=lambda c: c.count, reverse=True)
    return {
        "log_path": log_path,
        "extracted_errorish": len(error_lines),
        "threshold": threshold,
        "clusters": [asdict(c) for c in clusters[:top_k]],
    }

@mcp.tool()
def make_graph(log_path: str, out_path: str = "log_levels.png") -> Dict[str, Any]:
    """Generate a PNG chart of level counts; saves locally and also returns base64."""
    data = analyze_levels(log_path)
    counts = data["level_counts"]
    if not counts:
        counts = {"INFO": 0, "WARN": 0, "ERROR": 0, "FATAL": 0}

    # Stable order
    order = ["TRACE", "DEBUG", "INFO", "WARN", "WARNING", "ERROR", "FATAL"]
    labels = [k for k in order if k in counts]
    values = [counts[k] for k in labels]

    plt.figure()
    plt.bar(labels, values)
    plt.title("Log level counts")
    plt.xlabel("Level")
    plt.ylabel("Count")
    plt.tight_layout()
    plt.savefig(out_path, dpi=160)
    plt.close()

    # base64 for UIs that want inline image
    with open(out_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")

    return {"log_path": log_path, "out_path": os.path.abspath(out_path), "png_base64": b64}
    
if __name__ == "__main__":
    # Streamable HTTP MCP server
    mcp.run(transport="streamable-http")
