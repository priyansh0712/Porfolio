"""
Rate Limiting Utility — Application-Level IP Sliding Window Rate Limiter.

Architecture (SEC-01):
  - Uses Django's cache backend (Redis / LocMemCache) to track request timestamps per IP.
  - Returns HTTP 429 Too Many Requests when rate threshold is exceeded.
"""
import functools
import time
from django.core.cache import cache
from django.http import JsonResponse, HttpResponse


def get_client_ip(request):
    """Extracts client IP address from HTTP request headers."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '127.0.0.1')


def rate_limit(key_prefix='rl', limit=10, period_seconds=60):
    """
    Decorator for views to enforce rate limits per client IP.

    Args:
        key_prefix: String prefix for cache key isolation.
        limit: Max allowed requests within period_seconds.
        period_seconds: Time window in seconds (default 60s).
    """
    def decorator(view_func):
        @functools.wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            client_ip = get_client_ip(request)
            cache_key = f"ratelimit:{key_prefix}:{client_ip}"
            now = time.time()

            timestamps = cache.get(cache_key, [])
            # Filter out timestamps outside current time window
            cutoff = now - period_seconds
            valid_timestamps = [ts for ts in timestamps if ts > cutoff]

            if len(valid_timestamps) >= limit:
                if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('accept', ''):
                    return JsonResponse(
                        {'error': 'Too many requests. Please slow down.'},
                        status=429,
                    )
                return HttpResponse('429 Too Many Requests — Please try again later.', status=429)

            valid_timestamps.append(now)
            cache.set(cache_key, valid_timestamps, timeout=period_seconds + 5)

            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator
