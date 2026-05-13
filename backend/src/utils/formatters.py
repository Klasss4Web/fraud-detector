"""
Formatting utilities for fraud detection outputs.
"""

from typing import Optional


def format_risk_score(score: float, include_level: bool = True) -> str:
    """
    Format a risk score for display.

    Args:
        score: Risk score (0-100)
        include_level: Whether to include the risk level label

    Returns:
        Formatted risk score string
    """
    score = max(0, min(100, score))

    if include_level:
        if score >= 80:
            level = "CRITICAL"
        elif score >= 60:
            level = "HIGH"
        elif score >= 40:
            level = "MEDIUM"
        else:
            level = "LOW"
        return f"{score:.1f}/100 ({level})"

    return f"{score:.1f}/100"


def format_currency(amount: float, currency: str = "USD", symbol: Optional[str] = None) -> str:
    """
    Format a monetary amount.

    Args:
        amount: The amount to format
        currency: Currency code
        symbol: Currency symbol (optional, defaults based on currency)

    Returns:
        Formatted currency string
    """
    symbols = {
        "USD": "$",
        "EUR": "€",
        "GBP": "£",
        "CAD": "C$",
        "AUD": "A$",
        "JPY": "¥",
    }

    sym = symbol or symbols.get(currency, currency + " ")

    if currency == "JPY":
        return f"{sym}{amount:,.0f}"

    return f"{sym}{amount:,.2f}"


def format_percentage(value: float, decimal_places: int = 1) -> str:
    """
    Format a value as a percentage.

    Args:
        value: The value to format (0-1 or 0-100)
        decimal_places: Number of decimal places

    Returns:
        Formatted percentage string
    """
    # Normalize to percentage if needed
    if 0 <= value <= 1:
        value = value * 100

    return f"{value:.{decimal_places}f}%"


def format_signal_severity(weight: float) -> str:
    """
    Format a signal weight as severity level.

    Args:
        weight: Signal weight (0-1)

    Returns:
        Severity label (HIGH, MEDIUM, LOW)
    """
    if weight >= 0.7:
        return "HIGH"
    elif weight >= 0.4:
        return "MEDIUM"
    return "LOW"


def format_entity_type(entity_type: str) -> str:
    """
    Format entity type for display.

    Args:
        entity_type: Raw entity type string

    Returns:
        Formatted entity type
    """
    type_labels = {
        "transaction": "Financial Transaction",
        "claim": "Insurance Claim",
        "profile": "User Profile",
        "order": "E-Commerce Order",
        "comprehensive": "Comprehensive Analysis",
    }
    return type_labels.get(entity_type, entity_type.title())
