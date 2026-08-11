"""
Thread-safe active tenant context management using Python contextvars.

Provides get/set functions for the current tenant that are safe across
threads (gunicorn workers) and coroutines (async views).
"""
import contextvars

_current_tenant = contextvars.ContextVar('current_tenant', default=None)


def set_current_tenant(tenant):
    """Set the active tenant in the current thread/coroutine context."""
    return _current_tenant.set(tenant)


def get_current_tenant():
    """Retrieve the active tenant from the current context. Returns None if unset."""
    return _current_tenant.get()
