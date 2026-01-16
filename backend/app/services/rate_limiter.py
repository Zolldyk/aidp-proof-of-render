"""
Rate Limiter Service

In-memory rate limiting with sliding window algorithm.
"""

import logging
from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import HTTPException, Request, status

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    In-memory rate limiter using sliding window algorithm.

    Tracks requests per IP address and enforces rate limits.
    """

    def __init__(self, max_requests: int, window_seconds: int):
        """
        Initialize rate limiter.

        Args:
            max_requests: Maximum number of requests allowed in time window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)  # IP -> list of timestamps

    def check_rate_limit(self, ip: str) -> None:
        """
        Check if IP has exceeded rate limit.

        Uses sliding window algorithm:
        1. Remove old requests outside time window
        2. Check if remaining requests exceed limit
        3. Record current request timestamp

        Args:
            ip: Client IP address

        Raises:
            HTTPException: 429 if rate limit exceeded
        """
        now = datetime.now()
        cutoff = now - timedelta(seconds=self.window_seconds)

        # Remove old requests outside window
        self.requests[ip] = [
            req_time for req_time in self.requests[ip]
            if req_time > cutoff
        ]

        # Check if limit exceeded
        if len(self.requests[ip]) >= self.max_requests:
            logger.warning(
                f"Rate limit exceeded for IP {ip}: "
                f"{len(self.requests[ip])} requests in window"
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Max {self.max_requests} uploads per hour."
            )

        # Record this request
        self.requests[ip].append(now)
        logger.info(
            f"Rate limit check passed: {ip} has "
            f"{len(self.requests[ip])} requests in window"
        )


# Global rate limiter instance: 10 uploads per hour
upload_rate_limiter = RateLimiter(max_requests=10, window_seconds=3600)


async def check_upload_rate_limit(request: Request) -> None:
    """
    FastAPI dependency to check upload rate limit.

    Args:
        request: FastAPI Request object to extract client IP

    Raises:
        HTTPException: 429 if rate limit exceeded
    """
    client_ip = request.client.host
    upload_rate_limiter.check_rate_limit(client_ip)
