"""
Real external service integrations for fraud detection.
Replaces mocked tools with actual API calls.
"""

import os
import logging
import httpx
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from math import radians, sin, cos, sqrt, atan2
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# ============== IP Intelligence Service ==============


@dataclass
class IPIntelligence:
    """IP intelligence data."""

    ip: str
    country: str
    country_code: str
    city: str
    region: str
    latitude: float
    longitude: float
    isp: str
    org: str
    is_vpn: bool
    is_proxy: bool
    is_tor: bool
    is_datacenter: bool
    is_bogon: bool
    risk_score: float
    timezone: str


class IPIntelligenceService:
    """
    IP intelligence service with multiple provider support.

    Supports:
    - IPinfo.io (default, free tier available)
    - MaxMind GeoIP2 (requires license)
    - IP-API (free, no key required)
    """

    def __init__(self):
        self.ipinfo_token = os.getenv("IPINFO_TOKEN")
        self.maxmind_key = os.getenv("MAXMIND_LICENSE_KEY")
        self._cache = {}  # Simple in-memory cache, use Redis in production

    async def lookup(self, ip: str) -> Optional[IPIntelligence]:
        """Look up IP intelligence data."""
        # Check cache first
        if ip in self._cache:
            cached, timestamp = self._cache[ip]
            if datetime.utcnow() - timestamp < timedelta(hours=1):
                return cached

        # Try providers in order of preference
        result = None

        if self.ipinfo_token:
            result = await self._lookup_ipinfo(ip)

        if not result:
            result = await self._lookup_ip_api(ip)

        if result:
            self._cache[ip] = (result, datetime.utcnow())

        return result

    async def _lookup_ipinfo(self, ip: str) -> Optional[IPIntelligence]:
        """Look up IP using IPinfo.io."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://ipinfo.io/{ip}", params={"token": self.ipinfo_token}, timeout=5.0
                )

                if response.status_code != 200:
                    logger.warning(f"IPinfo lookup failed: {response.status_code}")
                    return None

                data = response.json()

                # Parse location
                loc = data.get("loc", "0,0").split(",")
                lat = float(loc[0]) if len(loc) > 0 else 0.0
                lon = float(loc[1]) if len(loc) > 1 else 0.0

                # Detect VPN/proxy indicators
                org = data.get("org", "").lower()
                is_vpn = any(x in org for x in ["vpn", "proxy", "hosting", "cloud"])

                return IPIntelligence(
                    ip=ip,
                    country=data.get("country", "Unknown"),
                    country_code=data.get("country", "XX"),
                    city=data.get("city", "Unknown"),
                    region=data.get("region", "Unknown"),
                    latitude=lat,
                    longitude=lon,
                    isp=data.get("org", "Unknown"),
                    org=data.get("org", "Unknown"),
                    is_vpn=is_vpn,
                    is_proxy=is_vpn,
                    is_tor=False,
                    is_datacenter="hosting" in org or "cloud" in org,
                    is_bogon=ip.startswith(("10.", "192.168.", "172.16.")),
                    risk_score=self._calculate_ip_risk(data, is_vpn),
                    timezone=data.get("timezone", "UTC"),
                )

        except Exception as e:
            logger.error(f"IPinfo lookup error: {e}")
            return None

    async def _lookup_ip_api(self, ip: str) -> Optional[IPIntelligence]:
        """Look up IP using ip-api.com (free, no key required)."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"http://ip-api.com/json/{ip}",
                    params={
                        "fields": "status,country,countryCode,region,city,lat,lon,timezone,isp,org,proxy,hosting"
                    },
                    timeout=5.0,
                )

                if response.status_code != 200:
                    return None

                data = response.json()

                if data.get("status") != "success":
                    return None

                is_vpn = data.get("proxy", False) or data.get("hosting", False)

                return IPIntelligence(
                    ip=ip,
                    country=data.get("country", "Unknown"),
                    country_code=data.get("countryCode", "XX"),
                    city=data.get("city", "Unknown"),
                    region=data.get("region", "Unknown"),
                    latitude=data.get("lat", 0.0),
                    longitude=data.get("lon", 0.0),
                    isp=data.get("isp", "Unknown"),
                    org=data.get("org", "Unknown"),
                    is_vpn=is_vpn,
                    is_proxy=data.get("proxy", False),
                    is_tor=False,
                    is_datacenter=data.get("hosting", False),
                    is_bogon=ip.startswith(("10.", "192.168.", "172.16.")),
                    risk_score=self._calculate_ip_risk(data, is_vpn),
                    timezone=data.get("timezone", "UTC"),
                )

        except Exception as e:
            logger.error(f"IP-API lookup error: {e}")
            return None

    def _calculate_ip_risk(self, data: Dict, is_vpn: bool) -> float:
        """Calculate IP risk score (0-100)."""
        score = 0.0

        # High-risk countries
        high_risk_countries = {"NG", "RU", "CN", "IN", "BR", "UA", "RO", "ID", "PH", "VN"}
        country_code = data.get("countryCode", data.get("country", ""))
        if country_code in high_risk_countries:
            score += 30

        # VPN/Proxy/Datacenter
        if is_vpn:
            score += 40

        # Private/Bogon IP
        if str(data.get("ip", "")).startswith(("10.", "192.168.", "172.16.")):
            score += 25

        return min(score, 100)


# ============== Impossible Travel Detection ==============


class ImpossibleTravelDetector:
    """
    Detects impossible travel scenarios.

    Compares the distance between two locations against the time elapsed
    to determine if travel between them is physically possible.
    """

    # Maximum reasonable travel speeds (km/h)
    MAX_SPEEDS = {
        "car": 150,  # Highway speed
        "train": 350,  # High-speed rail
        "plane": 900,  # Commercial aircraft
    }

    # Threshold for flagging (using plane speed with buffer)
    MAX_SPEED_KMH = 1000  # km/h (faster than commercial flights)

    @staticmethod
    def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate the distance between two points on Earth using Haversine formula.

        Returns:
            Distance in kilometers
        """
        R = 6371  # Earth's radius in kilometers

        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        return R * c

    @classmethod
    def check_impossible_travel(
        cls, lat1: float, lon1: float, time1: datetime, lat2: float, lon2: float, time2: datetime
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if travel between two locations in the given time is impossible.

        Returns:
            Tuple of (is_impossible, details)
        """
        # Calculate distance
        distance_km = cls.haversine_distance(lat1, lon1, lat2, lon2)

        # Calculate time elapsed in hours
        time_diff = abs((time2 - time1).total_seconds()) / 3600

        # Avoid division by zero
        if time_diff < 0.01:  # Less than 36 seconds
            time_diff = 0.01

        # Calculate required speed
        required_speed = distance_km / time_diff

        # Determine if impossible
        is_impossible = required_speed > cls.MAX_SPEED_KMH

        # Calculate what's reasonable
        min_travel_time_hours = distance_km / cls.MAX_SPEED_KMH

        details = {
            "distance_km": round(distance_km, 2),
            "time_elapsed_hours": round(time_diff, 2),
            "required_speed_kmh": round(required_speed, 2),
            "max_reasonable_speed_kmh": cls.MAX_SPEED_KMH,
            "min_travel_time_hours": round(min_travel_time_hours, 2),
            "is_impossible": is_impossible,
            "risk_score": min(100, (required_speed / cls.MAX_SPEED_KMH) * 50)
            if is_impossible
            else 0,
        }

        return is_impossible, details


# ============== Email Risk Service ==============


@dataclass
class EmailRisk:
    """Email risk assessment data."""

    email: str
    domain: str
    is_disposable: bool
    is_free_provider: bool
    is_valid_format: bool
    domain_age_days: Optional[int]
    has_mx_records: bool
    risk_score: float
    risk_factors: list


class EmailRiskService:
    """
    Email risk assessment service.

    Checks for disposable emails, domain reputation, and other risk factors.
    """

    # Known disposable email domains
    DISPOSABLE_DOMAINS = {
        "tempmail.com",
        "guerrillamail.com",
        "10minutemail.com",
        "mailinator.com",
        "throwaway.email",
        "temp-mail.org",
        "fakemailgenerator.com",
        "getnada.com",
        "maildrop.cc",
        "yopmail.com",
        "tempail.com",
        "dispostable.com",
    }

    # Free email providers (not necessarily risky, but noteworthy)
    FREE_PROVIDERS = {
        "gmail.com",
        "yahoo.com",
        "hotmail.com",
        "outlook.com",
        "aol.com",
        "icloud.com",
        "protonmail.com",
        "mail.com",
        "zoho.com",
        "gmx.com",
    }

    def __init__(self):
        self.abstract_api_key = os.getenv("ABSTRACT_API_KEY")

    async def assess_risk(self, email: str) -> EmailRisk:
        """Assess email risk."""
        import re

        # Basic validation
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        is_valid = bool(re.match(email_pattern, email))

        # Extract domain
        domain = email.split("@")[-1].lower() if "@" in email else ""

        # Check for disposable
        is_disposable = domain in self.DISPOSABLE_DOMAINS

        # Check for free provider
        is_free = domain in self.FREE_PROVIDERS

        # Calculate risk factors
        risk_factors = []
        risk_score = 0.0

        if not is_valid:
            risk_factors.append("Invalid email format")
            risk_score += 50

        if is_disposable:
            risk_factors.append("Disposable email domain")
            risk_score += 60

        if is_free and not is_disposable:
            risk_factors.append("Free email provider")
            risk_score += 10

        # Check for suspicious patterns
        local_part = email.split("@")[0] if "@" in email else email

        if len(local_part) > 30:
            risk_factors.append("Unusually long local part")
            risk_score += 15

        if re.search(r"\d{6,}", local_part):
            risk_factors.append("Many consecutive digits")
            risk_score += 20

        if re.search(r"[._-]{3,}", local_part):
            risk_factors.append("Unusual character patterns")
            risk_score += 15

        # Try external API if available
        if self.abstract_api_key:
            external_data = await self._check_abstract_api(email)
            if external_data:
                if not external_data.get("deliverability", True):
                    risk_factors.append("Email not deliverable")
                    risk_score += 40

        return EmailRisk(
            email=email,
            domain=domain,
            is_disposable=is_disposable,
            is_free_provider=is_free,
            is_valid_format=is_valid,
            domain_age_days=None,  # Would need WHOIS lookup
            has_mx_records=True,  # Would need DNS lookup
            risk_score=min(risk_score, 100),
            risk_factors=risk_factors,
        )

    async def _check_abstract_api(self, email: str) -> Optional[Dict]:
        """Check email using Abstract API."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://emailvalidation.abstractapi.com/v1/",
                    params={"api_key": self.abstract_api_key, "email": email},
                    timeout=5.0,
                )

                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            logger.error(f"Abstract API error: {e}")

        return None


# ============== Dynamic Threshold Service ==============


class DynamicThresholdService:
    """
    Service for calculating dynamic, user-specific thresholds.

    Instead of static rules like "flag if velocity > 10", this service
    calculates thresholds based on each user's historical behavior.
    """

    def __init__(self, db_session=None, redis_cache=None):
        self.db = db_session
        self.cache = redis_cache

    def get_user_thresholds(self, customer_id: str) -> Dict[str, Any]:
        """
        Get dynamic thresholds for a user based on their history.

        Returns thresholds for:
        - amount: max normal transaction amount
        - velocity_1h, velocity_24h: max normal transaction counts
        - locations: list of typical locations
        """
        # Try cache first
        if self.cache:
            cached = self.cache.get(f"thresholds:{customer_id}")
            if cached:
                import json

                return json.loads(cached)

        # Calculate from database
        thresholds = self._calculate_thresholds(customer_id)

        # Cache for 1 hour
        if self.cache:
            import json

            self.cache.set(f"thresholds:{customer_id}", json.dumps(thresholds), ttl=3600)

        return thresholds

    def _calculate_thresholds(self, customer_id: str) -> Dict[str, Any]:
        """Calculate thresholds from user history."""
        if not self.db:
            return self._get_default_thresholds()

        from db.repository import TransactionRepository, UserProfileRepository

        tx_repo = TransactionRepository(self.db)
        profile_repo = UserProfileRepository(self.db)

        # Get user stats
        stats = tx_repo.get_customer_stats(customer_id, days=30)
        profile = profile_repo.get_or_create(customer_id)

        # Calculate dynamic thresholds
        avg_amount = stats.get("avg_amount", 100)
        max_amount = stats.get("max_amount", 500)
        tx_count = stats.get("transaction_count", 0)

        # Amount threshold: 3x average or 1.5x historical max, whichever is higher
        amount_threshold = max(avg_amount * 3, max_amount * 1.5, 1000)  # Min $1000

        # Velocity threshold: 3x average daily rate
        avg_daily = tx_count / 30 if tx_count > 0 else 1
        velocity_24h_threshold = max(avg_daily * 3, 5)  # Min 5 transactions
        velocity_1h_threshold = max(avg_daily * 0.5, 3)  # Min 3 transactions

        return {
            "customer_id": customer_id,
            "amount_threshold": round(amount_threshold, 2),
            "velocity_24h_threshold": int(velocity_24h_threshold),
            "velocity_1h_threshold": int(velocity_1h_threshold),
            "typical_locations": profile.typical_locations or [],
            "typical_merchants": profile.typical_merchants or [],
            "avg_amount_30d": round(avg_amount, 2),
            "max_amount_30d": round(max_amount, 2),
            "baseline_updated_at": datetime.utcnow().isoformat(),
        }

    def _get_default_thresholds(self) -> Dict[str, Any]:
        """Get default thresholds for new users or when DB unavailable."""
        return {
            "customer_id": "default",
            "amount_threshold": 2000.0,
            "velocity_24h_threshold": 10,
            "velocity_1h_threshold": 5,
            "typical_locations": [],
            "typical_merchants": [],
            "avg_amount_30d": 150.0,
            "max_amount_30d": 500.0,
            "baseline_updated_at": datetime.utcnow().isoformat(),
        }

    def check_amount_anomaly(
        self, customer_id: str, amount: float, thresholds: Dict[str, Any] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if transaction amount is anomalous for this user.

        Returns:
            Tuple of (is_anomalous, details)
        """
        if not thresholds:
            thresholds = self.get_user_thresholds(customer_id)

        threshold = thresholds["amount_threshold"]
        avg_amount = thresholds["avg_amount_30d"]

        # Calculate deviation
        deviation = (amount - avg_amount) / avg_amount if avg_amount > 0 else 0

        is_anomalous = amount > threshold

        details = {
            "amount": amount,
            "threshold": threshold,
            "avg_amount_30d": avg_amount,
            "deviation_factor": round(deviation, 2),
            "is_anomalous": is_anomalous,
            "risk_score": min(100, deviation * 20) if is_anomalous else 0,
        }

        return is_anomalous, details

    def check_velocity_anomaly(
        self,
        customer_id: str,
        current_velocity: int,
        window: str = "24h",
        thresholds: Dict[str, Any] = None,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if transaction velocity is anomalous for this user.

        Returns:
            Tuple of (is_anomalous, details)
        """
        if not thresholds:
            thresholds = self.get_user_thresholds(customer_id)

        threshold_key = f"velocity_{window}_threshold"
        threshold = thresholds.get(threshold_key, 10)

        is_anomalous = current_velocity > threshold

        details = {
            "current_velocity": current_velocity,
            "threshold": threshold,
            "window": window,
            "is_anomalous": is_anomalous,
            "risk_score": min(100, (current_velocity / threshold - 1) * 30) if is_anomalous else 0,
        }

        return is_anomalous, details


# ============== Combined Risk Enrichment Service ==============


class RiskEnrichmentService:
    """
    Combined service that enriches transactions with risk data from all sources.
    """

    def __init__(self, db_session=None, redis_cache=None):
        self.ip_service = IPIntelligenceService()
        self.email_service = EmailRiskService()
        self.threshold_service = DynamicThresholdService(db_session, redis_cache)
        self.travel_detector = ImpossibleTravelDetector()
        self.db = db_session

    async def enrich_transaction(
        self, transaction: Dict[str, Any], previous_location: Tuple[float, float, datetime] = None
    ) -> Dict[str, Any]:
        """
        Enrich a transaction with risk data from all sources.

        Returns:
            Dictionary with enriched risk data
        """
        enrichment = {
            "ip_intelligence": None,
            "email_risk": None,
            "dynamic_thresholds": None,
            "impossible_travel": None,
            "combined_risk_score": 0.0,
            "risk_factors": [],
        }

        customer_id = transaction.get("customer_id") or transaction.get("user_id")

        # IP Intelligence
        ip = transaction.get("ip_address")
        if ip:
            ip_intel = await self.ip_service.lookup(ip)
            if ip_intel:
                enrichment["ip_intelligence"] = {
                    "country": ip_intel.country,
                    "city": ip_intel.city,
                    "is_vpn": ip_intel.is_vpn,
                    "is_proxy": ip_intel.is_proxy,
                    "is_datacenter": ip_intel.is_datacenter,
                    "risk_score": ip_intel.risk_score,
                    "latitude": ip_intel.latitude,
                    "longitude": ip_intel.longitude,
                }

                if ip_intel.is_vpn:
                    enrichment["risk_factors"].append("VPN/Proxy detected")
                if ip_intel.risk_score > 50:
                    enrichment["risk_factors"].append(f"High-risk IP location: {ip_intel.country}")

        # Email Risk (if available)
        email = transaction.get("email")
        if email:
            email_risk = await self.email_service.assess_risk(email)
            enrichment["email_risk"] = {
                "is_disposable": email_risk.is_disposable,
                "is_free_provider": email_risk.is_free_provider,
                "risk_score": email_risk.risk_score,
                "risk_factors": email_risk.risk_factors,
            }

            if email_risk.is_disposable:
                enrichment["risk_factors"].append("Disposable email detected")

        # Dynamic Thresholds
        if customer_id:
            thresholds = self.threshold_service.get_user_thresholds(customer_id)
            enrichment["dynamic_thresholds"] = thresholds

            # Check amount anomaly
            amount = transaction.get("amount", 0)
            is_amount_anomaly, amount_details = self.threshold_service.check_amount_anomaly(
                customer_id, amount, thresholds
            )
            if is_amount_anomaly:
                enrichment["risk_factors"].append(
                    f"Amount ${amount} exceeds user threshold ${thresholds['amount_threshold']}"
                )
                enrichment["amount_anomaly"] = amount_details

        # Impossible Travel Detection
        if previous_location and ip and enrichment.get("ip_intelligence"):
            current_lat = enrichment["ip_intelligence"]["latitude"]
            current_lon = enrichment["ip_intelligence"]["longitude"]
            current_time = datetime.fromisoformat(
                transaction.get("timestamp", datetime.utcnow().isoformat()).replace("Z", "")
            )

            prev_lat, prev_lon, prev_time = previous_location

            is_impossible, travel_details = self.travel_detector.check_impossible_travel(
                prev_lat, prev_lon, prev_time, current_lat, current_lon, current_time
            )

            enrichment["impossible_travel"] = travel_details

            if is_impossible:
                enrichment["risk_factors"].append(
                    f"Impossible travel: {travel_details['distance_km']}km in {travel_details['time_elapsed_hours']}h"
                )

        # Calculate combined risk score
        scores = []

        if enrichment.get("ip_intelligence"):
            scores.append(enrichment["ip_intelligence"]["risk_score"])

        if enrichment.get("email_risk"):
            scores.append(enrichment["email_risk"]["risk_score"])

        if enrichment.get("amount_anomaly"):
            scores.append(enrichment["amount_anomaly"]["risk_score"])

        if enrichment.get("impossible_travel", {}).get("is_impossible"):
            scores.append(enrichment["impossible_travel"]["risk_score"])

        if scores:
            # Weighted average with emphasis on highest risk
            enrichment["combined_risk_score"] = round(
                (max(scores) * 0.5 + sum(scores) / len(scores) * 0.5), 2
            )

        return enrichment
