import os
import json
from typing import Dict, Any, List, Optional
from .base_agent import BaseAgent
from pydantic import BaseModel, ValidationError


# Define a schema for a transaction that matches TransactionRequest + context fields
class TransactionSchema(BaseModel):
    transaction_id: str
    amount: float
    currency: str = "USD"
    merchant_category: str
    merchant_name: str
    location: str
    device_id: Optional[str] = None
    ip_address: Optional[str] = None
    timestamp: Optional[str] = None
    user_id: Optional[str] = None
    # Context fields for fraud detection
    velocity_24h: Optional[int] = None  # Number of transactions in last 24h
    avg_amount_30d: Optional[float] = None  # User's average transaction amount
    is_international: Optional[bool] = None  # Cross-border transaction flag
    card_present: Optional[bool] = None  # Physical card present
    # Label for mixed simulation
    is_fraudulent: Optional[bool] = None  # Expected label: True = fraud, False = legitimate


class AttackPayload(BaseModel):
    transactions: List[TransactionSchema]


class MixedPayload(BaseModel):
    """Payload containing both legitimate and fraudulent transactions"""

    fraudulent_transactions: List[TransactionSchema]
    legitimate_transactions: List[TransactionSchema]


class SimulationAgent(BaseAgent):
    # ...existing code...
    def __init__(self, api_key: str = None):
        super().__init__("SimulationAgent")
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.client = None
        self.base_url = "https://openrouter.ai/api/v1"
        print(f"SimulationAgent initialized with API key: {'Yes' if self.api_key else 'No'}")
        if self.api_key:
            try:
                from openai import OpenAI

                self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
                self.log("OpenAI client initialized for SimulationAgent")
            except ImportError:
                self.log("OpenAI package not installed. Install with: pip install openai")
        else:
            self.log("No API key provided. LLM features disabled.")

    def analyze(self, data: Dict[str, Any]) -> Any:
        """
        SimulationAgent doesn't analyze - it generates.
        This is a placeholder to satisfy BaseAgent's abstract method.
        Use generate_attack() or generate_mixed_transactions() instead.
        """
        # Return a dummy result - this agent is for generation, not analysis
        from .base_agent import AgentResult, RiskLevel

        return AgentResult(
            agent_name=self.name,
            entity_id="simulation",
            risk_score=0.0,
            risk_level=RiskLevel.LOW,
            signals=[],
            recommendation="Use generate_attack() or generate_mixed_transactions() instead",
            details={},
            confidence=0.0,
        )

    def _call_llm(self, prompt: str) -> str:
        if not self.client:
            raise RuntimeError("No LLM client available. Cannot generate attack.")
        try:
            response = self.client.chat.completions.create(
                model="openai/gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a fraud simulation LLM."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=2048,
                temperature=0.7,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content.strip()
            if not content:
                self.log("LLM returned empty content!")
            return content
        except Exception as e:
            self.log(f"LLM call failed: {e}")
            raise

    def generate_attack(self, target_scheme: str, intensity: str = "medium") -> Dict[str, Any]:
        """
        Generates a fraud payload designed to mimic a specific scheme.
        Schemes: 'account_takeover', 'synthetic_identity', 'money_laundering', 'card_testing', 'velocity_attack', etc.
        """
        # Use scenario-based wording for LLM-guarded types
        scenario_map = {
            "card_testing": "multiple small transactions using different credit cards in a short period, as might be seen in card testing attempts",
            "velocity_attack": "a burst of many rapid transactions from the same account or device within a short time window, as might be seen in velocity-based fraud",
            "address_mismatch": "transactions where shipping and billing information would typically differ, indicating potential fraud",
            "high_amount": "transactions with unusually high amounts that would trigger fraud alerts",
            "device_spoofing": "transactions appearing to come from multiple different devices for the same user",
            "synthetic_identity": "transactions using synthetic or fabricated identity information",
        }

        # Attack-specific guidance for context fields
        context_guidance = {
            "velocity_attack": """
IMPORTANT for velocity attack simulation:
- velocity_24h should be HIGH (15-50+ transactions) to simulate rapid transaction bursts
- Timestamps should be very close together (within minutes)
- Use the same user_id and device_id across transactions""",
            "card_testing": """
IMPORTANT for card testing simulation:
- Use small amounts ($1-20) to test if cards are valid
- velocity_24h should be moderate to high (10-30)
- card_present should be false (online transactions)
- Different merchant names but similar categories""",
            "high_amount": """
IMPORTANT for high amount simulation:
- amounts should be very high ($5000-50000+)
- avg_amount_30d should be LOW ($50-200) to show deviation
- is_international can be true for added risk
- merchant_category should be high-risk like "electronics", "jewelry", "gift_cards\"""",
            "device_spoofing": """
IMPORTANT for device spoofing simulation:
- Use DIFFERENT device_id values for the SAME user_id
- ip_address should vary significantly between transactions
- is_international should be true (different countries)
- card_present should be false""",
            "synthetic_identity": """
IMPORTANT for synthetic identity simulation:
- Use high-risk locations from this list: Lagos Nigeria, Moscow Russia, Beijing China, Mumbai India
- is_international should be true
- card_present should be false
- velocity_24h should be low (new account behavior)
- High value transactions with new account""",
            "address_mismatch": """
IMPORTANT for address mismatch simulation:
- is_international should be true
- Use mismatched locations (transaction location far from user's typical location)
- card_present should be false
- merchant_category should be "electronics" or "jewelry" (commonly shipped items)""",
        }

        example_json = """
Example:
{
    "transactions": [
        {
            "transaction_id": "txn_001",
            "amount": 5500.00,
            "currency": "USD",
            "merchant_category": "electronics",
            "merchant_name": "TechStore Pro",
            "location": "Lagos, Nigeria",
            "device_id": "device_abc123",
            "ip_address": "82.165.123.45",
            "timestamp": "2024-01-15T03:32:00Z",
            "user_id": "user_12345",
            "velocity_24h": 25,
            "avg_amount_30d": 150.00,
            "is_international": true,
            "card_present": false
        },
        {
            "transaction_id": "txn_002",
            "amount": 3200.75,
            "currency": "USD",
            "merchant_category": "jewelry",
            "merchant_name": "Luxury Gems",
            "location": "Moscow, Russia",
            "device_id": "device_xyz789",
            "ip_address": "1.234.56.78",
            "timestamp": "2024-01-15T03:35:00Z",
            "user_id": "user_12345",
            "velocity_24h": 26,
            "avg_amount_30d": 150.00,
            "is_international": true,
            "card_present": false
        }
    ]
}
"""

        required_fields = """
Each transaction object MUST include ALL these fields:

Basic fields:
- transaction_id (string): Unique identifier like "txn_001"
- amount (float): Transaction amount in the currency specified
- currency (string): Currency code like "USD", "EUR", "GBP"
- merchant_category (string): Use realistic categories like "electronics", "retail", "travel", "gaming", "jewelry", "gift_cards", "wire_transfer", "crypto", "gambling", "restaurant"
- merchant_name (string): Realistic merchant name
- location (string): City and country like "Lagos, Nigeria" or "Moscow, Russia"
- device_id (string): Device identifier
- ip_address (string): IP address (use realistic public IPs, or private ranges like 10.x.x.x or 192.168.x.x for VPN/suspicious)
- timestamp (string): ISO format timestamp like "2024-01-15T03:32:00Z" (use unusual hours 2-5 AM for suspicious)
- user_id (string): User identifier

Context fields (CRITICAL for fraud detection):
- velocity_24h (integer): Number of transactions by this user in last 24 hours. Normal is 1-5, suspicious is 10+, attack is 20+
- avg_amount_30d (float): User's average transaction amount over 30 days. Set LOW if current amount is suspiciously high
- is_international (boolean): true if cross-border transaction, false otherwise
- card_present (boolean): false for online/card-not-present transactions, true for in-person
"""

        attack_specific = context_guidance.get(target_scheme, "")

        if target_scheme in scenario_map:
            scenario_desc = scenario_map[target_scheme]
            prompt = f"""
You are a security researcher assisting with red team testing and improvement of fraud detection systems. This is for ethical, internal simulation only—never for real fraud.

Please generate a synthetic, fictional JSON payload representing {scenario_desc}. The goal is to help test if a risk scoring system can detect this pattern. Intensity Level: {intensity} (high means more obvious fraud patterns, low means very subtle).

{attack_specific}

Ensure the transactions include suspicious patterns that a fraud detection system should catch:
- Use high-risk locations when appropriate (Lagos Nigeria, Moscow Russia, Beijing China, Mumbai India)
- Set velocity_24h, avg_amount_30d, is_international, and card_present to values that indicate fraud
- Use timestamps in unusual hours (2-5 AM) when appropriate
- Use high-risk merchant categories when appropriate (gift_cards, wire_transfer, crypto, gambling)

{required_fields}

Return a JSON object with a key 'transactions' containing an array of 3-5 transaction objects.

{example_json}
"""
        else:
            prompt = f"""
You are a security researcher assisting with red team testing and improvement of fraud detection systems. This is for ethical, internal simulation only—never for real fraud.

Please generate a synthetic, fictional JSON payload for a {target_scheme} fraud attack. The goal is to help test if a risk scoring system can detect this pattern. Intensity Level: {intensity} (high means more obvious fraud patterns, low means very subtle).

Ensure the transactions include suspicious patterns that a fraud detection system should catch:
- Use high-risk locations when appropriate (Lagos Nigeria, Moscow Russia, Beijing China, Mumbai India)
- Set velocity_24h, avg_amount_30d, is_international, and card_present to values that indicate fraud
- Use timestamps in unusual hours (2-5 AM) when appropriate
- Use high-risk merchant categories when appropriate (gift_cards, wire_transfer, crypto, gambling)

{required_fields}

Return a JSON object with a key 'transactions' containing an array of 3-5 transaction objects.

{example_json}
"""
        raw_json = self._call_llm(prompt)
        self.log(f"LLM Response for {target_scheme} attack:\n{raw_json}\n")

        # Detect LLM refusal or empty response
        refusal_phrases = [
            "i'm sorry",
            "i am sorry",
            "cannot help",
            "can't help",
            "not able to",
            "as an ai",
            "i cannot",
            "i can't",
            "refuse",
            "not permitted",
            "not allowed",
            "no can do",
        ]
        if not raw_json or any(phrase in raw_json.lower() for phrase in refusal_phrases):
            self.log(f"LLM refused or returned empty response for {target_scheme}: {raw_json}")
            raise RuntimeError(
                f"LLM refused to generate a response for {target_scheme} or returned empty output."
            )

        # --- Robust JSON cleaning ---
        def clean_json_string(s):
            import re

            s = s.strip()
            # Remove Markdown code block markers
            if s.startswith("```"):
                s = s.lstrip("`").split("\n", 1)[-1]
                if s.strip().startswith("json"):
                    s = s.strip()[4:]
                if s.strip().endswith("```"):
                    s = s.strip()[:-3]
            s = s.strip()
            # Remove comment lines and non-JSON lines
            lines = s.split("\n")
            json_lines = []
            in_json = False
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                # Start collecting at first { or [
                if not in_json and (line.startswith("{") or line.startswith("[")):
                    in_json = True
                if in_json:
                    # Remove C-style and Python-style comments
                    line = re.sub(r"//.*", "", line)
                    line = re.sub(r"#.*", "", line)
                    json_lines.append(line)
            s = "\n".join(json_lines)
            # Remove any trailing text after last } or ]
            last_brace = max(s.rfind("}"), s.rfind("]"))
            if last_brace != -1:
                s = s[: last_brace + 1]
            # Final Guard: Auto-close truncated arrays or objects
            open_brackets = s.count("[") - s.count("]")
            open_braces = s.count("{") - s.count("}")
            if open_braces > 0:
                s += "}" * open_braces
            if open_brackets > 0:
                s += "]" * open_brackets
            # Replace single quotes with double quotes
            s = s.replace("'", '"')
            # Remove trailing commas before } or ]
            s = re.sub(r",\s*([}\]])", r"\1", s)
            # Remove any trailing commas in arrays/objects
            s = re.sub(r",\s*([}\]])", r"\1", s)
            # Remove any double commas
            s = re.sub(r",\s*,", ",", s)
            return s

        cleaned_json = clean_json_string(raw_json)
        try:
            data = json.loads(cleaned_json)
            # Always normalize to a dict with 'transactions' key
            if isinstance(data, dict) and "transactions" in data:
                transactions_list = data["transactions"]
            elif isinstance(data, list):
                transactions_list = data
            else:
                self.log(f"Unexpected LLM response type: {type(data)}. Raw: {cleaned_json}")
                raise ValueError("LLM response is not a dict with 'transactions' or a list")
            # Validate using AttackPayload schema
            try:
                payload = AttackPayload(transactions=transactions_list)
            except ValidationError as ve:
                self.log(f"AttackPayload validation error: {ve}\nRaw: {transactions_list}")
                raise ValueError(f"Invalid attack payload format: {ve}")
            return [t.dict() for t in payload.transactions]
        except Exception as e:
            self.log(f"Failed to decode LLM response as JSON: {e}\nRaw response: {cleaned_json}")
            raise

    def generate_mixed_transactions(
        self, attack_type: str = None, num_legitimate: int = 3, num_fraudulent: int = 3
    ) -> Dict[str, Any]:
        """
        Generate a mix of legitimate and fraudulent transactions for realistic testing.

        Args:
            attack_type: Type of fraud attack for fraudulent transactions (optional, random if None)
            num_legitimate: Number of legitimate transactions to generate
            num_fraudulent: Number of fraudulent transactions to generate

        Returns:
            Dictionary with 'transactions' list, each labeled with 'is_fraudulent' boolean
        """
        prompt = f"""
You are a security researcher helping to test fraud detection systems. Generate a realistic mix of BOTH legitimate AND fraudulent transactions.

Generate exactly {num_legitimate} LEGITIMATE transactions and {num_fraudulent} FRAUDULENT transactions.

LEGITIMATE transactions should have these characteristics:
- Normal transaction amounts ($20-500) consistent with user's average
- Common locations in the USA (New York, Los Angeles, Chicago, etc.)
- Normal business hours (9 AM - 9 PM)
- Low velocity (1-3 transactions in 24h)
- Card present = true (in-person) OR card present = false with matching patterns
- Normal merchant categories (grocery, restaurant, retail, gas_station)
- avg_amount_30d should be SIMILAR to current amount
- is_international = false
- velocity_24h between 1-5

FRAUDULENT transactions should have these characteristics:
- High amounts ($2000+) OR very small test amounts ($1-5)
- High-risk locations (Lagos Nigeria, Moscow Russia, Beijing China, Mumbai India)
- Unusual hours (2-5 AM)
- High velocity (15+ transactions in 24h)
- card_present = false
- High-risk categories (electronics, jewelry, gift_cards, crypto, wire_transfer)
- avg_amount_30d much LOWER than current amount (showing deviation)
- is_international = true
- velocity_24h above 10

{"Attack type focus for fraudulent transactions: " + attack_type if attack_type else "Use a variety of fraud patterns"}

Each transaction MUST include these fields:
- transaction_id (string): Use "legit_001", "legit_002" for legitimate, "fraud_001", "fraud_002" for fraudulent
- amount (float)
- currency (string): "USD"
- merchant_category (string)
- merchant_name (string)
- location (string): "City, Country"
- device_id (string)
- ip_address (string)
- timestamp (string): ISO format
- user_id (string)
- velocity_24h (integer)
- avg_amount_30d (float)
- is_international (boolean)
- card_present (boolean)
- is_fraudulent (boolean): CRITICAL - set to false for legitimate, true for fraudulent

Return JSON with this EXACT structure:
{{
    "fraudulent_transactions": [
        {{ ... transaction with is_fraudulent: true ... }}
    ],
    "legitimate_transactions": [
        {{ ... transaction with is_fraudulent: false ... }}
    ]
}}

Example legitimate transaction:
{{
    "transaction_id": "legit_001",
    "amount": 45.99,
    "currency": "USD",
    "merchant_category": "grocery",
    "merchant_name": "Whole Foods Market",
    "location": "San Francisco, USA",
    "device_id": "device_user123",
    "ip_address": "73.162.45.89",
    "timestamp": "2024-01-15T14:30:00Z",
    "user_id": "user_regular_001",
    "velocity_24h": 2,
    "avg_amount_30d": 52.00,
    "is_international": false,
    "card_present": true,
    "is_fraudulent": false
}}

Example fraudulent transaction:
{{
    "transaction_id": "fraud_001",
    "amount": 4999.99,
    "currency": "USD",
    "merchant_category": "electronics",
    "merchant_name": "TechWorld Online",
    "location": "Lagos, Nigeria",
    "device_id": "device_suspicious_789",
    "ip_address": "41.190.3.156",
    "timestamp": "2024-01-15T03:15:00Z",
    "user_id": "user_compromised_001",
    "velocity_24h": 23,
    "avg_amount_30d": 75.00,
    "is_international": true,
    "card_present": false,
    "is_fraudulent": true
}}
"""

        raw_json = self._call_llm(prompt)
        self.log(f"LLM Response for mixed transactions:\n{raw_json}\n")

        # Detect LLM refusal
        refusal_phrases = [
            "i'm sorry",
            "i am sorry",
            "cannot help",
            "can't help",
            "not able to",
            "as an ai",
            "i cannot",
            "i can't",
            "refuse",
        ]
        if not raw_json or any(phrase in raw_json.lower() for phrase in refusal_phrases):
            raise RuntimeError("LLM refused to generate mixed transactions")

        # Clean and parse JSON
        cleaned_json = self._clean_json_string(raw_json)

        try:
            data = json.loads(cleaned_json)

            fraudulent = data.get("fraudulent_transactions", [])
            legitimate = data.get("legitimate_transactions", [])

            # Ensure is_fraudulent labels are set correctly
            for tx in fraudulent:
                tx["is_fraudulent"] = True
            for tx in legitimate:
                tx["is_fraudulent"] = False

            # Combine and shuffle for realistic testing
            import random

            all_transactions = fraudulent + legitimate
            random.shuffle(all_transactions)

            return {
                "transactions": all_transactions,
                "fraudulent_count": len(fraudulent),
                "legitimate_count": len(legitimate),
                "total_count": len(all_transactions),
            }

        except Exception as e:
            self.log(f"Failed to parse mixed transactions: {e}\nRaw: {cleaned_json}")
            raise

    def _clean_json_string(self, s: str) -> str:
        """Clean and normalize JSON string from LLM response"""
        import re

        s = s.strip()
        # Remove Markdown code block markers
        if s.startswith("```"):
            s = s.lstrip("`").split("\n", 1)[-1]
            if s.strip().startswith("json"):
                s = s.strip()[4:]
            if s.strip().endswith("```"):
                s = s.strip()[:-3]
        s = s.strip()

        # Remove comment lines and non-JSON lines
        lines = s.split("\n")
        json_lines = []
        in_json = False
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if not in_json and (line.startswith("{") or line.startswith("[")):
                in_json = True
            if in_json:
                line = re.sub(r"//.*", "", line)
                line = re.sub(r"#.*", "", line)
                json_lines.append(line)
        s = "\n".join(json_lines)

        # Remove trailing text after last } or ]
        last_brace = max(s.rfind("}"), s.rfind("]"))
        if last_brace != -1:
            s = s[: last_brace + 1]

        # Auto-close truncated arrays/objects
        open_brackets = s.count("[") - s.count("]")
        open_braces = s.count("{") - s.count("}")
        if open_braces > 0:
            s += "}" * open_braces
        if open_brackets > 0:
            s += "]" * open_brackets

        # Fix common JSON issues
        s = s.replace("'", '"')
        s = re.sub(r",\s*([}\]])", r"\1", s)
        s = re.sub(r",\s*,", ",", s)

        return s

    def generate_deterministic_mixed_transactions(
        self, num_legitimate: int = 5, num_fraudulent: int = 5
    ) -> Dict[str, Any]:
        """
        Generate a deterministic mix of legitimate and fraudulent transactions.

        This is a fallback method that doesn't require LLM calls and provides
        consistent, well-labeled test data for evaluation.

        Args:
            num_legitimate: Number of legitimate transactions to generate
            num_fraudulent: Number of fraudulent transactions to generate

        Returns:
            Dictionary with 'transactions' list, each labeled with 'is_fraudulent' boolean
        """
        import random
        from datetime import datetime, timedelta

        transactions = []
        base_time = datetime.now()

        # === LEGITIMATE TRANSACTION TEMPLATES ===
        legitimate_patterns = [
            {
                "merchant_category": "grocery",
                "merchant_name": "Whole Foods Market",
                "amount_range": (25, 150),
                "location": "San Francisco, USA",
                "velocity_range": (1, 3),
                "hour_range": (9, 20),  # Normal business hours
                "card_present": True,
                "is_international": False,
            },
            {
                "merchant_category": "restaurant",
                "merchant_name": "Olive Garden",
                "amount_range": (15, 80),
                "location": "Los Angeles, USA",
                "velocity_range": (1, 4),
                "hour_range": (11, 22),
                "card_present": True,
                "is_international": False,
            },
            {
                "merchant_category": "gas_station",
                "merchant_name": "Shell Gas Station",
                "amount_range": (30, 70),
                "location": "Chicago, USA",
                "velocity_range": (1, 2),
                "hour_range": (7, 21),
                "card_present": True,
                "is_international": False,
            },
            {
                "merchant_category": "retail",
                "merchant_name": "Target",
                "amount_range": (20, 200),
                "location": "New York, USA",
                "velocity_range": (1, 3),
                "hour_range": (10, 21),
                "card_present": True,
                "is_international": False,
            },
            {
                "merchant_category": "online_retail",
                "merchant_name": "Amazon.com",
                "amount_range": (15, 150),
                "location": "Seattle, USA",
                "velocity_range": (1, 4),
                "hour_range": (8, 23),
                "card_present": False,
                "is_international": False,
            },
            {
                "merchant_category": "subscription",
                "merchant_name": "Netflix",
                "amount_range": (9.99, 22.99),
                "location": "Los Gatos, USA",
                "velocity_range": (1, 1),
                "hour_range": (0, 23),
                "card_present": False,
                "is_international": False,
            },
            {
                "merchant_category": "pharmacy",
                "merchant_name": "CVS Pharmacy",
                "amount_range": (10, 80),
                "location": "Boston, USA",
                "velocity_range": (1, 2),
                "hour_range": (8, 22),
                "card_present": True,
                "is_international": False,
            },
        ]

        # === FRAUDULENT TRANSACTION TEMPLATES ===
        fraudulent_patterns = [
            # High-amount fraud
            {
                "merchant_category": "electronics",
                "merchant_name": "TechWorld Online",
                "amount_range": (3000, 8000),
                "location": "Lagos, Nigeria",
                "velocity_range": (15, 30),
                "hour_range": (2, 5),  # Unusual hours
                "card_present": False,
                "is_international": True,
                "fraud_type": "high_amount",
            },
            # Velocity attack
            {
                "merchant_category": "gift_cards",
                "merchant_name": "Gift Card Express",
                "amount_range": (200, 500),
                "location": "Moscow, Russia",
                "velocity_range": (20, 40),
                "hour_range": (1, 4),
                "card_present": False,
                "is_international": True,
                "fraud_type": "velocity_attack",
            },
            # Card testing
            {
                "merchant_category": "gaming",
                "merchant_name": "Steam Games",
                "amount_range": (0.99, 5.00),
                "location": "Beijing, China",
                "velocity_range": (25, 50),
                "hour_range": (3, 6),
                "card_present": False,
                "is_international": True,
                "fraud_type": "card_testing",
            },
            # Jewelry/luxury fraud
            {
                "merchant_category": "jewelry",
                "merchant_name": "Luxury Gems International",
                "amount_range": (5000, 15000),
                "location": "Mumbai, India",
                "velocity_range": (10, 20),
                "hour_range": (2, 4),
                "card_present": False,
                "is_international": True,
                "fraud_type": "high_amount",
            },
            # Wire transfer fraud
            {
                "merchant_category": "wire_transfer",
                "merchant_name": "QuickTransfer Global",
                "amount_range": (2000, 10000),
                "location": "Lagos, Nigeria",
                "velocity_range": (8, 15),
                "hour_range": (0, 5),
                "card_present": False,
                "is_international": True,
                "fraud_type": "synthetic_identity",
            },
            # Crypto purchase fraud
            {
                "merchant_category": "crypto",
                "merchant_name": "CryptoExchange Pro",
                "amount_range": (1000, 5000),
                "location": "Moscow, Russia",
                "velocity_range": (12, 25),
                "hour_range": (1, 5),
                "card_present": False,
                "is_international": True,
                "fraud_type": "device_spoofing",
            },
        ]

        # Generate legitimate transactions
        for i in range(num_legitimate):
            pattern = random.choice(legitimate_patterns)
            amount = round(random.uniform(*pattern["amount_range"]), 2)
            velocity = random.randint(*pattern["velocity_range"])
            hour = random.randint(*pattern["hour_range"])

            # For legitimate transactions, avg_amount should be close to current amount
            avg_amount = round(amount * random.uniform(0.8, 1.2), 2)

            tx_time = base_time - timedelta(hours=random.randint(0, 48))
            tx_time = tx_time.replace(hour=hour, minute=random.randint(0, 59))

            tx = {
                "transaction_id": f"legit_{i + 1:03d}",
                "amount": amount,
                "currency": "USD",
                "merchant_category": pattern["merchant_category"],
                "merchant_name": pattern["merchant_name"],
                "location": pattern["location"],
                "device_id": f"device_user_{random.randint(100, 999)}",
                "ip_address": f"73.{random.randint(1, 254)}.{random.randint(1, 254)}.{random.randint(1, 254)}",
                "timestamp": tx_time.isoformat() + "Z",
                "user_id": f"user_regular_{random.randint(1, 100):03d}",
                "velocity_24h": velocity,
                "avg_amount_30d": avg_amount,
                "is_international": pattern["is_international"],
                "card_present": pattern["card_present"],
                "is_fraudulent": False,  # LABEL: Legitimate
            }
            transactions.append(tx)

        # Generate fraudulent transactions
        for i in range(num_fraudulent):
            pattern = random.choice(fraudulent_patterns)
            amount = round(random.uniform(*pattern["amount_range"]), 2)
            velocity = random.randint(*pattern["velocity_range"])
            hour = random.randint(*pattern["hour_range"])

            # For fraud, avg_amount should be much lower than current amount (deviation)
            avg_amount = round(random.uniform(50, 150), 2)

            tx_time = base_time - timedelta(hours=random.randint(0, 24))
            tx_time = tx_time.replace(hour=hour, minute=random.randint(0, 59))

            # Use suspicious IP ranges (private IPs that might indicate VPN/proxy)
            ip_choices = [
                f"10.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}",
                f"192.168.{random.randint(0, 255)}.{random.randint(1, 254)}",
                f"41.{random.randint(1, 254)}.{random.randint(1, 254)}.{random.randint(1, 254)}",  # African IPs
                f"91.{random.randint(1, 254)}.{random.randint(1, 254)}.{random.randint(1, 254)}",  # Eastern European IPs
            ]

            tx = {
                "transaction_id": f"fraud_{i + 1:03d}",
                "amount": amount,
                "currency": "USD",
                "merchant_category": pattern["merchant_category"],
                "merchant_name": pattern["merchant_name"],
                "location": pattern["location"],
                "device_id": f"device_suspicious_{random.randint(1000, 9999)}",
                "ip_address": random.choice(ip_choices),
                "timestamp": tx_time.isoformat() + "Z",
                "user_id": f"user_compromised_{random.randint(1, 50):03d}",
                "velocity_24h": velocity,
                "avg_amount_30d": avg_amount,
                "is_international": pattern["is_international"],
                "card_present": pattern["card_present"],
                "is_fraudulent": True,  # LABEL: Fraudulent
                "fraud_type": pattern.get("fraud_type", "unknown"),
            }
            transactions.append(tx)

        # Shuffle for realistic testing
        random.shuffle(transactions)

        return {
            "transactions": transactions,
            "fraudulent_count": num_fraudulent,
            "legitimate_count": num_legitimate,
            "total_count": len(transactions),
        }
