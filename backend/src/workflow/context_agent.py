"""
Context Gatherer Agent - Gathers external context about alerts.

This agent is the system's "sensors" - it queries external APIs and
internal databases to build a complete picture of the alert context.
"""

import logging
from typing import Any
from dataclasses import asdict

from workflow.state import (
    WorkflowState,
    WorkflowStatus,
    ContextData,
)
from tools.external import (
    IPInfoTool,
    DeviceFingerprintTool,
    EmailRiskTool,
    VelocityCheckTool,
    AddressVerificationTool,
)
from utils.helpers import mask_sensitive_data

logger = logging.getLogger(__name__)


class ContextGathererAgent:
    """
    Gathers context about fraud alerts from multiple sources.
    """

    def __init__(
        self,
        ip_api_key: str | None = None,
        device_api_key: str | None = None,
        email_api_key: str | None = None,
    ):
        self.name = "ContextGathererAgent"

        # Initialize tools
        self.ip_tool = IPInfoTool(api_key=ip_api_key)
        self.device_tool = DeviceFingerprintTool(api_key=device_api_key)
        self.email_tool = EmailRiskTool(api_key=email_api_key)
        self.velocity_tool = VelocityCheckTool()
        self.address_tool = AddressVerificationTool()

    async def process(self, state: WorkflowState) -> WorkflowState:
        """
        Gather context for the alert.

        Args:
            state: Current workflow state

        Returns:
            Updated state with gathered context
        """
        state.status = WorkflowStatus.GATHERING_CONTEXT
        state.current_agent = self.name
        state.add_log(self.name, "Starting context gathering")

        alert = state.alert
        data = alert.entity_data

        # Mask sensitive data before processing
        masked_data = mask_sensitive_data(data)

        context = ContextData()
        risk_indicators = []
        anomalies = []

        # Gather IP information
        if ip_address := data.get("ip_address"):
            try:
                ip_info = await self.ip_tool.lookup(ip_address)
                context.ip_info = asdict(ip_info)

                if ip_info.is_vpn or ip_info.is_proxy:
                    risk_indicators.append(f"VPN/Proxy detected from {ip_info.country}")
                if ip_info.is_datacenter:
                    risk_indicators.append("Request from datacenter IP")
                if ip_info.risk_score > 50:
                    risk_indicators.append(f"High-risk IP location: {ip_info.country}")

                state.add_log(
                    self.name,
                    f"IP lookup complete: {ip_info.country}",
                    {"risk_score": ip_info.risk_score},
                )
            except Exception as e:
                logger.error(f"IP lookup failed: {e}")
                state.errors.append(f"IP lookup failed: {str(e)}")

        # Gather device information
        if device_id := data.get("device_id"):
            try:
                device_info = await self.device_tool.lookup(device_id)
                context.device_info = asdict(device_info)

                if device_info.is_emulator:
                    risk_indicators.append("Emulator/simulator detected")
                    anomalies.append("EMULATOR_DETECTED")
                if device_info.is_rooted:
                    risk_indicators.append("Rooted/jailbroken device")
                if device_info.associated_users > 3:
                    risk_indicators.append(f"Device shared by {device_info.associated_users} users")
                    anomalies.append("SHARED_DEVICE")

                state.add_log(
                    self.name, "Device lookup complete", {"risk_score": device_info.risk_score}
                )
            except Exception as e:
                logger.error(f"Device lookup failed: {e}")
                state.errors.append(f"Device lookup failed: {str(e)}")

        # Assess email risk
        if email := data.get("email"):
            try:
                email_risk = await self.email_tool.assess(email)
                context.email_risk = asdict(email_risk)

                if email_risk.is_disposable:
                    risk_indicators.append("Disposable email address detected")
                    anomalies.append("DISPOSABLE_EMAIL")
                if email_risk.domain_age_days < 30:
                    risk_indicators.append(
                        f"Very new email domain ({email_risk.domain_age_days} days old)"
                    )
                    anomalies.append("NEW_EMAIL_DOMAIN")
                if email_risk.breach_count > 0:
                    risk_indicators.append(
                        f"Email found in {email_risk.breach_count} data breach(es)"
                    )

                state.add_log(
                    self.name, "Email assessment complete", {"risk_score": email_risk.risk_score}
                )
            except Exception as e:
                logger.error(f"Email assessment failed: {e}")
                state.errors.append(f"Email assessment failed: {str(e)}")

        # Check velocity
        if user_id := data.get("user_id"):
            try:
                velocity = await self.velocity_tool.check(user_id)
                context.velocity_check = velocity

                if "HIGH_VELOCITY" in velocity.get("flags", []):
                    risk_indicators.append(
                        f"High transaction velocity: {velocity['transaction_count']} in 24h"
                    )
                    anomalies.append("HIGH_VELOCITY")
                if "MULTIPLE_LOCATIONS" in velocity.get("flags", []):
                    risk_indicators.append("Transactions from multiple distant locations")
                    anomalies.append("IMPOSSIBLE_TRAVEL")

                state.add_log(
                    self.name, "Velocity check complete", {"risk_score": velocity.get("risk_score")}
                )
            except Exception as e:
                logger.error(f"Velocity check failed: {e}")
                state.errors.append(f"Velocity check failed: {str(e)}")

        # Verify addresses (for orders)
        shipping = data.get("shipping_address")
        billing = data.get("billing_address")
        if shipping and billing:
            try:
                address_check = await self.address_tool.verify(shipping, billing)
                context.address_verification = address_check

                if not address_check.get("addresses_match"):
                    risk_indicators.append("Shipping and billing addresses don't match")
                if address_check.get("is_freight_forwarder"):
                    risk_indicators.append("Shipping to known freight forwarder")
                    anomalies.append("FREIGHT_FORWARDER")

                state.add_log(
                    self.name,
                    "Address verification complete",
                    {"risk_score": address_check.get("risk_score")},
                )
            except Exception as e:
                logger.error(f"Address verification failed: {e}")
                state.errors.append(f"Address verification failed: {str(e)}")

        # Store gathered context
        context.risk_indicators = risk_indicators
        context.anomalies_detected = anomalies
        state.context = context

        state.add_log(
            self.name,
            f"Context gathering complete: {len(risk_indicators)} risk indicators found",
            {"risk_indicators": risk_indicators, "anomalies": anomalies},
        )

        logger.info(
            f"Context gathered for alert {alert.alert_id}: {len(risk_indicators)} indicators"
        )

        return state

    def get_context_summary(self, state: WorkflowState) -> str:
        """Generate a human-readable summary of gathered context."""
        context = state.context
        lines = ["=== Context Summary ==="]

        if context.ip_info:
            ip = context.ip_info
            lines.append(
                f"IP: {ip.get('country', 'Unknown')} | VPN: {ip.get('is_vpn')} | Risk: {ip.get('risk_score', 0):.0f}"
            )

        if context.device_info:
            dev = context.device_info
            lines.append(
                f"Device: {dev.get('device_type', 'Unknown')} | Emulator: {dev.get('is_emulator')} | Users: {dev.get('associated_users', 1)}"
            )

        if context.email_risk:
            email = context.email_risk
            lines.append(
                f"Email: Disposable: {email.get('is_disposable')} | Domain Age: {email.get('domain_age_days', 0)} days"
            )

        if context.velocity_check:
            vel = context.velocity_check
            lines.append(
                f"Velocity: {vel.get('transaction_count', 0)} txns in 24h | Total: ${vel.get('total_amount', 0):,.2f}"
            )

        if context.risk_indicators:
            lines.append("\nRisk Indicators:")
            for indicator in context.risk_indicators:
                lines.append(f"  - {indicator}")

        return "\n".join(lines)
