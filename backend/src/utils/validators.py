"""
Data validation utilities for fraud detection inputs.
"""

from typing import Any


class ValidationError(Exception):
    """Raised when validation fails."""

    pass


def validate_transaction(data: dict[str, Any]) -> dict[str, Any]:
    """
    Validate transaction data.

    Args:
        data: Transaction data dictionary

    Returns:
        Validated transaction data

    Raises:
        ValidationError: If validation fails
    """
    required_fields = ["transaction_id", "amount", "merchant_category", "merchant_name", "location"]

    for field in required_fields:
        if field not in data or data[field] is None:
            raise ValidationError(f"Missing required field: {field}")

    # Validate amount
    if not isinstance(data["amount"], (int, float)) or data["amount"] < 0:
        raise ValidationError("Amount must be a non-negative number")

    return data


def validate_insurance_claim(data: dict[str, Any]) -> dict[str, Any]:
    """
    Validate insurance claim data.

    Args:
        data: Insurance claim data dictionary

    Returns:
        Validated claim data

    Raises:
        ValidationError: If validation fails
    """
    required_fields = [
        "claim_id",
        "claim_amount",
        "claim_type",
        "incident_date",
        "filing_date",
        "description",
        "claimant_id",
    ]

    for field in required_fields:
        if field not in data or data[field] is None:
            raise ValidationError(f"Missing required field: {field}")

    # Validate claim amount
    if not isinstance(data["claim_amount"], (int, float)) or data["claim_amount"] < 0:
        raise ValidationError("Claim amount must be a non-negative number")

    return data


def validate_user_profile(data: dict[str, Any]) -> dict[str, Any]:
    """
    Validate user profile data.

    Args:
        data: User profile data dictionary

    Returns:
        Validated profile data

    Raises:
        ValidationError: If validation fails
    """
    required_fields = ["user_id", "email", "account_age_days"]

    for field in required_fields:
        if field not in data or data[field] is None:
            raise ValidationError(f"Missing required field: {field}")

    # Validate account age
    if not isinstance(data["account_age_days"], int) or data["account_age_days"] < 0:
        raise ValidationError("Account age must be a non-negative integer")

    # Basic email validation
    email = data.get("email", "")
    if "@" not in email or "." not in email:
        raise ValidationError("Invalid email format")

    return data


def validate_ecommerce_order(data: dict[str, Any]) -> dict[str, Any]:
    """
    Validate e-commerce order data.

    Args:
        data: E-commerce order data dictionary

    Returns:
        Validated order data

    Raises:
        ValidationError: If validation fails
    """
    required_fields = [
        "order_id",
        "order_total",
        "item_count",
        "shipping_address",
        "billing_address",
        "customer_id",
        "payment_method",
    ]

    for field in required_fields:
        if field not in data or data[field] is None:
            raise ValidationError(f"Missing required field: {field}")

    # Validate order total
    if not isinstance(data["order_total"], (int, float)) or data["order_total"] < 0:
        raise ValidationError("Order total must be a non-negative number")

    # Validate item count
    if not isinstance(data["item_count"], int) or data["item_count"] < 1:
        raise ValidationError("Item count must be a positive integer")

    return data
