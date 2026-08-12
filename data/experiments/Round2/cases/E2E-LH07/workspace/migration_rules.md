# v3 migration

All services: schema_version=3, runtime.channel=stable, compat.api=v3.
service-03: replace database with storage {dsn: old url, pool_size: old pool}.
service-07: replace auth with security {session_ttl_seconds: old token_ttl, provider: old provider}.
