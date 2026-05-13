"""
External tools for the fraud detection agents.
These tools provide the agents with "sensors" to gather context.
"""

import hashlib
import random
from datetime import datetime, timedelta
from typing import Any, Optional
from dataclasses import dataclass

from utils.helpers import mask_ip_address, mask_email, is_disposable_email_domain


@dataclass
class IPInfo:
    """IP geolocation and risk information."""

    ip_address: str
    country: str
    country_code: str
    city: str
    region: str
    latitude: float
    longitude: float
    isp: str
    is_vpn: bool
    is_proxy: bool
    is_tor: bool
    is_datacenter: bool
    risk_score: float
    timezone: str


@dataclass
class DeviceInfo:
    """Device fingerprint information."""

    device_id: str
    device_type: str  # mobile, desktop, tablet
    os: str
    browser: str
    is_emulator: bool
    is_rooted: bool
    first_seen: str
    times_seen: int
    associated_users: int
    risk_score: float


@dataclass
class EmailRisk:
    """Email risk assessment."""

    email: str
    domain: str
    is_disposable: bool
    is_free_provider: bool
    domain_age_days: int
    has_mx_records: bool
    deliverable: bool
    risk_score: float
    breach_count: int


class IPInfoTool:
    """
    Tool for IP geolocation and risk assessment.
    In production, integrate with MaxMind, IPinfo, or similar APIs.
    """

    HIGH_RISK_COUNTRIES = {"NG", "RU", "CN", "KP", "IR", "VE", "MM"}
    VPN_ISPS = {"NordVPN", "ExpressVPN", "Mullvad", "Private Internet Access"}

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key

    async def lookup(self, ip_address: str) -> IPInfo:
        """
        Look up IP information.

        In production, this would call an external API like:
        - MaxMind GeoIP2
        - IPinfo.io
        - IP2Location
        """
        # Simulated lookup - replace with real API call
        # This is a mock implementation for demonstration

        is_private = ip_address.startswith(("10.", "192.168.", "172."))

        # Simulate different scenarios based on IP patterns
        if is_private:
            return IPInfo(
                ip_address=mask_ip_address(ip_address),
                country="United States",
                country_code="US",
                city="Unknown (Private IP)",
                region="Unknown",
                latitude=0.0,
                longitude=0.0,
                isp="Private Network",
                is_vpn=False,
                is_proxy=False,
                is_tor=False,
                is_datacenter=False,
                risk_score=10.0,
                timezone="America/New_York",
            )

        # Simulate risk assessment based on IP hash for consistency
        ip_hash = int(hashlib.md5(ip_address.encode()).hexdigest()[:8], 16)
        risk_factor = (ip_hash % 100) / 100.0

        is_vpn = risk_factor > 0.85
        is_proxy = risk_factor > 0.90
        is_datacenter = risk_factor > 0.80

        countries = [
            ("United States", "US", "New York", 40.7128, -74.0060),
            ("United Kingdom", "GB", "London", 51.5074, -0.1278),
            ("Germany", "DE", "Berlin", 52.5200, 13.4050),
            ("Nigeria", "NG", "Lagos", 6.5244, 3.3792),
            ("Russia", "RU", "Moscow", 55.7558, 37.6173),
        ]

        country_idx = ip_hash % len(countries)
        country, code, city, lat, lon = countries[country_idx]

        risk_score = 20.0
        if code in self.HIGH_RISK_COUNTRIES:
            risk_score += 40.0
        if is_vpn or is_proxy:
            risk_score += 25.0
        if is_datacenter:
            risk_score += 15.0

        return IPInfo(
            ip_address=mask_ip_address(ip_address),
            country=country,
            country_code=code,
            city=city,
            region=city,
            latitude=lat,
            longitude=lon,
            isp="Sample ISP Inc.",
            is_vpn=is_vpn,
            is_proxy=is_proxy,
            is_tor=False,
            is_datacenter=is_datacenter,
            risk_score=min(100.0, risk_score),
            timezone="UTC",
        )


class DeviceFingerprintTool:
    """
    Tool for device fingerprint analysis.
    In production, integrate with Fingerprint.com or similar.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key

    async def lookup(self, device_id: str) -> DeviceInfo:
        """
        Look up device information.

        In production, this would call Fingerprint.com or similar API.
        """
        # Simulated lookup
        device_hash = int(hashlib.md5(device_id.encode()).hexdigest()[:8], 16)

        device_types = ["mobile", "desktop", "tablet"]
        os_list = ["iOS 17", "Android 14", "Windows 11", "macOS 14"]
        browsers = ["Chrome", "Safari", "Firefox", "Edge"]

        # Simulate suspicious device patterns
        is_emulator = (device_hash % 100) > 95
        is_rooted = (device_hash % 100) > 90
        associated_users = (device_hash % 10) + 1

        risk_score = 15.0
        if is_emulator:
            risk_score += 35.0
        if is_rooted:
            risk_score += 20.0
        if associated_users > 3:
            risk_score += 25.0

        return DeviceInfo(
            device_id=device_id[:8] + "..." + device_id[-4:] if len(device_id) > 12 else device_id,
            device_type=device_types[device_hash % len(device_types)],
            os=os_list[device_hash % len(os_list)],
            browser=browsers[device_hash % len(browsers)],
            is_emulator=is_emulator,
            is_rooted=is_rooted,
            first_seen=(datetime.utcnow() - timedelta(days=device_hash % 365)).isoformat(),
            times_seen=(device_hash % 50) + 1,
            associated_users=associated_users,
            risk_score=min(100.0, risk_score),
        )


class EmailRiskTool:
    """
    Tool for email risk assessment.
    In production, integrate with Sift, SEON, or similar.
    """

    FREE_PROVIDERS = {
        "gmail.com",
        "yahoo.com",
        "hotmail.com",
        "outlook.com",
        "aol.com",
        "icloud.com",
    }

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key

    async def assess(self, email: str) -> EmailRisk:
        """
        Assess email risk.

        In production, this would call email verification APIs.
        """
        domain = email.split("@")[-1].lower() if "@" in email else ""
        email_hash = int(hashlib.md5(email.encode()).hexdigest()[:8], 16)

        is_disposable = is_disposable_email_domain(email)
        is_free = domain in self.FREE_PROVIDERS

        # Simulate domain age and other checks
        domain_age = email_hash % 3650  # 0-10 years in days
        has_mx = (email_hash % 100) > 5  # 95% have MX records
        deliverable = (email_hash % 100) > 10  # 90% deliverable
        breach_count = email_hash % 5  # 0-4 breaches

        risk_score = 10.0
        if is_disposable:
            risk_score += 50.0
        if domain_age < 30:
            risk_score += 30.0
        elif domain_age < 90:
            risk_score += 15.0
        if not has_mx:
            risk_score += 25.0
        if breach_count > 0:
            risk_score += breach_count * 5.0

        return EmailRisk(
            email=mask_email(email),
            domain=domain,
            is_disposable=is_disposable,
            is_free_provider=is_free,
            domain_age_days=domain_age,
            has_mx_records=has_mx,
            deliverable=deliverable,
            risk_score=min(100.0, risk_score),
            breach_count=breach_count,
        )


class VelocityCheckTool:
    """
    Tool for checking transaction velocity patterns.
    """

    def __init__(self):
        pass

    async def check(
        self,
        user_id: str,
        timeframe_hours: int = 24,
    ) -> dict[str, Any]:
        """
        Check transaction velocity for a user.

        In production, this would query your transaction database.
        """
        # Simulated velocity check
        user_hash = int(hashlib.md5(user_id.encode()).hexdigest()[:8], 16)

        transaction_count = user_hash % 20
        total_amount = (user_hash % 10000) + (transaction_count * 100)
        unique_merchants = min(transaction_count, (user_hash % 10) + 1)
        unique_locations = min(transaction_count, (user_hash % 5) + 1)

        # Calculate velocity risk
        risk_score = 10.0
        if transaction_count > 10:
            risk_score += 30.0
        if total_amount > 5000:
            risk_score += 25.0
        if unique_locations > 3:
            risk_score += 20.0  # Impossible travel indicator

        return {
            "user_id": user_id,
            "timeframe_hours": timeframe_hours,
            "transaction_count": transaction_count,
            "total_amount": total_amount,
            "unique_merchants": unique_merchants,
            "unique_locations": unique_locations,
            "average_amount": total_amount / max(1, transaction_count),
            "risk_score": min(100.0, risk_score),
            "flags": [
                flag
                for flag, condition in [
                    ("HIGH_VELOCITY", transaction_count > 10),
                    ("HIGH_TOTAL_AMOUNT", total_amount > 5000),
                    ("MULTIPLE_LOCATIONS", unique_locations > 3),
                ]
                if condition
            ],
        }


class AddressVerificationTool:
    """
    Tool for address verification.
    """

    KNOWN_FREIGHT_FORWARDERS = ["myus", "shipito", "stackry", "planet express", "forward2me"]

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key

    async def verify(
        self,
        shipping_address: str,
        billing_address: str,
    ) -> dict[str, Any]:
        """
        Verify and compare addresses.

        In production, this would use address validation APIs.
        """
        shipping_lower = shipping_address.lower()
        billing_lower = billing_address.lower()

        # Check for freight forwarder
        is_freight_forwarder = any(ff in shipping_lower for ff in self.KNOWN_FREIGHT_FORWARDERS)

        # Simple address match check
        addresses_match = shipping_lower == billing_lower

        # Check for PO Box
        is_po_box = "po box" in shipping_lower or "p.o. box" in shipping_lower

        risk_score = 10.0
        if not addresses_match:
            risk_score += 20.0
        if is_freight_forwarder:
            risk_score += 40.0
        if is_po_box:
            risk_score += 10.0

        return {
            "shipping_address": shipping_address,
            "billing_address": billing_address,
            "addresses_match": addresses_match,
            "is_freight_forwarder": is_freight_forwarder,
            "is_po_box": is_po_box,
            "shipping_verified": True,  # Would be actual verification result
            "billing_verified": True,
            "risk_score": min(100.0, risk_score),
            "flags": [
                flag
                for flag, condition in [
                    ("ADDRESS_MISMATCH", not addresses_match),
                    ("FREIGHT_FORWARDER", is_freight_forwarder),
                    ("PO_BOX", is_po_box),
                ]
                if condition
            ],
        }


# Tool registry for easy access
TOOLS = {
    "ip_info": IPInfoTool,
    "device_fingerprint": DeviceFingerprintTool,
    "email_risk": EmailRiskTool,
    "velocity_check": VelocityCheckTool,
    "address_verification": AddressVerificationTool,
}
