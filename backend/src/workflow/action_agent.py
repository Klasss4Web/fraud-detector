"""
Action Agent - Executes containment and remediation actions.

This agent is responsible for taking defensive actions based on
the Decider Agent's determination. It includes safety guardrails
to prevent runaway automation.
"""

import logging
from typing import Any
from datetime import datetime

from workflow.state import (
    WorkflowState,
    WorkflowStatus,
    ActionType,
    ActionResult,
)
from tools.actions import (
    SoftMitigationTools,
    HardMitigationTools,
    ActionResponse,
    ActionStatus,
)

logger = logging.getLogger(__name__)


class ActionAgent:
    """
    Executes containment and remediation actions with safety guardrails.
    """

    def __init__(self):
        self.name = "ActionAgent"
        self.soft_tools = SoftMitigationTools()
        self.hard_tools = HardMitigationTools()

    async def process(self, state: WorkflowState) -> WorkflowState:
        """
        Execute the decided action.

        Args:
            state: Current workflow state with decision

        Returns:
            Updated state with action results
        """
        state.status = WorkflowStatus.EXECUTING_ACTION
        state.current_agent = self.name

        if not state.decision:
            state.add_log(self.name, "No decision to execute")
            return state

        decision = state.decision

        # If human review is required, don't execute hard actions
        if decision.requires_human_review and decision.action in (
            ActionType.BLOCK,
            ActionType.FREEZE_ACCOUNT,
        ):
            state.add_log(
                self.name,
                "Hard action deferred pending human review",
                {"action": decision.action.value},
            )
            state.escalated_to_human = True
            return state

        state.add_log(self.name, f"Executing action: {decision.action.value}")

        # Execute the appropriate action
        action_result = await self._execute_action(state, decision.action)
        state.actions_taken.append(action_result)

        state.add_log(
            self.name,
            f"Action executed: {action_result.action_type.value} - {'Success' if action_result.success else 'Failed'}",
            action_result.details,
        )

        logger.info(
            f"Action {decision.action.value} executed for {state.alert.alert_id}: "
            f"{'Success' if action_result.success else 'Failed'}"
        )

        return state

    async def _execute_action(self, state: WorkflowState, action: ActionType) -> ActionResult:
        """Execute a specific action type."""

        alert = state.alert
        data = alert.entity_data

        user_id = data.get("user_id", alert.entity_id)

        try:
            if action == ActionType.APPROVE:
                return ActionResult(
                    action_type=action,
                    success=True,
                    timestamp=datetime.utcnow().isoformat(),
                    details={"message": "Transaction approved - no action needed"},
                )

            elif action == ActionType.REQUEST_MFA:
                response = await self.soft_tools.trigger_mfa_challenge(
                    user_id=user_id,
                    transaction_id=alert.entity_id,
                    method="sms",
                )
                return self._response_to_result(action, response)

            elif action == ActionType.REQUEST_VERIFICATION:
                response = await self.soft_tools.request_id_verification(
                    user_id=user_id,
                    verification_type="document",
                )
                return self._response_to_result(action, response)

            elif action == ActionType.HOLD:
                if alert.entity_type == "order":
                    response = await self.soft_tools.hold_order(
                        order_id=alert.entity_id,
                        reason=state.decision.explanation if state.decision else "Fraud review",
                    )
                    return self._response_to_result(action, response)
                else:
                    return ActionResult(
                        action_type=action,
                        success=True,
                        timestamp=datetime.utcnow().isoformat(),
                        details={"message": "Entity held for review"},
                    )

            elif action == ActionType.FLAG_FOR_REVIEW:
                return ActionResult(
                    action_type=action,
                    success=True,
                    timestamp=datetime.utcnow().isoformat(),
                    details={
                        "message": "Flagged for manual review",
                        "priority": "medium",
                        "review_deadline": "24 hours",
                    },
                )

            elif action == ActionType.NOTIFY_USER:
                response = await self.soft_tools.notify_user(
                    user_id=user_id,
                    notification_type="suspicious_activity",
                    transaction_id=alert.entity_id,
                )
                return self._response_to_result(action, response)

            elif action == ActionType.BLOCK:
                if alert.entity_type == "transaction":
                    response = await self.hard_tools.decline_transaction(
                        transaction_id=alert.entity_id,
                        reason=state.decision.explanation if state.decision else "Fraud detected",
                    )
                    return self._response_to_result(action, response)
                else:
                    # For other entity types, lock the account
                    response = await self.hard_tools.lock_account(
                        user_id=user_id,
                        reason="Fraudulent activity detected",
                        lock_type="temporary",
                    )
                    return self._response_to_result(action, response)

            elif action == ActionType.FREEZE_ACCOUNT:
                response = await self.hard_tools.lock_account(
                    user_id=user_id,
                    reason="Critical fraud alert",
                    lock_type="permanent",
                )

                # Also block the device if available
                if device_id := data.get("device_id"):
                    await self.hard_tools.block_device(
                        device_id=device_id,
                        reason="Associated with frozen account",
                    )

                return self._response_to_result(action, response)

            elif action == ActionType.ESCALATE_TO_HUMAN:
                state.escalated_to_human = True
                return ActionResult(
                    action_type=action,
                    success=True,
                    timestamp=datetime.utcnow().isoformat(),
                    details={"message": "Escalated to human analyst"},
                )

            else:
                return ActionResult(
                    action_type=action,
                    success=False,
                    timestamp=datetime.utcnow().isoformat(),
                    error_message=f"Unknown action type: {action.value}",
                )

        except Exception as e:
            logger.error(f"Action execution failed: {e}")
            return ActionResult(
                action_type=action,
                success=False,
                timestamp=datetime.utcnow().isoformat(),
                error_message=str(e),
            )

    def _response_to_result(self, action: ActionType, response: ActionResponse) -> ActionResult:
        """Convert an ActionResponse to an ActionResult."""
        return ActionResult(
            action_type=action,
            success=response.status == ActionStatus.SUCCESS,
            timestamp=response.timestamp,
            details=response.details,
            error_message=response.message if response.status != ActionStatus.SUCCESS else None,
        )
