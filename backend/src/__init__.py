"""
Fraud Detection System - Multi-agent AI for comprehensive fraud detection.

This package provides specialized AI agents for detecting fraud across:
- Financial transactions
- Insurance claims
- Identity verification
- E-commerce orders
"""

from .orchestrator import FraudDetectionOrchestrator

__version__ = "0.1.0"
__all__ = ["FraudDetectionOrchestrator"]
