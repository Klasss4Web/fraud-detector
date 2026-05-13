"""
Agents Module
=============

Export all fraud detection agents.
"""

from .base_agent import BaseAgent, AgentResult, FraudSignal, RiskLevel
from .transaction_agent import TransactionFraudAgent
from .insurance_agent import InsuranceFraudAgent
from .identity_agent import IdentityFraudAgent
from .ecommerce_agent import EcommerceFraudAgent
from .risk_scoring_agent import RiskScoringAgent, AggregatedRisk
from .investigation_agent import InvestigationAgent
from .fraud_simulation_agent import FraudSimulationAgent
from .simulation_agent import SimulationAgent

__all__ = [
    "BaseAgent",
    "AgentResult",
    "FraudSignal",
    "RiskLevel",
    "TransactionFraudAgent",
    "InsuranceFraudAgent",
    "IdentityFraudAgent",
    "EcommerceFraudAgent",
    "RiskScoringAgent",
    "AggregatedRisk",
    "InvestigationAgent",
    "FraudSimulationAgent",
    "SimulationAgent",
]
