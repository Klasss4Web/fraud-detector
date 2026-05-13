"""
Identity Fraud Detection Agent
===============================

Specialized agent for detecting identity fraud:
- Synthetic identity fraud
- Account takeover
- Identity theft
- New account fraud
"""

from typing import Dict, Any, List
from .base_agent import BaseAgent, AgentResult, FraudSignal


class IdentityFraudAgent(BaseAgent):
    """Agent specialized in detecting identity fraud"""

    # Thresholds
    NEW_ACCOUNT_DAYS = 30
    SUSPICIOUS_DEVICE_COUNT = 5
    SUSPICIOUS_IP_COUNT = 10
    LOGIN_ANOMALY_THRESHOLD = 5

    # Suspicious email domains
    DISPOSABLE_EMAIL_DOMAINS = [
        "tempmail.com",
        "guerrillamail.com",
        "10minutemail.com",
        "throwaway.com",
        "mailinator.com",
        "temp-mail.org",
        "fakeinbox.com",
        "getnada.com",
        "yopmail.com",
        "trashmail.com",
        ]

    HIGH_RISK_EMAIL_DOMAINS = ["mail.ru", "yandex.com", "protonmail.com"]

    def __init__(self):
        super().__init__("IdentityFraudAgent")

    def analyze(self, data: Dict[str, Any]) -> AgentResult:
        """Analyze a user profile for identity fraud signals"""
        self.log(f"Analyzing user {data.get('user_id', 'unknown')}")

        signals = []
        risk_score = 0

        # 1. Email Analysis
        email_score, email_signals = self._analyze_email(data)
        risk_score += email_score
        signals.extend(email_signals)

        # 2. Account Age Analysis
        age_score, age_signals = self._analyze_account_age(data)
        risk_score += age_score
        signals.extend(age_signals)

        # 3. Device Patterns
        device_score, device_signals = self._analyze_devices(data)
        risk_score += device_score
        signals.extend(device_signals)

        # 4. Login Behavior
        login_score, login_signals = self._analyze_login_behavior(data)
        risk_score += login_score
        signals.extend(login_signals)

        # 5. Verification Failures
        verify_score, verify_signals = self._analyze_verifications(data)
        risk_score += verify_score
        signals.extend(verify_signals)

        # 6. Synthetic Identity Indicators
        synthetic_score, synthetic_signals = self._detect_synthetic_identity(data)
        risk_score += synthetic_score
        signals.extend(synthetic_signals)

        # Determine fraud type
        fraud_type = self._determine_fraud_type(signals, data)

        recommendation = self._generate_recommendation(risk_score, fraud_type)

        return self._create_result(
            entity_id=data.get("user_id", "unknown"),
            risk_score=risk_score,
            signals=signals,
            recommendation=recommendation,
            details={
                "email_domain": data.get("email_domain"),
                "account_age_days": data.get("account_age_days"),
                "device_count": data.get("device_count"),
                "suspected_fraud_type": fraud_type,
            },
        )

    def _analyze_email(self, data: Dict[str, Any]) -> tuple:
        """Analyze email address for fraud indicators"""
        signals = []
        score = 0

        email_domain = data.get("email_domain", "").lower()

        if email_domain in self.DISPOSABLE_EMAIL_DOMAINS:
            score += 30
            signals.append(
                FraudSignal(
                    name="disposable_email",
                    description=f"Disposable email domain: {email_domain}",
                    weight=0.9,
                    category="email",
                )
            )
        elif email_domain in self.HIGH_RISK_EMAIL_DOMAINS:
            score += 15
            signals.append(
                FraudSignal(
                    name="high_risk_email",
                    description=f"High-risk email domain: {email_domain}",
                    weight=0.5,
                    category="email",
                )
            )

        return score, signals

    def _analyze_account_age(self, data: Dict[str, Any]) -> tuple:
        """Analyze account age patterns"""
        signals = []
        score = 0

        account_age = data.get("account_age_days", 365)

        if account_age < 7:
            score += 20
            signals.append(
                FraudSignal(
                    name="very_new_account",
                    description=f"Very new account: {account_age} days old",
                    weight=0.7,
                    category="account_age",
                )
            )
        elif account_age < self.NEW_ACCOUNT_DAYS:
            score += 10
            signals.append(
                FraudSignal(
                    name="new_account",
                    description=f"New account: {account_age} days old",
                    weight=0.4,
                    category="account_age",
                )
            )

        return score, signals

    def _analyze_devices(self, data: Dict[str, Any]) -> tuple:
        """Analyze device usage patterns"""
        signals = []
        score = 0

        device_count = data.get("device_count", 1)
        ip_count = data.get("ip_addresses_used", 1)

        if device_count > self.SUSPICIOUS_DEVICE_COUNT * 2:
            score += 25
            signals.append(
                FraudSignal(
                    name="excessive_devices",
                    description=f"Excessive devices: {device_count} unique devices",
                    weight=0.8,
                    category="device",
                )
            )
        elif device_count > self.SUSPICIOUS_DEVICE_COUNT:
            score += 15
            signals.append(
                FraudSignal(
                    name="multiple_devices",
                    description=f"Multiple devices: {device_count} unique devices",
                    weight=0.5,
                    category="device",
                )
            )

        if ip_count > self.SUSPICIOUS_IP_COUNT * 2:
            score += 20
            signals.append(
                FraudSignal(
                    name="excessive_ips",
                    description=f"Excessive IP addresses: {ip_count}",
                    weight=0.7,
                    category="device",
                )
            )
        elif ip_count > self.SUSPICIOUS_IP_COUNT:
            score += 10
            signals.append(
                FraudSignal(
                    name="multiple_ips",
                    description=f"Multiple IP addresses: {ip_count}",
                    weight=0.4,
                    category="device",
                )
            )

        return score, signals

    def _analyze_login_behavior(self, data: Dict[str, Any]) -> tuple:
        """Analyze login behavior anomalies"""
        signals = []
        score = 0

        login_anomalies = data.get("login_anomalies", 0)

        if login_anomalies > self.LOGIN_ANOMALY_THRESHOLD * 2:
            score += 25
            signals.append(
                FraudSignal(
                    name="severe_login_anomalies",
                    description=f"Severe login anomalies: {login_anomalies} detected",
                    weight=0.85,
                    category="behavior",
                )
            )
        elif login_anomalies > self.LOGIN_ANOMALY_THRESHOLD:
            score += 15
            signals.append(
                FraudSignal(
                    name="login_anomalies",
                    description=f"Login anomalies detected: {login_anomalies}",
                    weight=0.6,
                    category="behavior",
                )
            )

        return score, signals

    def _analyze_verifications(self, data: Dict[str, Any]) -> tuple:
        """Analyze verification failure patterns"""
        signals = []
        score = 0

        failed_verifications = data.get("failed_verifications", 0)

        if failed_verifications > 5:
            score += 25
            signals.append(
                FraudSignal(
                    name="many_failed_verifications",
                    description=f"Many failed verifications: {failed_verifications}",
                    weight=0.8,
                    category="verification",
                )
            )
        elif failed_verifications > 2:
            score += 15
            signals.append(
                FraudSignal(
                    name="failed_verifications",
                    description=f"Failed verifications: {failed_verifications}",
                    weight=0.5,
                    category="verification",
                )
            )

        return score, signals

    def _detect_synthetic_identity(self, data: Dict[str, Any]) -> tuple:
        """Detect synthetic identity patterns"""
        signals = []
        score = 0

        # Combination of factors indicating synthetic identity
        is_new = data.get("account_age_days", 365) < 30
        has_disposable_email = (
            data.get("email_domain", "") in self.DISPOSABLE_EMAIL_DOMAINS
        )
        many_devices = data.get("device_count", 1) > 3
        many_ips = data.get("ip_addresses_used", 1) > 5

        synthetic_indicators = sum(
            [is_new, has_disposable_email, many_devices, many_ips]
        )

        if synthetic_indicators >= 3:
            score += 20
            signals.append(
                FraudSignal(
                    name="synthetic_identity_pattern",
                    description="Multiple indicators of synthetic identity",
                    weight=0.85,
                    category="synthetic",
                )
            )

        return score, signals

    def _determine_fraud_type(
        self, signals: List[FraudSignal], data: Dict[str, Any]
    ) -> str:
        """Determine the most likely fraud type"""
        signal_names = [s.name for s in signals]

        if (
            "synthetic_identity_pattern" in signal_names
            or "disposable_email" in signal_names
        ):
            return "synthetic_identity"
        elif (
            "severe_login_anomalies" in signal_names
            and data.get("account_age_days", 0) > 90
        ):
            return "account_takeover"
        elif "very_new_account" in signal_names:
            return "new_account_fraud"
        elif len(signals) > 3:
            return "identity_theft"
        else:
            return "low_risk"

    def _generate_recommendation(self, score: float, fraud_type: str) -> str:
        """Generate action recommendation"""
        if score >= 80:
            return f"BLOCK: High probability of {fraud_type}. Suspend account and require identity verification."
        elif score >= 60:
            return f"VERIFY: Suspected {fraud_type}. Require additional identity verification (ID upload, video call)."
        elif score >= 40:
            return f"MONITOR: Possible {fraud_type} indicators. Enhanced monitoring and step-up authentication."
        else:
            return "ALLOW: Identity appears legitimate. Continue standard monitoring."
