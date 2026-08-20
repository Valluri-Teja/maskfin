"""
rate_limit.py
A simple per-session rate limit for the public deployment, since
maskfin.onrender.com is a free-tier, publicly accessible instance with
no authentication. Limiting redactions per session prevents any single
user (or bot) from monopolizing the shared free-tier compute/API quota.

Deliberately simple: in-memory, per-Streamlit-session counting, not a
distributed rate limiter (Redis, etc). That would be the right upgrade
for a real production deployment with multiple server instances behind
a load balancer - documented as a known limitation rather than
over-built for a single free-tier instance.
"""

DEFAULT_LIMIT = 20


def check_rate_limit(current_count: int, requested: int, limit: int = DEFAULT_LIMIT) -> tuple:
    """
    Returns (allowed: bool, message: str).
    `requested` is how many redactions this action would add (1 for a
    single-file redact, len(files) for a batch).
    """
    if requested <= 0:
        return True, ""

    projected = current_count + requested
    if projected > limit:
        remaining = max(0, limit - current_count)
        return False, (
            f"Session limit reached: {limit} redactions per session on this "
            f"free deployment. You have {remaining} remaining this session "
            f"(requested {requested}). Refresh the page to start a new session, "
            f"or run this locally for unlimited use."
        )
    return True, ""
