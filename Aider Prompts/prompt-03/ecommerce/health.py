import os
from django.http import JsonResponse
from django.db import connections
from django.db.utils import OperationalError

def healthz(request):
    db_ok = True
    redis_ok = True
    db_error = None
    redis_error = None

    try:
        with connections["default"].cursor() as cursor:
            cursor.execute("SELECT 1;")
            cursor.fetchone()
    except OperationalError as e:
        db_ok = False
        db_error = str(e)

    try:
        import redis
        r = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
        r.ping()
    except Exception as e:
        redis_ok = False
        redis_error = str(e)

    status = 200 if (db_ok and redis_ok) else 503
    return JsonResponse({"database": db_ok, "redis": redis_ok, "errors": {"database": db_error, "redis": redis_error}}, status=status)
