# Sample Test Data for Fraud Detection System

## 1. Transaction Analysis

### Low Risk Transaction

```json
{
  "transaction_id": "TXN-2024-001234",
  "user_id": "USR-78945",
  "amount": 125.5,
  "currency": "USD",
  "merchant_category": "grocery",
  "merchant_name": "Whole Foods Market",
  "location": "San Francisco, US",
  "device_id": "dev-a1b2c3d4e5f6",
  "ip_address": "73.158.64.22"
}
```

### Medium Risk Transaction

```json
{
  "transaction_id": "TXN-2024-005678",
  "user_id": "USR-12345",
  "amount": 2500.0,
  "currency": "USD",
  "merchant_category": "electronics",
  "merchant_name": "TechZone Online",
  "location": "Miami, US",
  "device_id": "dev-x9y8z7w6v5u4",
  "ip_address": "45.33.32.156"
}
```

### High Risk Transaction (Suspicious)

```json
{
  "transaction_id": "TXN-2024-009999",
  "user_id": "USR-00001",
  "amount": 9850.0,
  "currency": "USD",
  "merchant_category": "cryptocurrency",
  "merchant_name": "CryptoExchange Pro",
  "location": "Lagos, Nigeria",
  "device_id": "dev-0000000000",
  "ip_address": "192.168.1.100"
}
```

### Critical Risk Transaction (Likely Fraud)

```json
{
  "transaction_id": "TXN-2024-FRAUD01",
  "user_id": "USR-NEWUSER",
  "amount": 14999.99,
  "currency": "USD",
  "merchant_category": "money_transfer",
  "merchant_name": "Quick Wire Transfer",
  "location": "Moscow, Russia",
  "device_id": "dev-emulator-001",
  "ip_address": "10.0.0.1"
}
```

---

## 2. Insurance Claim Analysis

### Low Risk Claim

```json
{
  "claim_id": "CLM-2024-001234",
  "claimant_id": "CLMT-56789",
  "claim_type": "auto",
  "claim_amount": 1200.0,
  "incident_date": "2024-01-10",
  "filing_date": "2024-01-15",
  "description": "Minor parking lot accident. Another driver backed into my rear bumper while I was parked. Police report filed. Witness present.",
  "policy_id": "POL-AUTO-789456"
}
```

### Medium Risk Claim

```json
{
  "claim_id": "CLM-2024-005678",
  "claimant_id": "CLMT-11111",
  "claim_type": "property",
  "claim_amount": 15000.0,
  "incident_date": "2024-02-01",
  "filing_date": "2024-02-03",
  "description": "Water damage to basement from burst pipe during cold weather. Furniture and electronics damaged.",
  "policy_id": "POL-HOME-123456"
}
```

### High Risk Claim (Suspicious)

```json
{
  "claim_id": "CLM-2024-SUS001",
  "claimant_id": "CLMT-99999",
  "claim_type": "auto",
  "claim_amount": 75000.0,
  "incident_date": "2024-03-01",
  "filing_date": "2024-03-01",
  "description": "Total loss vehicle. Severe whiplash injury. Need immediate cash settlement. Vehicle was brand new.",
  "policy_id": "POL-AUTO-000001"
}
```

### Critical Risk Claim (Likely Fraud)

```json
{
  "claim_id": "CLM-2024-FRAUD01",
  "claimant_id": "CLMT-SERIAL",
  "claim_type": "health",
  "claim_amount": 125000.0,
  "incident_date": "2024-03-10",
  "filing_date": "2024-03-10",
  "description": "Emergency surgery required. Total loss. Severe injuries. Cash settlement needed immediately. No witnesses. Happened at night in remote area.",
  "policy_id": "POL-HEALTH-NEW01"
}
```

---

## 3. Identity/User Profile Analysis

### Low Risk Profile

```json
{
  "user_id": "USR-TRUSTED-001",
  "email": "john.smith@gmail.com",
  "phone": "+1-415-555-1234",
  "account_age_days": 730,
  "device_count": 2,
  "login_frequency": 3.5,
  "failed_login_attempts": 0,
  "location_changes": 1
}
```

### Medium Risk Profile

```json
{
  "user_id": "USR-MED-001",
  "email": "newuser2024@yahoo.com",
  "phone": "+1-212-555-9876",
  "account_age_days": 45,
  "device_count": 4,
  "login_frequency": 8.0,
  "failed_login_attempts": 2,
  "location_changes": 3
}
```

### High Risk Profile (Suspicious)

```json
{
  "user_id": "USR-SUS-001",
  "email": "random123abc@tempmail.org",
  "phone": "+1-000-555-0000",
  "account_age_days": 3,
  "device_count": 8,
  "login_frequency": 25.0,
  "failed_login_attempts": 7,
  "location_changes": 12
}
```

### Critical Risk Profile (Likely Fraud)

```json
{
  "user_id": "USR-FRAUD-001",
  "email": "throwaway999@fakeinbox.com",
  "phone": "+1-999-999-9999",
  "account_age_days": 1,
  "device_count": 20,
  "login_frequency": 100.0,
  "failed_login_attempts": 15,
  "location_changes": 30
}
```

---

## 4. E-Commerce Order Analysis

### Low Risk Order

```json
{
  "order_id": "ORD-2024-001234",
  "customer_id": "CUST-LOYAL-001",
  "order_total": 89.99,
  "item_count": 3,
  "shipping_address": "123 Main Street, Apt 4B, New York, NY 10001",
  "billing_address": "123 Main Street, Apt 4B, New York, NY 10001",
  "payment_method": "credit_card",
  "is_expedited": "false"
}
```

### Medium Risk Order

```json
{
  "order_id": "ORD-2024-005678",
  "customer_id": "CUST-NEW-001",
  "order_total": 650.0,
  "item_count": 2,
  "shipping_address": "456 Oak Avenue, Los Angeles, CA 90001",
  "billing_address": "789 Pine Street, San Diego, CA 92101",
  "payment_method": "debit_card",
  "is_expedited": "false"
}
```

### High Risk Order (Suspicious)

```json
{
  "order_id": "ORD-2024-SUS001",
  "customer_id": "CUST-FIRSTTIME",
  "order_total": 3500.0,
  "item_count": 5,
  "shipping_address": "999 Warehouse Blvd, Suite 100, Miami, FL 33101",
  "billing_address": "111 Different Road, Chicago, IL 60601",
  "payment_method": "prepaid_card",
  "is_expedited": "true"
}
```

### Critical Risk Order (Likely Fraud)

```json
{
  "order_id": "ORD-2024-FRAUD01",
  "customer_id": "CUST-UNKNOWN",
  "order_total": 8999.99,
  "item_count": 10,
  "shipping_address": "PO Box 12345, Freight Forwarder Inc, Newark, NJ 07101",
  "billing_address": "Anonymous Address, Unknown City, XX 00000",
  "payment_method": "cryptocurrency",
  "is_expedited": "true"
}
```

---

## Quick Copy-Paste for Frontend Forms

### Transaction Form (High Risk Example)

| Field             | Value              |
| ----------------- | ------------------ |
| Transaction ID    | TXN-2024-009999    |
| User ID           | USR-00001          |
| Amount            | 9850.00            |
| Currency          | USD                |
| Merchant Category | cryptocurrency     |
| Merchant Name     | CryptoExchange Pro |
| Location          | Lagos, Nigeria     |
| Device ID         | dev-0000000000     |
| IP Address        | 192.168.1.100      |

### Insurance Claim Form (High Risk Example)

| Field         | Value                                                                                              |
| ------------- | -------------------------------------------------------------------------------------------------- |
| Claim ID      | CLM-2024-SUS001                                                                                    |
| Claimant ID   | CLMT-99999                                                                                         |
| Claim Type    | auto                                                                                               |
| Claim Amount  | 75000.00                                                                                           |
| Incident Date | 2024-03-01                                                                                         |
| Filing Date   | 2024-03-01                                                                                         |
| Policy ID     | POL-AUTO-000001                                                                                    |
| Description   | Total loss vehicle. Severe whiplash injury. Need immediate cash settlement. Vehicle was brand new. |

### User Profile Form (High Risk Example)

| Field                 | Value                     |
| --------------------- | ------------------------- |
| User ID               | USR-SUS-001               |
| Email                 | random123abc@tempmail.org |
| Phone                 | +1-000-555-0000           |
| Account Age (days)    | 3                         |
| Device Count          | 8                         |
| Login Frequency       | 25.0                      |
| Failed Login Attempts | 7                         |
| Location Changes      | 12                        |

### E-Commerce Order Form (High Risk Example)

| Field            | Value                                          |
| ---------------- | ---------------------------------------------- |
| Order ID         | ORD-2024-SUS001                                |
| Customer ID      | CUST-FIRSTTIME                                 |
| Order Total      | 3500.00                                        |
| Item Count       | 5                                              |
| Shipping Address | 999 Warehouse Blvd, Suite 100, Miami, FL 33101 |
| Billing Address  | 111 Different Road, Chicago, IL 60601          |
| Payment Method   | prepaid_card                                   |
| Shipping Type    | Expedited Shipping                             |

---

## API Testing with cURL

### Test Transaction Analysis

```bash
curl -X POST "http://localhost:8000/api/v1/analyze/transaction" \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_id": "TXN-2024-009999",
    "user_id": "USR-00001",
    "amount": 9850.00,
    "currency": "USD",
    "merchant_category": "cryptocurrency",
    "merchant_name": "CryptoExchange Pro",
    "location": "Lagos, Nigeria",
    "device_id": "dev-0000000000",
    "ip_address": "192.168.1.100"
  }'
```

### Test Insurance Claim Analysis

```bash
curl -X POST "http://localhost:8000/api/v1/analyze/insurance-claim" \
  -H "Content-Type: application/json" \
  -d '{
    "claim_id": "CLM-2024-SUS001",
    "claimant_id": "CLMT-99999",
    "claim_type": "auto",
    "claim_amount": 75000.00,
    "incident_date": "2024-03-01",
    "filing_date": "2024-03-01",
    "description": "Total loss vehicle. Severe whiplash injury. Need immediate cash settlement.",
    "policy_id": "POL-AUTO-000001"
  }'
```

### Test User Profile Analysis

```bash
curl -X POST "http://localhost:8000/api/v1/analyze/user-profile" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "USR-SUS-001",
    "email": "random123abc@tempmail.org",
    "phone": "+1-000-555-0000",
    "account_age_days": 3,
    "device_count": 8,
    "login_frequency": 25.0,
    "failed_login_attempts": 7,
    "location_changes": 12
  }'
```

### Test E-Commerce Order Analysis

```bash
curl -X POST "http://localhost:8000/api/v1/analyze/ecommerce-order" \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "ORD-2024-SUS001",
    "customer_id": "CUST-FIRSTTIME",
    "order_total": 3500.00,
    "item_count": 5,
    "shipping_address": "999 Warehouse Blvd, Suite 100, Miami, FL 33101",
    "billing_address": "111 Different Road, Chicago, IL 60601",
    "payment_method": "prepaid_card",
    "is_expedited": true
  }'
```

### Test Health Check

```bash
curl "http://localhost:8000/api/v1/health"
```

### NEXT STEP

Self-Learning Agent:
An agent that retrains itself periodically using new labeled data (analyst feedback, confirmed frauds).

Adaptive Rule Agent:
An agent that monitors detection performance and suggests or auto-tunes rules based on recent fraud trends.

Investigation Orchestrator:
An agent that coordinates multiple sub-agents (e.g., device, transaction, identity) and escalates to human review if agents disagree.

External Intelligence Agent:
An agent that queries external sources (e.g., threat feeds, dark web, device reputation) to enrich risk analysis.

Explainability Agent:
An agent that generates human-readable explanations for why a transaction was flagged, using LLMs or rule tracing.

Alert Prioritization Agent:
An agent that ranks and clusters alerts for analysts, reducing alert fatigue and surfacing the most urgent cases.

Simulation/Red Team Agent:
An agent that simulates fraud attacks to test and improve the system’s detection capabilities.

User Behavior Profiling Agent:
An agent that builds and updates behavioral profiles for users, flagging deviations in real time.

Automated Response Agent:
An agent that can take actions (block, challenge, notify) based on risk and business rules, with optional human-in-the-loop.

Collaboration Agent:
An agent that facilitates communication between analysts, shares case context, and suggests next steps.
