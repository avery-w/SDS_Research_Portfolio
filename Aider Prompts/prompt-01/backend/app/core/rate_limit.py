from fastapi_limiter import FastAPILimiter
import redis.asyncio as redis
from fastapi import FastAPI

async def init_rate_limiter(app: FastAPI):
    r = redis.from_url("redis://localhost:6379/0", encoding="utf-8", decode_responses=True)
    await FastAPILimiter.init(r)
