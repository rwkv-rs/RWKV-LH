def is_fresh(created_at, now, ttl):
    """Whether a cached value can be reused at this instant."""
    if ttl < 0 or now < created_at:
        raise ValueError("invalid cache clock or TTL")
    return now - created_at <= ttl
