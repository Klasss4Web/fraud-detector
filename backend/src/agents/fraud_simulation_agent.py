import random
from .simulation_agent import SimulationAgent


class FraudSimulationAgent(SimulationAgent):

    def analyze(self, data):
        """
        Dummy implementation to satisfy BaseAgent abstract method.
        This agent is not intended for real analysis.
        """
        raise NotImplementedError("FraudSimulationAgent does not implement analyze(). Use simulate_attack instead.")


    def __init__(self, api_key: str = None):
        super().__init__(api_key=api_key)


    def simulate_attack(self, attack_type=None, intensity="medium"):
        """
        Use LLM to generate a synthetic fraud attack payload.
        If attack_type is None, default to 'synthetic_identity'.
        """
        scheme = attack_type or "synthetic_identity"
        payload = self.generate_attack(scheme, intensity)
        return {
            "type": scheme,
            "transactions": payload,
            "description": f"LLM-generated {scheme} attack."
        }

    def _simulate_velocity_attack(self):
        # Many transactions in a short time, with diverse locations
        num_tx = random.randint(5, 10)
        locations = [
            "Moscow, Russia", "New York, NY, USA", "Los Angeles, CA, USA", "Chicago, IL, USA", "Houston, TX, USA",
            "London, UK", "Berlin, Germany", "Paris, France", "Tokyo, Japan", "Sydney, Australia",
            "Toronto, Canada", "Cape Town, South Africa", "São Paulo, Brazil", "Mumbai, India", "Beijing, China", "Pyongyang, North Korea", "Lagos, Nigeria", "Dubai, UAE", "Rome, Italy", "Madrid, Spain", "Seoul, South Korea"
        ]
        random.shuffle(locations)
        txs = []
        for i in range(num_tx):
            loc = locations[i % len(locations)]
            txs.append(self._random_transaction(amount=round(random.uniform(10, 100), 2), location=loc, shipping_address=loc, billing_address=loc))
        return {
            "type": "velocity_attack",
            "transactions": txs,
            "description": "Multiple rapid transactions to test velocity checks."
        }

    def _simulate_card_testing(self):
        # Small amounts, many cards, with diverse locations
        num_tx = random.randint(3, 8)
        locations = [
            "Moscow, Russia", "New York, NY, USA", "Los Angeles, CA, USA", "Chicago, IL, USA", "Houston, TX, USA",
            "London, UK", "Berlin, Germany", "Paris, France", "Tokyo, Japan", "Sydney, Australia",
            "Toronto, Canada", "Cape Town, South Africa", "São Paulo, Brazil", "Mumbai, India", "Beijing, China", "Pyongyang, North Korea", "Lagos, Nigeria", "Dubai, UAE", "Rome, Italy", "Madrid, Spain", "Seoul, South Korea"
        ]
        random.shuffle(locations)
        txs = []
        for i in range(num_tx):
            loc = locations[i % len(locations)]
            txs.append(self._random_transaction(amount=1.00, card_number=f"4111{random.randint(100000000000,999999999999)}", location=loc, shipping_address=loc, billing_address=loc))
        return {
            "type": "card_testing",
            "transactions": txs,
            "description": "Testing stolen cards with small amounts."
        }

    def _simulate_address_mismatch(self):
        # Shipping and billing addresses differ
        return {
            "type": "address_mismatch",
            "transactions": [
                self._random_transaction(shipping_address="123 Fake St", billing_address="456 Real Rd")
            ],
            "description": "Order with mismatched addresses."
        }

    def _simulate_high_amount(self):
        # Unusually high amount
        return {
            "type": "high_amount",
            "transactions": [
                self._random_transaction(amount=10000.00)
            ],
            "description": "Single transaction with a very high amount."
        }

    def _simulate_device_spoofing(self):
        # Device ID changes
        return {
            "type": "device_spoofing",
            "transactions": [
                self._random_transaction(device_id=f"device_{random.randint(1000,9999)}")
                for _ in range(2)
            ],
            "description": "Transactions from different devices for the same user."
        }

    def _simulate_synthetic_identity(self):
        # Fake user details
        return {
            "type": "synthetic_identity",
            "transactions": [
                self._random_transaction(customer_id=f"fake_{random.randint(10000,99999)}", amount=round(random.uniform(50, 500), 2))
            ],
            "description": "Transaction with synthetic/fake identity."
        }

    def _random_transaction(self, **overrides):
        locations = [
            "Moscow, Russia", "New York, NY, USA", "Los Angeles, CA, USA", "Chicago, IL, USA", "Houston, TX, USA",
            "London, UK", "Berlin, Germany", "Paris, France", "Tokyo, Japan", "Sydney, Australia",
            "Toronto, Canada", "Cape Town, South Africa", "São Paulo, Brazil", "Mumbai, India", "Beijing, China", "Pyongyang, North Korea", "Lagos, Nigeria", "Dubai, UAE", "Rome, Italy", "Madrid, Spain", "Seoul, South Korea"
        ]
        def random_ip():
            return f"{random.randint(1, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"

        base = {
            "order_id": f"ORD-{random.randint(100000,999999)}",
            "customer_id": f"CUST-{random.randint(1000,9999)}",
            "order_total": round(random.uniform(10, 500), 2),
            "item_count": random.randint(1, 5),
            "shipping_address": random.choice(locations),
            "billing_address": random.choice(locations),
            "payment_method": random.choice(["credit_card", "paypal", "bank_transfer", "gift_card", "crypto", "debit_card"]),
            "device_id": f"device_{random.randint(100,999)}",
            "card_number": f"4111{random.randint(100000000000,999999999999)}",
            "location": random.choice(locations),
            "ip": random_ip(),
        }
        base.update(overrides)
        return base

    def run(self, attack_type=None):
        """
        Main entry point for orchestrator.
        """
        return self.simulate_attack(attack_type)
