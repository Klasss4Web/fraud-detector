"""
Fraud Detection Orchestrator
=============================

Central coordinator that manages all fraud detection agents
and provides a unified interface for fraud analysis.
"""

import logging
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from uuid import uuid4

from src.agents import (
    TransactionFraudAgent,
    InsuranceFraudAgent,
    IdentityFraudAgent,
    EcommerceFraudAgent,
    RiskScoringAgent,
    InvestigationAgent,
    AgentResult,
    AggregatedRisk,
    RiskLevel,
)

# ML Integration
try:
    from ml import get_fraud_model, get_feedback_collector, FraudModel, FeatureSet

    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    get_fraud_model = None
    get_feedback_collector = None

# Metrics Integration
try:
    from observability import get_fraud_metrics, get_evaluation_store, get_feedback_loop

    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False
    get_fraud_metrics = None
    get_evaluation_store = None
    get_feedback_loop = None


class EntityType(Enum):
    """Supported entity types for fraud detection"""

    TRANSACTION = "transaction"
    INSURANCE_CLAIM = "claim"
    USER_PROFILE = "profile"
    ECOMMERCE_ORDER = "order"


@dataclass
class FraudAnalysisResult:
    """Complete fraud analysis result"""

    entity_id: str
    entity_type: str
    risk_score: float
    risk_level: str
    requires_action: bool
    recommendation: str
    signals: List[Dict[str, Any]]
    agent_results: Dict[str, float]
    investigation_report: Optional[Dict[str, Any]] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)
    # ML metadata
    prediction_id: Optional[str] = None
    model_name: Optional[str] = None
    model_version: Optional[str] = None
    ml_confidence: Optional[float] = None


class FraudDetectionOrchestrator:
    def __init__(
        self,
        enable_llm: bool = True,
        openai_api_key: str = None,
        auto_investigate_threshold: float = 60.0,
        enable_ml: bool = True,
        ml_model_name: Optional[str] = None,
    ):
        """
        Initialize the orchestrator.

        Args:
            enable_llm: Whether to enable LLM-powered investigation
            openai_api_key: OpenAI API key for investigation agent
            auto_investigate_threshold: Risk score threshold for auto-investigation
            enable_ml: Whether to enable ML model scoring
            ml_model_name: Specific ML model to use (None for default)
        """
        self.logger = logging.getLogger("FraudOrchestrator")
        self._setup_logging()

        # Store API key for LLM agents
        self.api_key = openai_api_key

        # Initialize specialized agents
        self.transaction_agent = TransactionFraudAgent()
        self.insurance_agent = InsuranceFraudAgent()
        self.identity_agent = IdentityFraudAgent()
        self.ecommerce_agent = EcommerceFraudAgent()

        # Initialize meta agents
        self.risk_scorer = RiskScoringAgent()

        if enable_llm:
            self.investigation_agent = InvestigationAgent(api_key=openai_api_key)
        else:
            self.investigation_agent = None

        self.auto_investigate_threshold = auto_investigate_threshold

        # Initialize ML components
        self.enable_ml = enable_ml and ML_AVAILABLE
        self.ml_model: Optional[FraudModel] = None
        self.feedback_collector = None

        if self.enable_ml:
            try:
                self.ml_model = get_fraud_model(ml_model_name)
                self.feedback_collector = get_feedback_collector()
                self.logger.info(
                    f"ML model initialized: {self.ml_model.name} v{self.ml_model.version}"
                )
            except Exception as e:
                self.logger.warning(f"Failed to initialize ML model: {e}")
                self.enable_ml = False
        else:
            if not ML_AVAILABLE:
                self.logger.info("ML module not available, using rule-based scoring only")

        # Initialize metrics
        self.metrics = None
        self.evaluation_store = None
        self.feedback_loop = None
        if METRICS_AVAILABLE:
            try:
                self.metrics = get_fraud_metrics()
                self.evaluation_store = get_evaluation_store()
                self.feedback_loop = get_feedback_loop()
                self.logger.info("Metrics and evaluation collection enabled")
            except Exception as e:
                self.logger.warning(f"Failed to initialize metrics: {e}")

        self.logger.info("Fraud Detection Orchestrator initialized")

    def run_adversarial_test(self, scheme: str, intensity: str = "medium"):
        """
        Simulates an LLM-generated attack and checks if the system caught it.
        """
        from agents import SimulationAgent

        simulator = SimulationAgent(
            api_key=getattr(self, "api_key", None) or getattr(self, "openai_api_key", None)
        )
        # 1. Generate the 'Fake' Fraud
        attack_payload = simulator.generate_attack(scheme, intensity)
        # 2. Run all transactions through the detection pipeline
        results = []
        for txn in attack_payload:
            result = self.analyze_transaction(txn, auto_investigate=True)
            was_caught = result.risk_score >= self.auto_investigate_threshold
            results.append(
                {
                    "transaction": txn,
                    "detected": was_caught,
                    "score": result.risk_score,
                    "analysis": result.investigation_report.get("llm_analysis")
                    if result.investigation_report
                    else "No LLM analysis",
                }
            )
        return {"attack_payload": attack_payload, "results": results}

    """
    Orchestrates multiple fraud detection agents to provide
    comprehensive fraud analysis.
    """

    def _setup_logging(self):
        """Configure logging"""
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(
                logging.Formatter(
                    "[%(asctime)s] [%(name)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
                )
            )
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def analyze_transaction(
        self, transaction_data: Dict[str, Any], auto_investigate: bool = True
    ) -> FraudAnalysisResult:
        """
        Analyze a financial transaction for fraud.

        Args:
            transaction_data: Transaction record
            auto_investigate: Whether to auto-investigate high-risk cases

        Returns:
            FraudAnalysisResult
        """
        self.logger.info(
            f"Analyzing transaction {transaction_data.get('transaction_id', 'unknown')}"
        )

        # Run transaction agent
        result = self.transaction_agent.analyze(transaction_data)

        # Aggregate (single agent, but maintains consistent interface)
        aggregated = self.risk_scorer.aggregate(
            results=[result],
            entity_id=transaction_data.get("transaction_id", "unknown"),
            entity_type=EntityType.TRANSACTION.value,
        )

        return self._build_result(
            aggregated=aggregated,
            raw_data=transaction_data,
            auto_investigate=auto_investigate,
        )

    def analyze_insurance_claim(
        self, claim_data: Dict[str, Any], auto_investigate: bool = True
    ) -> FraudAnalysisResult:
        """
        Analyze an insurance claim for fraud.

        Args:
            claim_data: Insurance claim record
            auto_investigate: Whether to auto-investigate high-risk cases

        Returns:
            FraudAnalysisResult
        """
        self.logger.info(f"Analyzing claim {claim_data.get('claim_id', 'unknown')}")

        result = self.insurance_agent.analyze(claim_data)

        aggregated = self.risk_scorer.aggregate(
            results=[result],
            entity_id=claim_data.get("claim_id", "unknown"),
            entity_type=EntityType.INSURANCE_CLAIM.value,
        )

        return self._build_result(
            aggregated=aggregated,
            raw_data=claim_data,
            auto_investigate=auto_investigate,
        )

    def analyze_user_profile(
        self, profile_data: Dict[str, Any], auto_investigate: bool = True
    ) -> FraudAnalysisResult:
        """
        Analyze a user profile for identity fraud.

        Args:
            profile_data: User profile record
            auto_investigate: Whether to auto-investigate high-risk cases

        Returns:
            FraudAnalysisResult
        """
        self.logger.info(f"Analyzing profile {profile_data.get('user_id', 'unknown')}")

        result = self.identity_agent.analyze(profile_data)

        aggregated = self.risk_scorer.aggregate(
            results=[result],
            entity_id=profile_data.get("user_id", "unknown"),
            entity_type=EntityType.USER_PROFILE.value,
        )

        return self._build_result(
            aggregated=aggregated,
            raw_data=profile_data,
            auto_investigate=auto_investigate,
        )

    def analyze_ecommerce_order(
        self, order_data: Dict[str, Any], auto_investigate: bool = True
    ) -> FraudAnalysisResult:
        """
        Analyze an e-commerce order for fraud.

        Args:
            order_data: E-commerce order record
            auto_investigate: Whether to auto-investigate high-risk cases

        Returns:
            FraudAnalysisResult
        """
        self.logger.info(f"Analyzing order {order_data.get('order_id', 'unknown')}")

        result = self.ecommerce_agent.analyze(order_data)

        aggregated = self.risk_scorer.aggregate(
            results=[result],
            entity_id=order_data.get("order_id", "unknown"),
            entity_type=EntityType.ECOMMERCE_ORDER.value,
        )

        return self._build_result(
            aggregated=aggregated,
            raw_data=order_data,
            auto_investigate=auto_investigate,
        )

    def analyze_comprehensive(
        self,
        transaction_data: Dict[str, Any] = None,
        user_profile: Dict[str, Any] = None,
        order_data: Dict[str, Any] = None,
        auto_investigate: bool = True,
    ) -> FraudAnalysisResult:
        """
        Perform comprehensive analysis combining multiple data sources.

        This is useful when you have related data (e.g., a transaction
        and the user profile of the person making it).

        Args:
            transaction_data: Optional transaction data
            user_profile: Optional user profile data
            order_data: Optional order data
            auto_investigate: Whether to auto-investigate high-risk cases

        Returns:
            FraudAnalysisResult with combined analysis
        """
        self.logger.info("Performing comprehensive multi-source analysis")

        results = []
        entity_id = "comprehensive"

        if transaction_data:
            results.append(self.transaction_agent.analyze(transaction_data))
            entity_id = transaction_data.get("transaction_id", entity_id)

        if user_profile:
            results.append(self.identity_agent.analyze(user_profile))
            entity_id = user_profile.get("user_id", entity_id)

        if order_data:
            results.append(self.ecommerce_agent.analyze(order_data))
            entity_id = order_data.get("order_id", entity_id)

        if not results:
            raise ValueError("At least one data source must be provided")

        aggregated = self.risk_scorer.aggregate(
            results=results, entity_id=entity_id, entity_type="comprehensive"
        )

        # Combine raw data
        combined_data = {}
        if transaction_data:
            combined_data["transaction"] = transaction_data
        if user_profile:
            combined_data["user_profile"] = user_profile
        if order_data:
            combined_data["order"] = order_data

        return self._build_result(
            aggregated=aggregated,
            raw_data=combined_data,
            auto_investigate=auto_investigate,
        )

    def _build_result(
        self,
        aggregated: AggregatedRisk,
        raw_data: Dict[str, Any],
        auto_investigate: bool,
    ) -> FraudAnalysisResult:
        """Build final result with optional investigation and ML scoring"""

        # Generate prediction ID for tracking
        prediction_id = str(uuid4())

        # Get ML model prediction if available
        ml_prediction = None
        ml_confidence = None
        model_name = None
        model_version = None

        if self.enable_ml and self.ml_model:
            try:
                ml_prediction = self.ml_model.predict_from_raw(raw_data, return_explanation=True)
                ml_confidence = ml_prediction.confidence
                model_name = ml_prediction.model_name
                model_version = ml_prediction.model_version

                # Blend ML score with rule-based score
                # Weight: 60% rules, 40% ML (adjustable)
                rule_weight = 0.6
                ml_weight = 0.4
                blended_score = (
                    aggregated.final_risk_score * rule_weight + ml_prediction.risk_score * ml_weight
                )

                self.logger.debug(
                    f"Score blending: rules={aggregated.final_risk_score:.1f}, "
                    f"ml={ml_prediction.risk_score:.1f}, blended={blended_score:.1f}"
                )

                # Update the aggregated score with blended score
                original_score = aggregated.final_risk_score
                aggregated.final_risk_score = blended_score

                # Add ML features to signals if they contributed
                if ml_prediction.top_features:
                    for feature in ml_prediction.top_features[:3]:  # Top 3 ML features
                        aggregated.top_signals.append(
                            type(aggregated.top_signals[0])(
                                name=f"ml_{feature.get('feature', 'unknown')}",
                                description=f"ML signal: {feature.get('feature', 'unknown')}",
                                weight=feature.get("contribution", 0) / 100,
                                category="ml_model",
                            )
                            if aggregated.top_signals
                            else None
                        )

            except Exception as e:
                self.logger.warning(f"ML prediction failed, using rules only: {e}")

        # Perform investigation if warranted
        investigation_report = None
        if (
            auto_investigate
            and self.investigation_agent
            and aggregated.final_risk_score >= self.auto_investigate_threshold
        ):
            self.logger.info(
                f"Auto-investigating high-risk case (score: {aggregated.final_risk_score})"
            )
            investigation_report = self.investigation_agent.investigate(
                aggregated_risk=aggregated, raw_data=raw_data
            )

        # Build signals list
        signals = [
            {
                "name": s.name,
                "description": s.description,
                "weight": s.weight,
                "category": s.category,
            }
            for s in aggregated.top_signals
            if s is not None
        ]

        # Determine decision for feedback tracking
        decision = (
            "block"
            if aggregated.final_risk_score >= 60
            else ("review" if aggregated.final_risk_score >= 40 else "allow")
        )

        # Record prediction for feedback loop
        if self.enable_ml and self.feedback_collector:
            try:
                self.feedback_collector.record_prediction(
                    prediction_id=prediction_id,
                    transaction_id=aggregated.entity_id,
                    model_name=model_name or "rule_based",
                    model_version=model_version or "1.0.0",
                    risk_score=aggregated.final_risk_score,
                    confidence=ml_confidence or 0.8,
                    decision=decision,
                    features=raw_data,
                )
            except Exception as e:
                self.logger.warning(f"Failed to record prediction for feedback: {e}")

        # Record metrics
        if self.metrics:
            try:
                # Record alert received
                self.metrics.record_alert_received(
                    entity_type=aggregated.entity_type,
                    source="api",
                )

                # Record alert processed with decision
                severity = (
                    aggregated.risk_level.value
                    if hasattr(aggregated.risk_level, "value")
                    else str(aggregated.risk_level)
                )
                self.metrics.record_alert_processed(
                    entity_type=aggregated.entity_type,
                    severity=severity,
                    decision=decision,
                    processing_time=0.0,  # Would need to track actual time
                )

                # Record decision
                self.metrics.record_decision(
                    action=decision,
                    confidence=ml_confidence or 0.8,
                    risk_score=aggregated.final_risk_score,
                    entity_type=aggregated.entity_type,
                )

                # Record escalation if high risk
                if aggregated.requires_investigation:
                    self.metrics.record_escalation(reason="high_risk_score")

            except Exception as e:
                self.logger.warning(f"Failed to record metrics: {e}")

        # Record agent execution in evaluation store
        if self.evaluation_store:
            try:
                for agent_name, score in aggregated.agent_scores.items():
                    self.evaluation_store.record_agent_execution(
                        agent_name=agent_name,
                        success=True,
                        execution_time=0.05,  # Approximate - would need actual timing
                    )
                # Also record the RiskScoringAgent
                self.evaluation_store.record_agent_execution(
                    agent_name="RiskScoringAgent",
                    success=True,
                    execution_time=0.02,
                )
            except Exception as e:
                self.logger.warning(f"Failed to record agent execution: {e}")

        return FraudAnalysisResult(
            entity_id=aggregated.entity_id,
            entity_type=aggregated.entity_type,
            risk_score=aggregated.final_risk_score,
            risk_level=aggregated.risk_level.value,
            requires_action=aggregated.requires_investigation,
            recommendation=aggregated.recommendation,
            signals=signals,
            agent_results=aggregated.agent_scores,
            investigation_report=investigation_report,
            raw_data=raw_data,
            prediction_id=prediction_id,
            model_name=model_name,
            model_version=model_version,
            ml_confidence=ml_confidence,
        )

    def batch_analyze(
        self,
        items: List[Dict[str, Any]],
        entity_type: EntityType,
        auto_investigate: bool = False,
    ) -> List[FraudAnalysisResult]:
        """
        Analyze multiple items in batch.

        Args:
            items: List of data records
            entity_type: Type of entities being analyzed
            auto_investigate: Whether to auto-investigate high-risk cases

        Returns:
            List of FraudAnalysisResult, sorted by risk score
        """
        self.logger.info(f"Batch analyzing {len(items)} {entity_type.value}s")

        analyze_func = {
            EntityType.TRANSACTION: self.analyze_transaction,
            EntityType.INSURANCE_CLAIM: self.analyze_insurance_claim,
            EntityType.USER_PROFILE: self.analyze_user_profile,
            EntityType.ECOMMERCE_ORDER: self.analyze_ecommerce_order,
        }[entity_type]

        results = []
        for item in items:
            try:
                result = analyze_func(item, auto_investigate=auto_investigate)
                results.append(result)
            except Exception as e:
                self.logger.error(f"Error analyzing item: {e}")

        # Sort by risk score (highest first)
        results.sort(key=lambda x: x.risk_score, reverse=True)

        return results

    def record_outcome(
        self,
        prediction_id: Optional[str] = None,
        transaction_id: Optional[str] = None,
        outcome: str = "unknown",
        outcome_details: Optional[Dict[str, Any]] = None,
        risk_score: Optional[float] = None,
        entity_type: str = "transaction",
    ) -> bool:
        """
        Record the outcome of a prediction for feedback loop.

        This should be called when you learn the true outcome of a transaction:
        - Chargeback received
        - Fraud confirmed by analyst
        - False positive identified
        - Customer confirmed legitimate

        Args:
            prediction_id: ID returned from analyze_* methods
            transaction_id: Original transaction ID (fallback lookup)
            outcome: One of: chargeback, fraud_report, analyst_confirmed,
                     analyst_dismissed, customer_confirmed
            outcome_details: Additional info (amount, reason, etc.)
            risk_score: Original risk score (for evaluation)
            entity_type: Type of entity

        Returns:
            True if outcome was recorded successfully
        """
        recorded = False

        # Record in ML feedback collector
        if self.enable_ml and self.feedback_collector:
            try:
                self.feedback_collector.record_outcome(
                    prediction_id=prediction_id,
                    transaction_id=transaction_id,
                    outcome=outcome,
                    outcome_details=outcome_details,
                )
                recorded = True
            except Exception as e:
                self.logger.warning(f"Failed to record ML feedback: {e}")

        # Record in evaluation store for confusion matrix
        if self.feedback_loop:
            try:
                original_decision = "block" if (risk_score or 0) >= 60 else "allow"

                if outcome in ["chargeback", "fraud_report"]:
                    # Chargeback = confirmed fraud
                    self.feedback_loop.record_chargeback(
                        alert_id=prediction_id or transaction_id or "unknown",
                        entity_type=entity_type,
                        original_decision=original_decision,
                        risk_score=risk_score or 0,
                        confidence=0.8,
                    )
                    recorded = True
                elif outcome == "analyst_confirmed":
                    # Analyst confirmed fraud
                    self.feedback_loop.record_human_override(
                        alert_id=prediction_id or transaction_id or "unknown",
                        entity_type=entity_type,
                        agent_decision=original_decision,
                        human_decision="block",
                        risk_score=risk_score or 0,
                        confidence=0.8,
                        reason=outcome_details.get("reason", "") if outcome_details else "",
                    )
                    recorded = True
                elif outcome == "analyst_dismissed":
                    # Analyst dismissed (false positive)
                    self.feedback_loop.record_human_override(
                        alert_id=prediction_id or transaction_id or "unknown",
                        entity_type=entity_type,
                        agent_decision=original_decision,
                        human_decision="approve",
                        risk_score=risk_score or 0,
                        confidence=0.8,
                        reason=outcome_details.get("reason", "") if outcome_details else "",
                    )
                    recorded = True
                elif outcome == "customer_confirmed":
                    # Customer confirmed legitimate
                    self.feedback_loop.record_user_confirmation(
                        alert_id=prediction_id or transaction_id or "unknown",
                        entity_type=entity_type,
                        original_decision=original_decision,
                        risk_score=risk_score or 0,
                        confidence=0.8,
                        was_legitimate=True,
                    )
                    recorded = True

            except Exception as e:
                self.logger.warning(f"Failed to record evaluation feedback: {e}")

        if recorded:
            self.logger.info(f"Recorded outcome '{outcome}' for {prediction_id or transaction_id}")
        else:
            self.logger.warning("No feedback systems available")

        return recorded

    def get_feedback_stats(self) -> Optional[Dict[str, Any]]:
        """
        Get current feedback statistics and model performance.

        Returns:
            Dictionary with precision, recall, F1, and outcome breakdown
        """
        if not self.enable_ml or not self.feedback_collector:
            return None

        stats = self.feedback_collector.get_stats()
        return {
            "total_predictions": stats.total_predictions,
            "labeled_predictions": stats.labeled_predictions,
            "precision": round(stats.precision, 4),
            "recall": round(stats.recall, 4),
            "f1_score": round(stats.f1_score, 4),
            "false_positive_rate": round(stats.false_positive_rate, 4),
            "outcomes": {
                "chargebacks": stats.chargebacks,
                "fraud_reports": stats.fraud_reports,
                "analyst_confirmed": stats.analyst_confirmed,
                "analyst_dismissed": stats.analyst_dismissed,
                "time_decay": stats.time_decay,
            },
            "confusion_matrix": {
                "true_positives": stats.true_positives,
                "false_positives": stats.false_positives,
                "true_negatives": stats.true_negatives,
                "false_negatives": stats.false_negatives,
            },
            "should_retrain": self.feedback_collector.should_retrain(),
        }

    def check_model_retraining(self) -> Optional[Dict[str, Any]]:
        """
        Check if model should be retrained and get suggestions.

        Returns:
            Retraining suggestions if needed, None otherwise
        """
        if not self.enable_ml or not self.feedback_collector:
            return None

        if self.feedback_collector.should_retrain():
            return self.feedback_collector.trigger_retraining()

        return self.feedback_collector.suggest_threshold_adjustment()

    def get_high_risk_summary(
        self, results: List[FraudAnalysisResult], threshold: float = 60.0
    ) -> Dict[str, Any]:
        """
        Generate summary of high-risk cases.

        Args:
            results: List of analysis results
            threshold: Minimum risk score for high-risk

        Returns:
            Summary statistics and high-risk cases
        """
        high_risk = [r for r in results if r.risk_score >= threshold]

        return {
            "total_analyzed": len(results),
            "high_risk_count": len(high_risk),
            "high_risk_rate": len(high_risk) / len(results) * 100 if results else 0,
            "average_risk_score": sum(r.risk_score for r in results) / len(results)
            if results
            else 0,
            "risk_distribution": {
                "critical": len([r for r in results if r.risk_level == "critical"]),
                "high": len([r for r in results if r.risk_level == "high"]),
                "medium": len([r for r in results if r.risk_level == "medium"]),
                "low": len([r for r in results if r.risk_level == "low"]),
            },
            "high_risk_cases": [
                {
                    "entity_id": r.entity_id,
                    "risk_score": r.risk_score,
                    "recommendation": r.recommendation,
                }
                for r in high_risk[:10]  # Top 10
            ],
        }

    def simulate_fraud_attack(self, attack_type=None):
        """
        Run the FraudSimulationAgent to generate and analyze a synthetic attack.
        Returns the attack payload and the system's analysis result.
        """
        from agents import FraudSimulationAgent

        sim_agent = FraudSimulationAgent(self.api_key)
        attack = sim_agent.simulate_attack(attack_type)
        # For each transaction in the attack, run through orchestrator
        results = []
        for tx in attack["transactions"]:
            # Route to the appropriate agent (e.g., transaction or ecommerce)
            # Here, we assume transaction for demo; adapt as needed
            result = self.analyze_transaction(tx, auto_investigate=True)
            results.append(result)
        return {
            "attack_type": attack["type"],
            "description": attack["description"],
            "attack_payload": attack["transactions"],
            "analysis_results": [r.__dict__ for r in results],
        }

    def run_detection_score_analysis(
        self,
        attack_types: List[str] = None,
        simulations_per_type: int = 1,
        detection_threshold: float = None,
    ) -> Dict[str, Any]:
        """
        Run batch simulations across attack types and compute detection metrics.

        Args:
            attack_types: List of attack types to simulate. If None, uses all types.
            simulations_per_type: Number of simulations to run per attack type.
            detection_threshold: Risk score threshold to consider an attack "caught".
                               Defaults to auto_investigate_threshold.

        Returns:
            Dictionary containing:
            - metrics_by_attack_type: Per-type detection stats
            - overall_metrics: Aggregated metrics across all types
            - detailed_results: Full results for each simulation
        """
        from agents import FraudSimulationAgent

        if attack_types is None:
            attack_types = [
                "velocity_attack",
                "card_testing",
                "address_mismatch",
                "high_amount",
                "device_spoofing",
                "synthetic_identity",
            ]

        if detection_threshold is None:
            detection_threshold = self.auto_investigate_threshold

        sim_agent = FraudSimulationAgent(self.api_key)

        metrics_by_type = {}
        all_results = []

        for attack_type in attack_types:
            type_results = {
                "attack_type": attack_type,
                "total_transactions": 0,
                "caught_count": 0,
                "missed_count": 0,
                "risk_scores": [],
                "simulations": [],
            }

            for sim_num in range(simulations_per_type):
                try:
                    # Generate attack
                    attack = sim_agent.simulate_attack(attack_type)
                    transactions = attack.get("transactions", [])

                    simulation_detail = {
                        "simulation_number": sim_num + 1,
                        "description": attack.get("description", ""),
                        "transactions": [],
                    }

                    for tx in transactions:
                        # Analyze each transaction
                        result = self.analyze_transaction(tx, auto_investigate=True)

                        was_caught = result.risk_score >= detection_threshold

                        tx_result = {
                            "transaction_id": tx.get("transaction_id", "unknown"),
                            "risk_score": result.risk_score,
                            "risk_level": result.risk_level,
                            "was_caught": was_caught,
                            "requires_action": result.requires_action,
                        }

                        simulation_detail["transactions"].append(tx_result)
                        type_results["total_transactions"] += 1
                        type_results["risk_scores"].append(result.risk_score)

                        if was_caught:
                            type_results["caught_count"] += 1
                        else:
                            type_results["missed_count"] += 1

                    type_results["simulations"].append(simulation_detail)

                except Exception as e:
                    self.logger.error(f"Error simulating {attack_type}: {e}")
                    continue

            # Calculate metrics for this attack type
            total = type_results["total_transactions"]
            if total > 0:
                type_results["detection_rate"] = (type_results["caught_count"] / total) * 100
                type_results["false_negative_rate"] = (type_results["missed_count"] / total) * 100
                type_results["average_confidence_score"] = sum(type_results["risk_scores"]) / total
            else:
                type_results["detection_rate"] = 0
                type_results["false_negative_rate"] = 0
                type_results["average_confidence_score"] = 0

            metrics_by_type[attack_type] = type_results
            all_results.append(type_results)

        # Calculate overall metrics
        total_transactions = sum(r["total_transactions"] for r in all_results)
        total_caught = sum(r["caught_count"] for r in all_results)
        total_missed = sum(r["missed_count"] for r in all_results)
        all_scores = []
        for r in all_results:
            all_scores.extend(r["risk_scores"])

        overall_metrics = {
            "total_attack_types_tested": len(attack_types),
            "total_simulations_run": len(attack_types) * simulations_per_type,
            "total_transactions_analyzed": total_transactions,
            "total_attacks_caught": total_caught,
            "total_attacks_missed": total_missed,
            "overall_detection_rate": (total_caught / total_transactions * 100)
            if total_transactions > 0
            else 0,
            "overall_false_negative_rate": (total_missed / total_transactions * 100)
            if total_transactions > 0
            else 0,
            "overall_average_confidence": sum(all_scores) / len(all_scores) if all_scores else 0,
            "detection_threshold_used": detection_threshold,
        }

        return {
            "metrics_by_attack_type": metrics_by_type,
            "overall_metrics": overall_metrics,
            "detailed_results": all_results,
        }

    def run_mixed_detection_analysis(
        self,
        num_legitimate: int = 10,
        num_fraudulent: int = 10,
        detection_threshold: float = None,
        use_llm: bool = False,
    ) -> Dict[str, Any]:
        """
        Run detection analysis with a mix of legitimate AND fraudulent transactions.

        This provides proper evaluation metrics including:
        - True Positives (fraud correctly detected)
        - True Negatives (legitimate correctly allowed)
        - False Positives (legitimate incorrectly flagged)
        - False Negatives (fraud incorrectly missed)

        Args:
            num_legitimate: Number of legitimate transactions to generate
            num_fraudulent: Number of fraudulent transactions to generate
            detection_threshold: Risk score threshold for detection (default: auto_investigate_threshold)
            use_llm: Whether to use LLM for transaction generation (False = deterministic)

        Returns:
            Dictionary containing confusion matrix, metrics, and detailed results
        """
        from agents import SimulationAgent

        if detection_threshold is None:
            detection_threshold = self.auto_investigate_threshold

        self.logger.info(
            f"Running mixed detection analysis: {num_legitimate} legitimate, "
            f"{num_fraudulent} fraudulent, threshold={detection_threshold}"
        )

        # Generate mixed transactions
        sim_agent = SimulationAgent(api_key=self.api_key)

        if use_llm and sim_agent.client:
            try:
                mixed_data = sim_agent.generate_mixed_transactions(
                    num_legitimate=num_legitimate, num_fraudulent=num_fraudulent
                )
            except Exception as e:
                self.logger.warning(f"LLM generation failed, using deterministic: {e}")
                mixed_data = sim_agent.generate_deterministic_mixed_transactions(
                    num_legitimate=num_legitimate, num_fraudulent=num_fraudulent
                )
        else:
            mixed_data = sim_agent.generate_deterministic_mixed_transactions(
                num_legitimate=num_legitimate, num_fraudulent=num_fraudulent
            )

        transactions = mixed_data["transactions"]

        # Initialize confusion matrix counters
        true_positives = 0  # Fraud correctly detected
        true_negatives = 0  # Legitimate correctly allowed
        false_positives = 0  # Legitimate incorrectly flagged as fraud
        false_negatives = 0  # Fraud incorrectly allowed

        # Detailed results
        detailed_results = []
        fraud_scores = []
        legitimate_scores = []

        for tx in transactions:
            expected_fraud = tx.get("is_fraudulent", False)

            # Analyze the transaction
            result = self.analyze_transaction(tx, auto_investigate=False)

            # Determine if system flagged as fraud
            predicted_fraud = result.risk_score >= detection_threshold

            # Categorize the outcome
            if expected_fraud and predicted_fraud:
                outcome = "true_positive"
                true_positives += 1
                fraud_scores.append(result.risk_score)
            elif not expected_fraud and not predicted_fraud:
                outcome = "true_negative"
                true_negatives += 1
                legitimate_scores.append(result.risk_score)
            elif not expected_fraud and predicted_fraud:
                outcome = "false_positive"
                false_positives += 1
                legitimate_scores.append(result.risk_score)
            else:  # expected_fraud and not predicted_fraud
                outcome = "false_negative"
                false_negatives += 1
                fraud_scores.append(result.risk_score)

            detailed_results.append(
                {
                    "transaction_id": tx.get("transaction_id", "unknown"),
                    "expected_fraud": expected_fraud,
                    "predicted_fraud": predicted_fraud,
                    "risk_score": result.risk_score,
                    "risk_level": result.risk_level,
                    "outcome": outcome,
                    "fraud_type": tx.get("fraud_type", "N/A"),
                    "amount": tx.get("amount", 0),
                    "location": tx.get("location", "unknown"),
                    "merchant_category": tx.get("merchant_category", "unknown"),
                }
            )

        # Calculate metrics
        total = true_positives + true_negatives + false_positives + false_negatives

        # Accuracy: (TP + TN) / Total
        accuracy = (true_positives + true_negatives) / total if total > 0 else 0

        # Precision: TP / (TP + FP) - Of all flagged as fraud, how many were actually fraud?
        precision = (
            true_positives / (true_positives + false_positives)
            if (true_positives + false_positives) > 0
            else 0
        )

        # Recall (Sensitivity): TP / (TP + FN) - Of all actual fraud, how many did we catch?
        recall = (
            true_positives / (true_positives + false_negatives)
            if (true_positives + false_negatives) > 0
            else 0
        )

        # F1 Score: Harmonic mean of precision and recall
        f1_score = (
            2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        )

        # Specificity: TN / (TN + FP) - Of all legitimate, how many did we correctly allow?
        specificity = (
            true_negatives / (true_negatives + false_positives)
            if (true_negatives + false_positives) > 0
            else 0
        )

        # False Positive Rate: FP / (FP + TN)
        false_positive_rate = (
            false_positives / (false_positives + true_negatives)
            if (false_positives + true_negatives) > 0
            else 0
        )

        # False Negative Rate: FN / (FN + TP)
        false_negative_rate = (
            false_negatives / (false_negatives + true_positives)
            if (false_negatives + true_positives) > 0
            else 0
        )

        # Average scores by category
        avg_fraud_score = sum(fraud_scores) / len(fraud_scores) if fraud_scores else 0
        avg_legitimate_score = (
            sum(legitimate_scores) / len(legitimate_scores) if legitimate_scores else 0
        )

        return {
            "confusion_matrix": {
                "true_positives": true_positives,
                "true_negatives": true_negatives,
                "false_positives": false_positives,
                "false_negatives": false_negatives,
            },
            "metrics": {
                "accuracy": round(accuracy, 4),
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1_score": round(f1_score, 4),
                "specificity": round(specificity, 4),
                "false_positive_rate": round(false_positive_rate, 4),
                "false_negative_rate": round(false_negative_rate, 4),
            },
            "summary": {
                "total_transactions": total,
                "total_legitimate": mixed_data["legitimate_count"],
                "total_fraudulent": mixed_data["fraudulent_count"],
                "detection_threshold": detection_threshold,
                "average_fraud_score": round(avg_fraud_score, 2),
                "average_legitimate_score": round(avg_legitimate_score, 2),
                "score_separation": round(avg_fraud_score - avg_legitimate_score, 2),
            },
            "interpretation": {
                "accuracy_meaning": f"Overall correctness: {accuracy * 100:.1f}% of predictions were correct",
                "precision_meaning": f"When we flag fraud, we're right {precision * 100:.1f}% of the time",
                "recall_meaning": f"We catch {recall * 100:.1f}% of actual fraud cases",
                "f1_meaning": f"Balanced score (precision+recall): {f1_score:.3f}",
                "fpr_meaning": f"{false_positive_rate * 100:.1f}% of legitimate transactions incorrectly flagged",
                "fnr_meaning": f"{false_negative_rate * 100:.1f}% of fraud transactions slipped through",
            },
            "detailed_results": detailed_results,
        }


def format_result(result: FraudAnalysisResult) -> str:
    """Format a fraud analysis result for display"""
    lines = [
        "=" * 60,
        f"FRAUD ANALYSIS: {result.entity_type.upper()} {result.entity_id}",
        "=" * 60,
        "",
        f"Risk Score: {result.risk_score}/100",
        f"Risk Level: {result.risk_level.upper()}",
        f"Requires Action: {'YES' if result.requires_action else 'NO'}",
        "",
        f"Recommendation: {result.recommendation}",
        "",
    ]

    if result.signals:
        lines.append("-" * 40)
        lines.append("DETECTED SIGNALS")
        lines.append("-" * 40)
        for signal in result.signals:
            severity = (
                "HIGH" if signal["weight"] >= 0.7 else "MED" if signal["weight"] >= 0.4 else "LOW"
            )
            lines.append(f"[{severity}] {signal['name']}: {signal['description']}")
        lines.append("")

    if result.agent_results:
        lines.append("-" * 40)
        lines.append("AGENT SCORES")
        lines.append("-" * 40)
        for agent, score in result.agent_results.items():
            lines.append(f"  {agent}: {score:.1f}")
        lines.append("")

    if result.investigation_report:
        lines.append("-" * 40)
        lines.append("INVESTIGATION REPORT")
        lines.append("-" * 40)
        lines.append(result.investigation_report.get("llm_analysis", "No analysis available"))
        lines.append("")

    lines.append("=" * 60)

    return "\n".join(lines)
