"""
Webhook endpoints for external integrations.
Handles callbacks from payment processors, chargeback notifications, etc.
"""

import hmac
import hashlib
import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Header, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.session import get_db
from db.repository import AlertRepository, TransactionRepository, CaseRepository, AuditRepository
from db.models import AlertStatus, CaseStatus, CaseResolution

# ML Feedback integration
try:
    from ml import get_feedback_collector

    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    get_feedback_collector = None

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


def _record_ml_feedback(transaction_id: str, outcome: str, outcome_details: dict = None):
    """Record outcome to ML feedback loop."""
    if not ML_AVAILABLE:
        return

    try:
        collector = get_feedback_collector()
        collector.record_outcome(
            transaction_id=transaction_id,
            outcome=outcome,
            outcome_details=outcome_details,
        )
        logger.info(f"ML feedback recorded: {transaction_id} -> {outcome}")
    except Exception as e:
        logger.warning(f"Failed to record ML feedback: {e}")

    # Also record in evaluation store for confusion matrix
    try:
        from observability import get_feedback_loop

        feedback_loop = get_feedback_loop()

        risk_score = outcome_details.get("risk_score", 50) if outcome_details else 50
        original_decision = "block" if risk_score >= 60 else "allow"

        if outcome == "chargeback":
            feedback_loop.record_chargeback(
                alert_id=transaction_id,
                entity_type="transaction",
                original_decision=original_decision,
                risk_score=risk_score,
                confidence=0.8,
            )
        elif outcome in ["analyst_confirmed", "analyst_dismissed"]:
            human_decision = "block" if outcome == "analyst_confirmed" else "approve"
            feedback_loop.record_human_override(
                alert_id=transaction_id,
                entity_type="transaction",
                agent_decision=original_decision,
                human_decision=human_decision,
                risk_score=risk_score,
                confidence=0.8,
            )
    except Exception as e:
        logger.warning(f"Failed to record evaluation feedback: {e}")


# ============== Webhook Security ==============


def verify_webhook_signature(
    payload: bytes, signature: str, secret: str, algorithm: str = "sha256"
) -> bool:
    """
    Verify webhook signature.

    Most payment processors use HMAC-SHA256 for webhook verification.
    """
    expected = hmac.new(secret.encode(), payload, getattr(hashlib, algorithm)).hexdigest()

    return hmac.compare_digest(expected, signature)


# ============== Request Models ==============


class ChargebackWebhook(BaseModel):
    """Chargeback notification from payment processor."""

    chargeback_id: str
    transaction_id: str  # Our external transaction ID
    amount: float
    currency: str = "USD"
    reason_code: str
    reason_description: str
    cardholder_name: Optional[str] = None
    dispute_date: Optional[str] = None
    response_due_date: Optional[str] = None
    metadata: Optional[dict] = None


class FraudConfirmationWebhook(BaseModel):
    """Fraud confirmation from downstream systems."""

    transaction_id: str
    is_fraud: bool
    confirmation_source: str  # "bank", "customer", "investigation"
    details: Optional[str] = None
    confirmed_at: Optional[str] = None


class TransactionOutcomeWebhook(BaseModel):
    """Transaction outcome notification."""

    transaction_id: str
    outcome: str  # "completed", "refunded", "disputed", "fraud_confirmed"
    amount: Optional[float] = None
    details: Optional[dict] = None


# ============== Webhook Endpoints ==============


@router.post("/chargeback")
async def receive_chargeback(
    webhook: ChargebackWebhook,
    request: Request,
    x_webhook_signature: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """
    Receive chargeback notification from payment processor.

    This endpoint:
    1. Records the chargeback against the transaction
    2. Updates associated fraud alerts
    3. Creates/updates investigation cases
    4. Logs for audit trail
    """
    import os

    # Verify signature if configured
    webhook_secret = os.getenv("WEBHOOK_SECRET")
    if webhook_secret and x_webhook_signature:
        body = await request.body()
        if not verify_webhook_signature(body, x_webhook_signature, webhook_secret):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature"
            )

    logger.info(f"Received chargeback for transaction {webhook.transaction_id}")

    tx_repo = TransactionRepository(db)
    alert_repo = AlertRepository(db)
    case_repo = CaseRepository(db)
    audit_repo = AuditRepository(db)

    # Find the transaction
    transaction = tx_repo.get_by_external_id(webhook.transaction_id)

    if not transaction:
        logger.warning(f"Chargeback received for unknown transaction: {webhook.transaction_id}")
        # Still log it for investigation
        audit_repo.log(
            action="webhook.chargeback.unknown_transaction",
            extra_data={
                "chargeback_id": webhook.chargeback_id,
                "transaction_id": webhook.transaction_id,
                "amount": webhook.amount,
                "reason_code": webhook.reason_code,
            },
        )
        return {"status": "recorded", "message": "Transaction not found, logged for investigation"}

    # Update any associated alerts
    for alert in transaction.alerts:
        alert_repo.record_chargeback(
            alert_id=alert.id, amount=webhook.amount, chargeback_date=datetime.utcnow()
        )

        # If alert was marked as false positive, this is a feedback signal
        if alert.status == AlertStatus.FALSE_POSITIVE:
            logger.warning(
                f"Chargeback received for alert {alert.id} previously marked as false positive!"
            )
            audit_repo.log(
                action="feedback.false_positive_was_fraud",
                resource_type="alert",
                resource_id=alert.id,
                extra_data={
                    "chargeback_id": webhook.chargeback_id,
                    "amount": webhook.amount,
                    "original_risk_score": alert.risk_score,
                },
            )

    # If no alert exists, create one (this was a missed fraud)
    if not transaction.alerts:
        logger.warning(
            f"Chargeback for transaction {transaction.id} with no fraud alert - MISSED FRAUD"
        )

        alert = alert_repo.create(
            {
                "transaction_id": transaction.id,
                "alert_type": "chargeback_received",
                "severity": "high",
                "risk_score": 100.0,
                "status": AlertStatus.CONFIRMED_FRAUD,
                "actual_outcome": "confirmed_fraud",
                "chargeback_received": True,
                "chargeback_amount": webhook.amount,
                "chargeback_date": datetime.utcnow(),
                "resolution_notes": f"Fraud confirmed via chargeback. Reason: {webhook.reason_code}",
            }
        )

        # Create a case for investigation
        case = case_repo.create(
            title=f"Chargeback Investigation - {webhook.transaction_id}",
            case_type="missed_fraud",
            alert_ids=[alert.id],
            description=f"Chargeback received for transaction that was not flagged. "
            f"Amount: ${webhook.amount}. Reason: {webhook.reason_description}",
            priority=1,  # Critical
        )

        audit_repo.log(
            action="feedback.missed_fraud",
            resource_type="transaction",
            resource_id=transaction.id,
            extra_data={
                "chargeback_id": webhook.chargeback_id,
                "amount": webhook.amount,
                "original_risk_score": transaction.risk_score,
                "case_number": case.case_number,
            },
        )

    # Log the chargeback
    audit_repo.log(
        action="webhook.chargeback.received",
        resource_type="transaction",
        resource_id=transaction.id,
        extra_data={
            "chargeback_id": webhook.chargeback_id,
            "amount": webhook.amount,
            "reason_code": webhook.reason_code,
            "reason_description": webhook.reason_description,
        },
    )

    # Record to ML feedback loop - chargeback = confirmed fraud
    _record_ml_feedback(
        transaction_id=webhook.transaction_id,
        outcome="chargeback",
        outcome_details={
            "chargeback_id": webhook.chargeback_id,
            "amount": webhook.amount,
            "reason_code": webhook.reason_code,
        },
    )

    return {
        "status": "processed",
        "transaction_id": str(transaction.id),
        "chargeback_id": webhook.chargeback_id,
        "alerts_updated": len(transaction.alerts),
    }


@router.post("/fraud-confirmation")
async def receive_fraud_confirmation(
    webhook: FraudConfirmationWebhook,
    request: Request,
    x_webhook_signature: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """
    Receive fraud confirmation from banks, customers, or investigation teams.

    This is used to:
    1. Confirm or clear fraud alerts
    2. Update case resolutions
    3. Provide feedback for model improvement
    """
    import os

    # Verify signature if configured
    webhook_secret = os.getenv("WEBHOOK_SECRET")
    if webhook_secret and x_webhook_signature:
        body = await request.body()
        if not verify_webhook_signature(body, x_webhook_signature, webhook_secret):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature"
            )

    logger.info(
        f"Received fraud confirmation for {webhook.transaction_id}: "
        f"is_fraud={webhook.is_fraud}, source={webhook.confirmation_source}"
    )

    tx_repo = TransactionRepository(db)
    alert_repo = AlertRepository(db)
    audit_repo = AuditRepository(db)

    # Find the transaction
    transaction = tx_repo.get_by_external_id(webhook.transaction_id)

    if not transaction:
        return {"status": "not_found", "message": "Transaction not found"}

    # Update alerts
    for alert in transaction.alerts:
        new_status = AlertStatus.CONFIRMED_FRAUD if webhook.is_fraud else AlertStatus.FALSE_POSITIVE
        outcome = "confirmed_fraud" if webhook.is_fraud else "false_positive"

        alert.status = new_status
        alert.actual_outcome = outcome
        alert.resolved_at = datetime.utcnow()
        alert.resolution_notes = (
            f"Confirmed via {webhook.confirmation_source}: {webhook.details or 'No details'}"
        )

        # Update associated case
        if alert.case:
            resolution = (
                CaseResolution.CONFIRMED_FRAUD
                if webhook.is_fraud
                else CaseResolution.FALSE_POSITIVE
            )
            alert.case.resolution = resolution
            alert.case.status = CaseStatus.RESOLVED
            alert.case.resolved_at = datetime.utcnow()

    db.commit()

    # Log for feedback loop
    audit_repo.log(
        action="feedback.fraud_confirmation",
        resource_type="transaction",
        resource_id=transaction.id,
        extra_data={
            "is_fraud": webhook.is_fraud,
            "confirmation_source": webhook.confirmation_source,
            "original_risk_score": transaction.risk_score,
            "details": webhook.details,
        },
    )

    # Record to ML feedback loop
    ml_outcome = "analyst_confirmed" if webhook.is_fraud else "analyst_dismissed"
    _record_ml_feedback(
        transaction_id=webhook.transaction_id,
        outcome=ml_outcome,
        outcome_details={
            "confirmation_source": webhook.confirmation_source,
            "details": webhook.details,
        },
    )

    return {
        "status": "processed",
        "transaction_id": str(transaction.id),
        "is_fraud": webhook.is_fraud,
        "alerts_updated": len(transaction.alerts),
    }


@router.post("/transaction-outcome")
async def receive_transaction_outcome(
    webhook: TransactionOutcomeWebhook, db: Session = Depends(get_db)
):
    """
    Receive transaction outcome for feedback loop.

    Outcomes like refunds or disputes can indicate fraud patterns.
    """
    tx_repo = TransactionRepository(db)
    audit_repo = AuditRepository(db)

    transaction = tx_repo.get_by_external_id(webhook.transaction_id)

    if not transaction:
        return {"status": "not_found"}

    # Log the outcome
    audit_repo.log(
        action=f"outcome.{webhook.outcome}",
        resource_type="transaction",
        resource_id=transaction.id,
        extra_data={
            "outcome": webhook.outcome,
            "amount": webhook.amount,
            "details": webhook.details,
        },
    )

    # If disputed, may need follow-up
    if webhook.outcome == "disputed":
        # Could automatically create an alert or case here
        logger.info(f"Transaction {webhook.transaction_id} disputed - may need investigation")

    return {"status": "recorded", "transaction_id": str(transaction.id)}


# ============== Webhook Status ==============


@router.get("/status")
async def webhook_status():
    """Get webhook endpoint status and configuration."""
    import os

    return {
        "status": "active",
        "endpoints": {
            "chargeback": "/webhooks/chargeback",
            "fraud_confirmation": "/webhooks/fraud-confirmation",
            "transaction_outcome": "/webhooks/transaction-outcome",
        },
        "signature_verification": bool(os.getenv("WEBHOOK_SECRET")),
        "supported_providers": ["stripe", "braintree", "adyen", "custom"],
    }
