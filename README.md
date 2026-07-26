# **Token Bucket Rate Limiter**
A standalone rate-limiting API; not a library, but a real networked service that other APIs call into to check whether a request should be allowed. Built with Python, FastAPI, and Redis.

# **What it does**
Every client (identified by an X-Client-Id header) gets their own isolated "bucket" of tokens. Each request costs 1 token. Tokens refill continuously over time, up to a max capacity. When a client runs out of tokens, further requests are denied with a 429 Too Many Requests until enough time passes for tokens to refill.

Two rate-limiting strategies are supported, selectable per request:
1. Token Bucket (default) - allows short bursts, refills continuously
2. Sliding Window - counts requests in a rolling time window, no burst allowance

# **Tech stack**
• Python - core algorithm and API logic
• FastAPI - HTTP layer, request handling, status codes
• Redis (via Docker) - persistent, atomic storage for bucket/window state
• k6 - load testing

# **How it works**
1. A client sends GET /check with an X-Client-Id header.
2. The server looks up that client's bucket in Redis (or creates one if new).
3. Time-based refill is calculated: refill = elapsed_time × refill_rate, capped at max capacity.
4. If at least 1 token is available, the request is allowed and 1 token is consumed.
   If not, the request is denied with a 429 status.
5. The updated state is saved back to Redis.
6. The response includes an X-RateLimit-Remaining header showing tokens/requests left.

# **API**
GET /check

Headers:
| Header      | Required |                 Description                |
| ----------- | -------- | ------------------------------------------ |
| X-Client-ID | Row 1 B  | 	Identifies the client making the request  |

Query Parameters:
| Param | Default |      Options       |              Description              |
| ----- | ------- | ------------------ | ------------------------------------- |
| mode  | bucket  | 	bucket, sliding  | 	Which rate-limiting strategy to use  |

# **Responses:**
**Allowed:**
```
200 OK
X-RateLimit-Remaining: 3.5
{"status": "allowed", "client_id": "client1"}
```

**Denied:**
```
429 Too Many Requests
X-RateLimit-Remaining: 0
{"detail": "Try After Sometime"}
```

# **Running locally**
_**Prerequisites:** Python 3.x, Docker Desktop_

1. **Start Redis:**
```
bash
docker run -d --name redis-rl -p 6379:6379 redis
```

2. **Install dependencies:**
```
bash
pip install fastapi uvicorn redis
```

3. **Run the server:**
```
bash
uvicorn main:app --workers 4_
```

4. **Test it:**
```
bash
curl -i -H "X-Client-Id: client1" http://127.0.0.1:8000/check
curl -i -H "X-Client-Id: client1" "http://127.0.0.1:8000/check?mode=sliding"
```

**Load testing**
```
bash
k6 run loadtest.js
```

**Result**: 500 concurrent virtual users, 600+ requests/second sustained, correct allow/deny decisions throughout — with fewer than 1% of requests failing at the connection level (OS-level socket limits on a single local dev machine, not application logic).

# **What I'd add next**
1. Per-client configurable limits via an admin endpoint (currently global constants).
2. TTL on Redis keys so inactive clients' data expires automatically.
3. Distributed mode — multiple rate limiter instances sharing state correctly.
4. Production-grade deployment (multiple workers behind a load balancer, container orchestration).

# **What I learned**
1. Why elapsed-time-based refill (not fixed "ticks") is required for correctness.
2. How Redis's atomic command execution solves race conditions without manual locking.
3. Why persistence matters — proved it by draining a client's tokens, restarting the server, and confirming Redis remembered the state.
4. Real infrastructure debugging: Docker container lifecycle, WSL2 as Docker's engine on Windows, PowerShell's curl alias trap.
5. FastAPI specifics: header injection, custom response headers, and how exceptions bypass normal response objects.
