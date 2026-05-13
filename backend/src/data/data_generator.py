"""
Synthetic Data Generator for Fraud Detection System
====================================================

Generates realistic synthetic data for multiple fraud types:
- Financial/Transaction fraud
- Insurance claims fraud
- Identity fraud
- E-commerce fraud
"""

import random
import string
from datetime import datetime, timedelta
from typing import List, Dict, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
import uuid
import json


class FraudType(Enum):
    LEGITIMATE = "legitimate"
    TRANSACTION_FRAUD = "transaction_fraud"
    INSURANCE_FRAUD = "insurance_fraud"
    IDENTITY_FRAUD = "identity_fraud"
    ECOMMERCE_FRAUD = "ecommerce_fraud"


@dataclass
class Transaction:
    """Financial transaction record"""

    transaction_id: str
    user_id: str
    amount: float
    currency: str
    merchant_name: str
    merchant_category: str
    location: str
    ip_address: str
    device_id: str
    timestamp: str
    card_present: bool
    is_international: bool
    velocity_24h: int  # Number of transactions in last 24h
    avg_amount_30d: float  # Average transaction amount last 30 days
    is_fraud: bool = False
    fraud_type: str = "legitimate"
    fraud_indicators: List[str] = field(default_factory=list)


@dataclass
class InsuranceClaim:
    """Insurance claim record"""

    claim_id: str
    policy_id: str
    claimant_id: str
    claim_type: str  # auto, health, property, life
    claim_amount: float
    incident_date: str
    claim_date: str
    description: str
    location: str
    witnesses: int
    previous_claims_count: int
    policy_age_days: int
    time_to_claim_days: int
    is_fraud: bool = False
    fraud_type: str = "legitimate"
    fraud_indicators: List[str] = field(default_factory=list)


@dataclass
class UserProfile:
    """User identity profile"""

    user_id: str
    email: str
    phone: str
    ssn_last4: str
    address: str
    account_age_days: int
    email_domain: str
    phone_carrier: str
    device_count: int
    ip_addresses_used: int
    login_anomalies: int
    failed_verifications: int
    is_fraud: bool = False
    fraud_type: str = "legitimate"
    fraud_indicators: List[str] = field(default_factory=list)


@dataclass
class EcommerceOrder:
    """E-commerce order record"""

    order_id: str
    user_id: str
    items: List[Dict[str, Any]]
    total_amount: float
    shipping_address: str
    billing_address: str
    payment_method: str
    ip_address: str
    device_fingerprint: str
    timestamp: str
    is_new_customer: bool
    shipping_billing_match: bool
    express_shipping: bool
    high_risk_items: bool
    previous_chargebacks: int
    is_fraud: bool = False
    fraud_type: str = "legitimate"
    fraud_indicators: List[str] = field(default_factory=list)


class SyntheticDataGenerator:
    """Generates realistic synthetic fraud data"""

    MERCHANTS = [
        ("Amazon", "online_retail"),
        ("Walmart", "retail"),
        ("Shell", "gas_station"),
        ("Starbucks", "restaurant"),
        ("Apple Store", "electronics"),
        ("Best Buy", "electronics"),
        ("Netflix", "subscription"),
        ("Uber", "transport"),
        ("DoorDash", "food_delivery"),
        ("Home Depot", "home_improvement"),
        ("Target", "retail"),
        ("Costco", "wholesale"),
    ]

    LOCATIONS = [
        "New York, NY",
        "Los Angeles, CA",
        "Chicago, IL",
        "Houston, TX",
        "Phoenix, AZ",
        "Philadelphia, PA",
        "San Antonio, TX",
        "San Diego, CA",
        "Dallas, TX",
        "San Jose, CA",
        "London, UK",
        "Lagos, Nigeria",
        "Moscow, Russia",
        "Beijing, China",
        "Mumbai, India",
    ]

    HIGH_RISK_COUNTRIES = ["Nigeria", "Russia", "China", "Romania", "Indonesia"]

    CLAIM_TYPES = ["auto", "health", "property", "life"]

    PRODUCT_CATEGORIES = [
        {"name": "Electronics", "high_risk": True, "price_range": (100, 2000)},
        {"name": "Gift Cards", "high_risk": True, "price_range": (50, 500)},
        {"name": "Jewelry", "high_risk": True, "price_range": (200, 5000)},
        {"name": "Clothing", "high_risk": False, "price_range": (20, 200)},
        {"name": "Books", "high_risk": False, "price_range": (10, 50)},
        {"name": "Home & Garden", "high_risk": False, "price_range": (30, 300)},
    ]

    def __init__(self, fraud_rate: float = 0.15):
        self.fraud_rate = fraud_rate

    def _generate_ip(self, suspicious: bool = False) -> str:
        if suspicious:
            # VPN/Proxy-like IPs or high-risk regions
            return f"{random.choice([10, 192, 172])}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}"
        return f"{random.randint(1, 223)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}"

    def _generate_device_id(self) -> str:
        return "".join(random.choices(string.hexdigits.lower(), k=32))

    def _random_timestamp(self, days_back: int = 30) -> str:
        delta = timedelta(
            days=random.randint(0, days_back),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59),
        )
        return (datetime.now() - delta).isoformat()

    def generate_transaction(self, force_fraud: bool = None) -> Transaction:
        """Generate a single transaction record"""
        is_fraud = (
            force_fraud
            if force_fraud is not None
            else random.random() < self.fraud_rate
        )
        merchant, category = random.choice(self.MERCHANTS)

        indicators = []

        if is_fraud:
            # Generate fraudulent transaction patterns
            fraud_pattern = random.choice(
                ["velocity", "amount", "location", "device", "time"]
            )

            if fraud_pattern == "velocity":
                amount = random.uniform(50, 500)
                velocity = random.randint(15, 50)  # Many transactions
                indicators.append("unusual_velocity")
            elif fraud_pattern == "amount":
                amount = random.uniform(2000, 15000)  # Large amount
                velocity = random.randint(1, 5)
                indicators.append("unusual_amount")
            elif fraud_pattern == "location":
                amount = random.uniform(100, 1000)
                velocity = random.randint(3, 10)
                indicators.append("high_risk_location")
            elif fraud_pattern == "device":
                amount = random.uniform(200, 800)
                velocity = random.randint(5, 15)
                indicators.append("new_device")
            else:  # time
                amount = random.uniform(100, 600)
                velocity = random.randint(2, 8)
                indicators.append("unusual_time")

            location = random.choice(self.LOCATIONS[-5:])  # High risk locations
            is_international = random.random() > 0.3
            card_present = random.random() > 0.7  # Usually card-not-present
        else:
            amount = random.uniform(10, 500)
            velocity = random.randint(1, 10)
            location = random.choice(self.LOCATIONS[:10])  # Normal locations
            is_international = random.random() > 0.85
            card_present = random.random() > 0.4

        return Transaction(
            transaction_id=str(uuid.uuid4()),
            user_id=f"USR_{random.randint(10000, 99999)}",
            amount=round(amount, 2),
            currency="USD",
            merchant_name=merchant,
            merchant_category=category,
            location=location,
            ip_address=self._generate_ip(is_fraud),
            device_id=self._generate_device_id(),
            timestamp=self._random_timestamp(),
            card_present=card_present,
            is_international=is_international,
            velocity_24h=velocity,
            avg_amount_30d=round(random.uniform(50, 300), 2),
            is_fraud=is_fraud,
            fraud_type=FraudType.TRANSACTION_FRAUD.value
            if is_fraud
            else FraudType.LEGITIMATE.value,
            fraud_indicators=indicators,
        )

    def generate_insurance_claim(self, force_fraud: bool = None) -> InsuranceClaim:
        """Generate a single insurance claim record"""
        is_fraud = (
            force_fraud
            if force_fraud is not None
            else random.random() < self.fraud_rate
        )
        claim_type = random.choice(self.CLAIM_TYPES)

        indicators = []
        incident_date = datetime.now() - timedelta(days=random.randint(1, 60))

        if is_fraud:
            fraud_pattern = random.choice(["staged", "exaggerated", "timing", "serial"])

            if fraud_pattern == "staged":
                claim_amount = random.uniform(10000, 100000)
                witnesses = 0
                time_to_claim = random.randint(1, 3)  # Quick claim
                previous_claims = random.randint(0, 2)
                indicators.extend(["no_witnesses", "quick_claim"])
            elif fraud_pattern == "exaggerated":
                claim_amount = random.uniform(50000, 200000)  # Very high
                witnesses = random.randint(0, 1)
                time_to_claim = random.randint(5, 15)
                previous_claims = random.randint(1, 3)
                indicators.append("excessive_amount")
            elif fraud_pattern == "timing":
                claim_amount = random.uniform(5000, 30000)
                witnesses = random.randint(0, 2)
                time_to_claim = random.randint(25, 45)  # Near policy end
                previous_claims = random.randint(0, 2)
                policy_age = random.randint(10, 30)  # New policy
                indicators.extend(["new_policy", "late_claim"])
            else:  # serial
                claim_amount = random.uniform(3000, 15000)
                witnesses = random.randint(1, 2)
                time_to_claim = random.randint(5, 20)
                previous_claims = random.randint(4, 10)  # Many previous claims
                indicators.append("serial_claimant")

            policy_age = random.randint(10, 180)
            description = random.choice(
                [
                    "Vehicle was stolen from parking lot at night",
                    "Water damage from burst pipe while on vacation",
                    "Expensive jewelry stolen during home break-in",
                    "Rear-ended at red light, severe whiplash",
                ]
            )
        else:
            claim_amount = random.uniform(500, 15000)
            witnesses = random.randint(1, 4)
            time_to_claim = random.randint(1, 14)
            previous_claims = random.randint(0, 2)
            policy_age = random.randint(180, 1800)
            description = random.choice(
                [
                    "Minor fender bender in grocery store parking lot",
                    "Routine dental procedure coverage",
                    "Wind damage to roof shingles",
                    "Prescription medication reimbursement",
                ]
            )

        claim_date = incident_date + timedelta(days=time_to_claim)

        return InsuranceClaim(
            claim_id=f"CLM_{random.randint(100000, 999999)}",
            policy_id=f"POL_{random.randint(10000, 99999)}",
            claimant_id=f"USR_{random.randint(10000, 99999)}",
            claim_type=claim_type,
            claim_amount=round(claim_amount, 2),
            incident_date=incident_date.isoformat(),
            claim_date=claim_date.isoformat(),
            description=description,
            location=random.choice(self.LOCATIONS[:10]),
            witnesses=witnesses,
            previous_claims_count=previous_claims,
            policy_age_days=policy_age,
            time_to_claim_days=time_to_claim,
            is_fraud=is_fraud,
            fraud_type=FraudType.INSURANCE_FRAUD.value
            if is_fraud
            else FraudType.LEGITIMATE.value,
            fraud_indicators=indicators,
        )

    def generate_user_profile(self, force_fraud: bool = None) -> UserProfile:
        """Generate a user identity profile"""
        is_fraud = (
            force_fraud
            if force_fraud is not None
            else random.random() < self.fraud_rate
        )

        indicators = []

        if is_fraud:
            fraud_pattern = random.choice(["synthetic", "takeover", "new_account"])

            if fraud_pattern == "synthetic":
                # Synthetic identity - fabricated
                email_domain = random.choice(
                    ["tempmail.com", "guerrillamail.com", "10minutemail.com"]
                )
                account_age = random.randint(1, 30)
                device_count = random.randint(5, 15)
                ip_count = random.randint(10, 30)
                login_anomalies = random.randint(5, 15)
                failed_verifications = random.randint(3, 8)
                indicators.extend(
                    ["disposable_email", "multiple_devices", "synthetic_identity"]
                )
            elif fraud_pattern == "takeover":
                # Account takeover
                email_domain = random.choice(["gmail.com", "yahoo.com", "outlook.com"])
                account_age = random.randint(180, 1000)  # Established account
                device_count = random.randint(3, 8)  # New devices
                ip_count = random.randint(8, 20)  # Many IPs
                login_anomalies = random.randint(8, 20)  # Many anomalies
                failed_verifications = random.randint(2, 5)
                indicators.extend(
                    ["login_anomalies", "new_devices", "possible_takeover"]
                )
            else:  # new_account
                email_domain = random.choice(
                    ["protonmail.com", "mail.ru", "yandex.com"]
                )
                account_age = random.randint(0, 7)
                device_count = random.randint(1, 3)
                ip_count = random.randint(3, 8)
                login_anomalies = random.randint(2, 6)
                failed_verifications = random.randint(1, 4)
                indicators.extend(["new_account", "high_risk_email_domain"])
        else:
            email_domain = random.choice(
                ["gmail.com", "yahoo.com", "outlook.com", "icloud.com"]
            )
            account_age = random.randint(90, 2000)
            device_count = random.randint(1, 3)
            ip_count = random.randint(1, 5)
            login_anomalies = random.randint(0, 2)
            failed_verifications = random.randint(0, 1)

        return UserProfile(
            user_id=f"USR_{random.randint(10000, 99999)}",
            email=f"user{random.randint(1000, 9999)}@{email_domain}",
            phone=f"+1{random.randint(2000000000, 9999999999)}",
            ssn_last4=f"{random.randint(1000, 9999)}",
            address=f"{random.randint(100, 9999)} {random.choice(['Main', 'Oak', 'Elm', 'Park'])} St",
            account_age_days=account_age,
            email_domain=email_domain,
            phone_carrier=random.choice(["Verizon", "AT&T", "T-Mobile", "Unknown"]),
            device_count=device_count,
            ip_addresses_used=ip_count,
            login_anomalies=login_anomalies,
            failed_verifications=failed_verifications,
            is_fraud=is_fraud,
            fraud_type=FraudType.IDENTITY_FRAUD.value
            if is_fraud
            else FraudType.LEGITIMATE.value,
            fraud_indicators=indicators,
        )

    def generate_ecommerce_order(self, force_fraud: bool = None) -> EcommerceOrder:
        """Generate an e-commerce order"""
        is_fraud = (
            force_fraud
            if force_fraud is not None
            else random.random() < self.fraud_rate
        )

        indicators = []
        items = []

        if is_fraud:
            fraud_pattern = random.choice(["reseller", "stolen_card", "friendly"])

            if fraud_pattern == "reseller":
                # Reseller fraud - high value items
                num_items = random.randint(3, 8)
                for _ in range(num_items):
                    cat = random.choice(
                        [c for c in self.PRODUCT_CATEGORIES if c["high_risk"]]
                    )
                    items.append(
                        {
                            "category": cat["name"],
                            "price": round(random.uniform(*cat["price_range"]), 2),
                            "quantity": random.randint(2, 5),
                        }
                    )
                express_shipping = True
                shipping_billing_match = False
                is_new_customer = True
                previous_chargebacks = 0
                indicators.extend(
                    ["high_value_items", "bulk_order", "address_mismatch"]
                )
            elif fraud_pattern == "stolen_card":
                num_items = random.randint(1, 4)
                for _ in range(num_items):
                    cat = random.choice(self.PRODUCT_CATEGORIES)
                    items.append(
                        {
                            "category": cat["name"],
                            "price": round(random.uniform(*cat["price_range"]), 2),
                            "quantity": random.randint(1, 3),
                        }
                    )
                express_shipping = random.random() > 0.3
                shipping_billing_match = random.random() > 0.6
                is_new_customer = random.random() > 0.3
                previous_chargebacks = 0
                indicators.extend(["new_customer", "express_shipping"])
            else:  # friendly fraud
                num_items = random.randint(1, 3)
                for _ in range(num_items):
                    cat = random.choice(self.PRODUCT_CATEGORIES)
                    items.append(
                        {
                            "category": cat["name"],
                            "price": round(random.uniform(*cat["price_range"]), 2),
                            "quantity": 1,
                        }
                    )
                express_shipping = False
                shipping_billing_match = True
                is_new_customer = False
                previous_chargebacks = random.randint(2, 5)
                indicators.append("previous_chargebacks")
        else:
            num_items = random.randint(1, 4)
            for _ in range(num_items):
                cat = random.choice(self.PRODUCT_CATEGORIES)
                items.append(
                    {
                        "category": cat["name"],
                        "price": round(random.uniform(*cat["price_range"]), 2),
                        "quantity": random.randint(1, 2),
                    }
                )
            express_shipping = random.random() > 0.8
            shipping_billing_match = random.random() > 0.15
            is_new_customer = random.random() > 0.7
            previous_chargebacks = 0

        total = sum(item["price"] * item["quantity"] for item in items)
        high_risk_items = any(
            item["category"] in ["Electronics", "Gift Cards", "Jewelry"]
            for item in items
        )

        return EcommerceOrder(
            order_id=f"ORD_{random.randint(100000, 999999)}",
            user_id=f"USR_{random.randint(10000, 99999)}",
            items=items,
            total_amount=round(total, 2),
            shipping_address=f"{random.randint(100, 9999)} Shipping St, {random.choice(self.LOCATIONS[:10])}",
            billing_address=f"{random.randint(100, 9999)} Billing Ave, {random.choice(self.LOCATIONS[:10])}",
            payment_method=random.choice(["credit_card", "debit_card", "paypal"]),
            ip_address=self._generate_ip(is_fraud),
            device_fingerprint=self._generate_device_id(),
            timestamp=self._random_timestamp(),
            is_new_customer=is_new_customer,
            shipping_billing_match=shipping_billing_match,
            express_shipping=express_shipping,
            high_risk_items=high_risk_items,
            previous_chargebacks=previous_chargebacks,
            is_fraud=is_fraud,
            fraud_type=FraudType.ECOMMERCE_FRAUD.value
            if is_fraud
            else FraudType.LEGITIMATE.value,
            fraud_indicators=indicators,
        )

    def generate_dataset(
        self,
        n_transactions: int = 100,
        n_claims: int = 50,
        n_profiles: int = 50,
        n_orders: int = 100,
    ) -> Dict[str, List[Dict]]:
        """Generate a complete dataset for all fraud types"""
        return {
            "transactions": [
                asdict(self.generate_transaction()) for _ in range(n_transactions)
            ],
            "insurance_claims": [
                asdict(self.generate_insurance_claim()) for _ in range(n_claims)
            ],
            "user_profiles": [
                asdict(self.generate_user_profile()) for _ in range(n_profiles)
            ],
            "ecommerce_orders": [
                asdict(self.generate_ecommerce_order()) for _ in range(n_orders)
            ],
        }

    def save_dataset(self, filepath: str, **kwargs):
        """Generate and save dataset to JSON file"""
        dataset = self.generate_dataset(**kwargs)
        with open(filepath, "w") as f:
            json.dump(dataset, f, indent=2)
        print(f"Dataset saved to {filepath}")
        return dataset


if __name__ == "__main__":
    generator = SyntheticDataGenerator(fraud_rate=0.2)

    # Generate sample data
    print("Generating synthetic fraud detection dataset...")
    dataset = generator.generate_dataset(
        n_transactions=200, n_claims=100, n_profiles=100, n_orders=200
    )

    # Print statistics
    for data_type, records in dataset.items():
        fraud_count = sum(1 for r in records if r["is_fraud"])
        print(
            f"{data_type}: {len(records)} records, {fraud_count} fraudulent ({fraud_count / len(records) * 100:.1f}%)"
        )

    # Save to file
    generator.save_dataset("sample_dataset.json")
