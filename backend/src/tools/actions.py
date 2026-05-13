"""
Action tools for executing containment and remediation actions.
"""

import logging
from datetime import datetime
from typing import Any, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ActionStatus(Enum):
    """Status of an executed action."""

    SUCCESS = "success"
    FAILED = "failed"
    PENDING = "pending"
    RATE_LIMITED = "rate_limited"


@dataclass
class ActionResponse:
    """Response from executing an action."""

    action_name: str
    status: ActionStatus
    message: str
    timestamp: str
    details: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_name": self.action_name,
            "status": self.status.value,
            "message": self.message,
            "timestamp": self.timestamp,
            "details": self.details,
        }


class RateLimiter:
    """
    Simple rate limiter to prevent runaway action execution.
    Critical guardrail to prevent mass account freezes due to LLM errors.
    """

    def __init__(self, max_actions_per_minute: int = 10, max_hard_actions_per_minute: int = 3):
        self.max_actions = max_actions_per_minute
        self.max_hard_actions = max_hard_actions_per_minute
        self.action_timestamps: list[datetime] = []
        self.hard_action_timestamps: list[datetime] = []

    def _cleanup_old(self, timestamps: list[datetime]) -> list[datetime]:
        """Remove timestamps older than 1 minute."""
        cutoff = datetime.utcnow().replace(microsecond=0)
        cutoff = cutoff.replace(second=cutoff.second - 60 if cutoff.second >= 60 else 0)
        return [ts for ts in timestamps if ts > cutoff]

    def can_execute(self, is_hard_action: bool = False) -> bool:
        """Check if an action can be executed within rate limits."""
        self.action_timestamps = self._cleanup_old(self.action_timestamps)

        if len(self.action_timestamps) >= self.max_actions:
            logger.warning("Rate limit exceeded for total actions")
            return False

        if is_hard_action:
            self.hard_action_timestamps = self._cleanup_old(self.hard_action_timestamps)
            if len(self.hard_action_timestamps) >= self.max_hard_actions:
                logger.warning("Rate limit exceeded for hard actions")
                return False

        return True

    def record_action(self, is_hard_action: bool = False):
        """Record that an action was executed."""
        now = datetime.utcnow()
        self.action_timestamps.append(now)
        if is_hard_action:
            self.hard_action_timestamps.append(now)


# Global rate limiter instance
_rate_limiter = RateLimiter()


class SoftMitigationTools:
    """
    Soft mitigation actions that don't immediately block the user.
    """

    @staticmethod
    async def trigger_mfa_challenge(
        user_id: str,
        transaction_id: Optional[str] = None,
        method: str = "sms",
    ) -> ActionResponse:
        """
        Trigger a Multi-Factor Authentication challenge.

        In production, this would call your MFA provider (Twilio, Auth0, etc.)
        """
        if not _rate_limiter.can_execute(is_hard_action=False):
            return ActionResponse(
                action_name="trigger_mfa_challenge",
                status=ActionStatus.RATE_LIMITED,
                message="Rate limit exceeded. Too many actions in short period.",
                timestamp=datetime.utcnow().isoformat(),
                details={"user_id": user_id},
            )

        _rate_limiter.record_action(is_hard_action=False)

        logger.info(f"Triggering MFA challenge for user {user_id} via {method}")

        # In production: Call MFA API
        # Example: await twilio_client.send_verification(user_phone, method)

        return ActionResponse(
            action_name="trigger_mfa_challenge",
            status=ActionStatus.SUCCESS,
            message=f"MFA challenge sent via {method}",
            timestamp=datetime.utcnow().isoformat(),
            details={
                "user_id": user_id,
                "transaction_id": transaction_id,
                "method": method,
                "challenge_id": f"MFA-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            },
        )

    @staticmethod
    async def request_id_verification(
        user_id: str,
        verification_type: str = "document",
    ) -> ActionResponse:
        """
        Request identity document verification (step-up verification).

        In production, this would trigger a flow in your ID verification provider.
        """
        if not _rate_limiter.can_execute(is_hard_action=False):
            return ActionResponse(
                action_name="request_id_verification",
                status=ActionStatus.RATE_LIMITED,
                message="Rate limit exceeded.",
                timestamp=datetime.utcnow().isoformat(),
                details={"user_id": user_id},
            )

        _rate_limiter.record_action(is_hard_action=False)

        logger.info(f"Requesting ID verification for user {user_id}")

        return ActionResponse(
            action_name="request_id_verification",
            status=ActionStatus.SUCCESS,
            message=f"ID verification ({verification_type}) requested",
            timestamp=datetime.utcnow().isoformat(),
            details={
                "user_id": user_id,
                "verification_type": verification_type,
                "verification_id": f"VER-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            },
        )

    @staticmethod
    async def hold_order(
        order_id: str,
        reason: str,
        hold_duration_hours: int = 24,
    ) -> ActionResponse:
        """
        Temporarily hold an order for review.
        """
        if not _rate_limiter.can_execute(is_hard_action=False):
            return ActionResponse(
                action_name="hold_order",
                status=ActionStatus.RATE_LIMITED,
                message="Rate limit exceeded.",
                timestamp=datetime.utcnow().isoformat(),
                details={"order_id": order_id},
            )

        _rate_limiter.record_action(is_hard_action=False)

        logger.info(f"Holding order {order_id} for {hold_duration_hours} hours")

        return ActionResponse(
            action_name="hold_order",
            status=ActionStatus.SUCCESS,
            message=f"Order held for review ({hold_duration_hours} hours)",
            timestamp=datetime.utcnow().isoformat(),
            details={
                "order_id": order_id,
                "reason": reason,
                "hold_duration_hours": hold_duration_hours,
                "release_time": (
                    datetime.utcnow().replace(hour=datetime.utcnow().hour + hold_duration_hours)
                ).isoformat(),
            },
        )

    @staticmethod
    async def notify_user(
        user_id: str,
        notification_type: str,
        transaction_id: Optional[str] = None,
        channel: str = "sms",
    ) -> ActionResponse:
        """
        Send a notification to the user asking to confirm activity.

        In production: "Did you just make this purchase? Reply YES to confirm."
        """
        if not _rate_limiter.can_execute(is_hard_action=False):
            return ActionResponse(
                action_name="notify_user",
                status=ActionStatus.RATE_LIMITED,
                message="Rate limit exceeded.",
                timestamp=datetime.utcnow().isoformat(),
                details={"user_id": user_id},
            )

        _rate_limiter.record_action(is_hard_action=False)

        logger.info(f"Sending {notification_type} notification to user {user_id} via {channel}")

        return ActionResponse(
            action_name="notify_user",
            status=ActionStatus.SUCCESS,
            message=f"Notification sent via {channel}",
            timestamp=datetime.utcnow().isoformat(),
            details={
                "user_id": user_id,
                "transaction_id": transaction_id,
                "notification_type": notification_type,
                "channel": channel,
            },
        )


class HardMitigationTools:
    """
    Hard mitigation actions that immediately restrict user access.
    These have stricter rate limits.
    """

    @staticmethod
    async def freeze_card(
        card_id: str,
        user_id: str,
        reason: str,
    ) -> ActionResponse:
        """
        Immediately freeze a debit/credit card.

        In production, this would call your card issuer's API.
        """
        if not _rate_limiter.can_execute(is_hard_action=True):
            return ActionResponse(
                action_name="freeze_card",
                status=ActionStatus.RATE_LIMITED,
                message="Rate limit exceeded for hard actions. Manual intervention required.",
                timestamp=datetime.utcnow().isoformat(),
                details={"card_id": card_id, "user_id": user_id},
            )

        _rate_limiter.record_action(is_hard_action=True)

        logger.warning(f"FREEZING card {card_id} for user {user_id}. Reason: {reason}")

        return ActionResponse(
            action_name="freeze_card",
            status=ActionStatus.SUCCESS,
            message="Card frozen immediately",
            timestamp=datetime.utcnow().isoformat(),
            details={
                "card_id": card_id[-4:],  # Only show last 4 digits
                "user_id": user_id,
                "reason": reason,
            },
        )

    @staticmethod
    async def lock_account(
        user_id: str,
        reason: str,
        lock_type: str = "temporary",
    ) -> ActionResponse:
        """
        Lock a user account.

        In production, this would update your user database and invalidate sessions.
        """
        if not _rate_limiter.can_execute(is_hard_action=True):
            return ActionResponse(
                action_name="lock_account",
                status=ActionStatus.RATE_LIMITED,
                message="Rate limit exceeded for hard actions.",
                timestamp=datetime.utcnow().isoformat(),
                details={"user_id": user_id},
            )

        _rate_limiter.record_action(is_hard_action=True)

        logger.warning(f"LOCKING account {user_id} ({lock_type}). Reason: {reason}")

        return ActionResponse(
            action_name="lock_account",
            status=ActionStatus.SUCCESS,
            message=f"Account locked ({lock_type})",
            timestamp=datetime.utcnow().isoformat(),
            details={
                "user_id": user_id,
                "lock_type": lock_type,
                "reason": reason,
            },
        )

    @staticmethod
    async def block_device(
        device_id: str,
        reason: str,
    ) -> ActionResponse:
        """
        Add a device fingerprint to the blocklist.
        """
        if not _rate_limiter.can_execute(is_hard_action=True):
            return ActionResponse(
                action_name="block_device",
                status=ActionStatus.RATE_LIMITED,
                message="Rate limit exceeded for hard actions.",
                timestamp=datetime.utcnow().isoformat(),
                details={"device_id": device_id},
            )

        _rate_limiter.record_action(is_hard_action=True)

        logger.warning(f"BLOCKING device {device_id}. Reason: {reason}")

        return ActionResponse(
            action_name="block_device",
            status=ActionStatus.SUCCESS,
            message="Device added to blocklist",
            timestamp=datetime.utcnow().isoformat(),
            details={
                "device_id": device_id[:8] + "...",
                "reason": reason,
            },
        )

    @staticmethod
    async def decline_transaction(
        transaction_id: str,
        reason: str,
    ) -> ActionResponse:
        """
        Decline/reverse a transaction.
        """
        if not _rate_limiter.can_execute(is_hard_action=True):
            return ActionResponse(
                action_name="decline_transaction",
                status=ActionStatus.RATE_LIMITED,
                message="Rate limit exceeded for hard actions.",
                timestamp=datetime.utcnow().isoformat(),
                details={"transaction_id": transaction_id},
            )

        _rate_limiter.record_action(is_hard_action=True)

        logger.warning(f"DECLINING transaction {transaction_id}. Reason: {reason}")

        return ActionResponse(
            action_name="decline_transaction",
            status=ActionStatus.SUCCESS,
            message="Transaction declined",
            timestamp=datetime.utcnow().isoformat(),
            details={
                "transaction_id": transaction_id,
                "reason": reason,
            },
        )


# Export all tools
__all__ = [
    "SoftMitigationTools",
    "HardMitigationTools",
    "ActionResponse",
    "ActionStatus",
    "RateLimiter",
]
