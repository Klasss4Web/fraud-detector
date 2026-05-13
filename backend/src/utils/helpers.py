"""
Helper utilities for fraud detection.
"""

import uuid
import re
import hashlib
from datetime import datetime, timedelta
from typing import Any, Optional


def generate_entity_id(prefix: str = "ENT") -> str:
    """
    Generate a unique entity ID.

    Args:
        prefix: ID prefix (e.g., "TXN", "CLM", "USR")

    Returns:
        Unique entity ID string
    """
    unique_part = uuid.uuid4().hex[:12].upper()
    return f"{prefix}-{unique_part}"


def calculate_time_delta(start_time: str, end_time: str) -> timedelta:
    """
    Calculate time difference between two ISO timestamps.

    Args:
        start_time: Start time in ISO format
        end_time: End time in ISO format

    Returns:
        Time delta between the two times
    """
    formats = [
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ]

    start_dt = None
    end_dt = None

    for fmt in formats:
        try:
            start_dt = datetime.strptime(start_time, fmt)
            break
        except ValueError:
            continue

    for fmt in formats:
        try:
            end_dt = datetime.strptime(end_time, fmt)
            break
        except ValueError:
            continue

    if start_dt is None or end_dt is None:
        raise ValueError("Could not parse timestamps")

    return end_dt - start_dt


def mask_sensitive_data(
    data: dict[str, Any], fields_to_mask: Optional[list[str]] = None
) -> dict[str, Any]:
    """
    Mask sensitive PII data before sending to external services.

    Args:
        data: Data dictionary containing potentially sensitive information
        fields_to_mask: List of field names to mask (uses defaults if None)

    Returns:
        Data with sensitive fields masked
    """
    default_sensitive_fields = [
        "ssn",
        "social_security",
        "social_security_number",
        "credit_card",
        "card_number",
        "cvv",
        "cvc",
        "password",
        "pin",
        "secret",
        "account_number",
        "routing_number",
        "date_of_birth",
        "dob",
    ]

    fields = fields_to_mask or default_sensitive_fields
    masked_data = data.copy()

    def mask_value(value: str, show_last: int = 4) -> str:
        """Mask a string value, showing only last N characters."""
        if len(value) <= show_last:
            return "*" * len(value)
        return "*" * (len(value) - show_last) + value[-show_last:]

    def process_dict(d: dict, parent_key: str = "") -> dict:
        """Recursively process dictionary to mask sensitive fields."""
        result = {}
        for key, value in d.items():
            full_key = f"{parent_key}.{key}" if parent_key else key
            lower_key = key.lower()

            if any(field in lower_key for field in fields):
                if isinstance(value, str):
                    result[key] = mask_value(value)
                elif isinstance(value, (int, float)):
                    result[key] = "***MASKED***"
                else:
                    result[key] = "***MASKED***"
            elif isinstance(value, dict):
                result[key] = process_dict(value, full_key)
            elif isinstance(value, list):
                result[key] = [
                    process_dict(item, full_key) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                result[key] = value

        return result

    return process_dict(masked_data)


def mask_email(email: str) -> str:
    """
    Mask an email address for privacy.

    Args:
        email: Email address to mask

    Returns:
        Masked email (e.g., "j***@example.com")
    """
    if "@" not in email:
        return mask_sensitive_data({"email": email}, ["email"])["email"]

    local, domain = email.rsplit("@", 1)
    if len(local) <= 2:
        masked_local = local[0] + "*"
    else:
        masked_local = local[0] + "*" * (len(local) - 2) + local[-1]

    return f"{masked_local}@{domain}"


def mask_ip_address(ip: str) -> str:
    """
    Partially mask an IP address.

    Args:
        ip: IP address to mask

    Returns:
        Masked IP (e.g., "192.168.xxx.xxx")
    """
    parts = ip.split(".")
    if len(parts) == 4:
        return f"{parts[0]}.{parts[1]}.xxx.xxx"
    return ip


def hash_for_dedup(data: dict[str, Any]) -> str:
    """
    Create a hash for deduplication purposes.

    Args:
        data: Data to hash

    Returns:
        SHA-256 hash string
    """
    import json

    serialized = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode()).hexdigest()


def is_disposable_email_domain(email: str) -> bool:
    """
    Check if an email uses a known disposable email domain.

    Args:
        email: Email address to check

    Returns:
        True if domain is likely disposable
    """
    disposable_domains = {
        "tempmail.com",
        "throwaway.email",
        "guerrillamail.com",
        "10minutemail.com",
        "mailinator.com",
        "yopmail.com",
        "temp-mail.org",
        "fakeinbox.com",
        "trashmail.com",
        "tempail.com",
        "tmpmail.org",
        "getnada.com",
        "sharklasers.com",
        "guerrillamailblock.com",
        "spam4.me",
    }

    if "@" not in email:
        return False

    domain = email.rsplit("@", 1)[1].lower()

    # Check exact match
    if domain in disposable_domains:
        return True

    # Check for common patterns
    suspicious_patterns = ["temp", "throw", "fake", "trash", "spam", "disposable"]
    return any(pattern in domain for pattern in suspicious_patterns)


def extract_domain_from_email(email: str) -> str:
    """
    Extract domain from email address.

    Args:
        email: Email address

    Returns:
        Domain portion of email
    """
    if "@" not in email:
        return ""
    return email.rsplit("@", 1)[1].lower()
