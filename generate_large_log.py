import random
import uuid
from datetime import datetime, timedelta

OUTPUT_FILE = "large_sample.log"
TOTAL_LINES = 15000

start_time = datetime(2026, 2, 18, 10, 0, 0)

redis_nodes = ["10.0.0.4", "10.0.0.7", "10.0.0.9"]
db_hosts = ["db-prod-01", "db-prod-02"]
workers = ["worker-1", "worker-2", "worker-3"]

def random_ts(offset_seconds):
    return (start_time + timedelta(seconds=offset_seconds)).strftime("%Y-%m-%d %H:%M:%S")

def random_request():
    return f"req-{uuid.uuid4().hex[:8]}"

def random_order():
    return random.randint(80000, 99999)

def random_user():
    return random.randint(1000, 5000)

lines = []
for i in range(TOTAL_LINES):
    ts = random_ts(i)
    req = random_request()

    # 70% normal traffic
    if random.random() < 0.7:
        lines.append(f"{ts} INFO Checkout start order_id={random_order()} user_id={random_user()} request_id={req}")

    # 10% redis issues
    elif random.random() < 0.5:
        ip = random.choice(redis_nodes)
        lines.append(f"{ts} ERROR Timeout connecting to redis at {ip}:6379 request_id={req}")
        lines.append(f"{ts} WARN Retrying cache read attempt=1 request_id={req}")

    # 10% db issues
    elif random.random() < 0.7:
        host = random.choice(db_hosts)
        lines.append(f"{ts} ERROR Database connection refused host={host} port=5432 request_id={req}")

    # 7% upstream failures
    elif random.random() < 0.9:
        lines.append(f"{ts} ERROR HTTP 500 returned from upstream service billing-api request_id={req}")
        lines.append(f"{ts} WARN Retry attempt=1 request_id={req}")

    # 3% disk pressure events
    else:
        worker = random.choice(workers)
        usage = random.randint(90, 98)
        lines.append(f"{ts} ERROR Disk space critical on node={worker} usage={usage}%")
        lines.append(f"{ts} FATAL Service shutting down due to disk pressure node={worker}")

with open(OUTPUT_FILE, "w") as f:
    for line in lines:
        f.write(line + "\n")

print(f"Generated {len(lines)} lines in {OUTPUT_FILE}")
