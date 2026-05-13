"""
Base Agent Module
=================

Provides the abstract base class for all fraud detection agents.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import logging


class RiskLevel(Enum):
    """Risk classification levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class FraudSignal:
    """Represents a single fraud indicator signal"""

    name: str
    description: str
    weight: float  # 0.0 to 1.0
    category: str
    evidence: Optional[str] = None


@dataclass
class AgentResult:
    """Standardized result from any fraud detection agent"""

    agent_name: str
    entity_id: str
    risk_score: float  # 0.0 to 100.0
    risk_level: RiskLevel
    signals: List[FraudSignal] = field(default_factory=list)
    recommendation: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0  # 0.0 to 1.0


class BaseAgent(ABC):
    """Abstract base class for all fraud detection agents"""

    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(name)

        # Configure logging if not already done
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(
                logging.Formatter(
                    "[%(asctime)s] [%(name)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
                )
            )
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    @abstractmethod
    def analyze(self, data: Dict[str, Any]) -> AgentResult:
        """
        Analyze data and return fraud detection result.

        Args:
            data: The data to analyze (transaction, claim, profile, order, etc.)

        Returns:
            AgentResult with risk score, signals, and recommendation
        """
        pass

    def log(self, message: str):
        """Log a message with agent name prefix"""
        self.logger.info(f"[{self.name}] {message}")

    def _calculate_risk_level(self, score: float) -> RiskLevel:
        """Convert numeric score to risk level"""
        if score >= 80:
            return RiskLevel.CRITICAL
        elif score >= 60:
            return RiskLevel.HIGH
        elif score >= 40:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW

    def _create_result(
        self,
        entity_id: str,
        risk_score: float,
        signals: List[FraudSignal],
        recommendation: str = "",
        details: Dict[str, Any] = None,
        confidence: float = 0.8,
    ) -> AgentResult:
        """Helper to create standardized result"""
        return AgentResult(
            agent_name=self.name,
            entity_id=entity_id,
            risk_score=min(100, max(0, risk_score)),
            risk_level=self._calculate_risk_level(risk_score),
            signals=signals,
            recommendation=recommendation,
            details=details or {},
            confidence=confidence,
        )
