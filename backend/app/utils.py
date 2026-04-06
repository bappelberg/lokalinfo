from fastapi import Request


def get_client_ip(request: Request) -> str:
    """Get real client IP — reads x-real-ip header set by Next.js proxy, falls back to direct connection."""
    forwarded = request.headers.get("x-real-ip")
    if forwarded:
        return forwarded
    return request.client.host
