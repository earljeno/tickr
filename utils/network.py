import os

from flask import has_request_context, request

DEFAULT_WHITELIST = {
    "localhost",
    "127.0.0.1",
    "::1",
    "172.16.255.237",  # GIA Station
    "172.16.255.236",  # Printing 1
    "172.16.254.255",  # Printing 2
}

DEFAULT_SPECIAL_IDS = {
    "2024998",
}


def get_whitelist() -> set[str]:
    env_val = os.getenv("IP_WHITELIST")
    if env_val:
        return {ip.strip() for ip in env_val.split(",") if ip.strip()}
    return DEFAULT_WHITELIST


def get_special_ids() -> set[str]:
    env_val = os.getenv("SPECIAL_USER_IDS")
    if env_val:
        return {uid.strip() for uid in env_val.split(",") if uid.strip()}
    return DEFAULT_SPECIAL_IDS


def get_client_ip() -> str:
    """Resolve the client IP address from proxy headers or remote addr."""
    if not has_request_context():
        return "127.0.0.1"

    # Cloudflare real client IP
    cf_ip = request.headers.get("CF-Connecting-IP")
    if cf_ip:
        return cf_ip.strip()

    # Generic proxy header
    xff = request.headers.get("X-Forwarded-For")
    if xff:
        return xff.split(",")[0].strip()

    # Direct connection
    return request.remote_addr or "127.0.0.1"


def is_ip_whitelisted(client_ip: str | None = None, user_id: str | None = None) -> bool:
    """Check if the client IP is allowed or exempted."""
    special_ids = get_special_ids()
    if user_id and str(user_id) in special_ids:
        return True

    ip = client_ip or get_client_ip()
    return ip in get_whitelist()
