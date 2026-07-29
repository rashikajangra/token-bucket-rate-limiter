from fastapi import FastAPI, Header, HTTPException, Response
import time
import redis
import os

app = FastAPI()

capacity = 5
refill_rate = 0.1

# r = redis.Redis(host="localhost", port=6379, decode_responses=True)
r = redis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379"), decode_responses=True)

def check_request(client_id, r):
    now = time.monotonic()

    if r.exists(client_id):
        data = r.hgetall(client_id)
        tokens = float(data["tokens"])
        last_checked = float(data["last_checked"])
    else:
        tokens = capacity
        last_checked = now

    elapsed = now - last_checked
    refill = elapsed * refill_rate
    tokens = min(capacity, tokens + refill)

    if tokens >= 1:
        tokens -= 1
        allowed = True
    else:
        allowed = False

    r.hset(client_id, mapping={"tokens": tokens, "last_checked": now})
    return allowed, tokens

window = 10
limit = 5

def check_sliding_window(client_id, r):
    now = time.time()
    cutoff  = now - window
    r.zremrangebyscore(client_id + ":sliding", 0, cutoff)
    count = r.zcard(client_id + ":sliding")

    if count < limit:
        r.zadd(client_id + ":sliding", {str(now): now})
        return True, limit - count - 1
    else:
        return False, 0

@app.get("/check")
def check(response: Response, x_client_id: str = Header(...), mode: str = "bucket"):
    allowed, remaining = check_request(x_client_id, r)

    if mode == "sliding":
        allowed, remaining = check_sliding_window(x_client_id, r)
    else:
        allowed, remaining = check_request(x_client_id, r)

    response.headers["X-RateLimit-Remaining"] = str(round(remaining, 2))

    if allowed:
        return {"status": "allowed", "client_id": x_client_id}
    else:
        raise HTTPException(status_code=429, detail="Try After Sometime", headers={"X-RateLimit-Remaining": str(round(remaining, 2))})
    