"""Network safeguards shared by tools that accept a user-controlled URL."""

from __future__ import annotations

import asyncio
import ipaddress
import socket
from urllib.parse import urlparse


async def validate_public_url(value: str) -> str:
    """Reject non-HTTP and private-network targets to prevent SSRF."""
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("URL must be an absolute http(s) URL")
    if parsed.username or parsed.password or (parsed.port and parsed.port not in {80, 443}):
        raise ValueError("URL credentials and non-standard ports are not allowed")
    try:
        addresses = await asyncio.get_running_loop().getaddrinfo(
            parsed.hostname, None, family=socket.AF_UNSPEC, type=socket.SOCK_STREAM
        )
    except socket.gaierror as exc:
        raise ValueError("URL host could not be resolved") from exc
    for address in {item[4][0] for item in addresses}:
        if not ipaddress.ip_address(address).is_global:
            raise ValueError("private or reserved network targets are not allowed")
    return value
