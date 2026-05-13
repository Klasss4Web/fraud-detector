"""
Fraud Detection System - Demo Script
=====================================

Demonstrates the full capabilities of the multi-agent
fraud detection system with synthetic data.
"""

from data.data_generator import SyntheticDataGenerator
from orchestrator import FraudDetectionOrchestrator, EntityType, format_result


def print_header(title: str):
    """Print a formatted header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")


def demo_transaction_analysis(orchestrator, generator):
    """Demonstrate transaction fraud detection"""
    print_header("TRANSACTION FRAUD DETECTION DEMO")

    # Generate some transactions (mix of legitimate and fraudulent)
    print("Generating sample transactions...")
    transactions = [generator.generate_transaction() for _ in range(10)]

    # Analyze each transaction
    results = []
    for txn in transactions:
        from dataclasses import asdict

        result = orchestrator.analyze_transaction(asdict(txn), auto_investigate=False)
        results.append((txn, result))

    # Show results sorted by risk
    results.sort(key=lambda x: x[1].risk_score, reverse=True)

    print(f"\nAnalyzed {len(results)} transactions:\n")
    print(f"{'ID':<40} {'Amount':>10} {'Risk':>8} {'Level':<10} {'Actual':>10}")
    print("-" * 80)

    for txn, result in results:
        actual = "FRAUD" if txn.is_fraud else "legit"
        print(
            f"{result.entity_id:<40} ${txn.amount:>8.2f} {result.risk_score:>7.1f} {result.risk_level:<10} {actual:>10}"
        )

    # Show detailed analysis for highest risk
    print("\n" + "-" * 70)
    print("DETAILED ANALYSIS - HIGHEST RISK TRANSACTION")
    print("-" * 70)
    print(format_result(results[0][1]))


def demo_insurance_analysis(orchestrator, generator):
    """Demonstrate insurance fraud detection"""
    print_header("INSURANCE FRAUD DETECTION DEMO")

    print("Generating sample insurance claims...")
    claims = [generator.generate_insurance_claim() for _ in range(10)]

    results = []
    for claim in claims:
        from dataclasses import asdict

        result = orchestrator.analyze_insurance_claim(asdict(claim), auto_investigate=False)
        results.append((claim, result))

    results.sort(key=lambda x: x[1].risk_score, reverse=True)

    print(f"\nAnalyzed {len(results)} claims:\n")
    print(f"{'ID':<20} {'Type':<12} {'Amount':>12} {'Risk':>8} {'Level':<10} {'Actual':>10}")
    print("-" * 80)

    for claim, result in results:
        actual = "FRAUD" if claim.is_fraud else "legit"
        print(
            f"{claim.claim_id:<20} {claim.claim_type:<12} ${claim.claim_amount:>10.2f} {result.risk_score:>7.1f} {result.risk_level:<10} {actual:>10}"
        )

    # Show top signals across all claims
    print("\n" + "-" * 70)
    print("TOP FRAUD SIGNALS DETECTED")
    print("-" * 70)

    all_signals = []
    for _, result in results:
        all_signals.extend(result.signals)

    signal_counts = {}
    for signal in all_signals:
        name = signal["name"]
        signal_counts[name] = signal_counts.get(name, 0) + 1

    for name, count in sorted(signal_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"  {name}: detected {count} times")


def demo_identity_analysis(orchestrator, generator):
    """Demonstrate identity fraud detection"""
    print_header("IDENTITY FRAUD DETECTION DEMO")

    print("Generating sample user profiles...")
    profiles = [generator.generate_user_profile() for _ in range(10)]

    results = []
    for profile in profiles:
        from dataclasses import asdict

        result = orchestrator.analyze_user_profile(asdict(profile), auto_investigate=False)
        results.append((profile, result))

    results.sort(key=lambda x: x[1].risk_score, reverse=True)

    print(f"\nAnalyzed {len(results)} profiles:\n")
    print(
        f"{'User ID':<20} {'Email Domain':<20} {'Age (days)':>10} {'Risk':>8} {'Level':<10} {'Actual':>10}"
    )
    print("-" * 90)

    for profile, result in results:
        actual = "FRAUD" if profile.is_fraud else "legit"
        print(
            f"{profile.user_id:<20} {profile.email_domain:<20} {profile.account_age_days:>10} {result.risk_score:>7.1f} {result.risk_level:<10} {actual:>10}"
        )


def demo_ecommerce_analysis(orchestrator, generator):
    """Demonstrate e-commerce fraud detection"""
    print_header("E-COMMERCE FRAUD DETECTION DEMO")

    print("Generating sample orders...")
    orders = [generator.generate_ecommerce_order() for _ in range(10)]

    results = []
    for order in orders:
        from dataclasses import asdict

        result = orchestrator.analyze_ecommerce_order(asdict(order), auto_investigate=False)
        results.append((order, result))

    results.sort(key=lambda x: x[1].risk_score, reverse=True)

    print(f"\nAnalyzed {len(results)} orders:\n")
    print(
        f"{'Order ID':<20} {'Amount':>10} {'Items':>6} {'New Cust':>10} {'Risk':>8} {'Actual':>10}"
    )
    print("-" * 80)

    for order, result in results:
        actual = "FRAUD" if order.is_fraud else "legit"
        new_cust = "Yes" if order.is_new_customer else "No"
        print(
            f"{order.order_id:<20} ${order.total_amount:>8.2f} {len(order.items):>6} {new_cust:>10} {result.risk_score:>7.1f} {actual:>10}"
        )


def demo_batch_analysis(orchestrator, generator):
    """Demonstrate batch processing capabilities"""
    print_header("BATCH ANALYSIS DEMO")

    print("Generating larger dataset for batch analysis...")
    from dataclasses import asdict

    transactions = [asdict(generator.generate_transaction()) for _ in range(50)]

    print(f"Analyzing {len(transactions)} transactions in batch...\n")

    results = orchestrator.batch_analyze(
        items=transactions, entity_type=EntityType.TRANSACTION, auto_investigate=False
    )

    # Get summary
    summary = orchestrator.get_high_risk_summary(results)

    print("BATCH ANALYSIS SUMMARY")
    print("-" * 40)
    print(f"Total Analyzed:     {summary['total_analyzed']}")
    print(f"High Risk Cases:    {summary['high_risk_count']}")
    print(f"High Risk Rate:     {summary['high_risk_rate']:.1f}%")
    print(f"Average Risk Score: {summary['average_risk_score']:.1f}")
    print()
    print("Risk Distribution:")
    for level, count in summary["risk_distribution"].items():
        bar = "#" * count
        print(f"  {level.upper():<10} {count:>3} {bar}")

    print("\nTop 5 High Risk Cases:")
    print("-" * 40)
    for case in summary["high_risk_cases"][:5]:
        print(f"  {case['entity_id']}: Score {case['risk_score']:.1f}")


def demo_comprehensive_analysis(orchestrator, generator):
    """Demonstrate comprehensive multi-source analysis"""
    print_header("COMPREHENSIVE ANALYSIS DEMO")

    print("Generating correlated data (transaction + user profile)...")
    from dataclasses import asdict

    # Generate a suspicious transaction and profile
    transaction = asdict(generator.generate_transaction(force_fraud=True))
    profile = asdict(generator.generate_user_profile(force_fraud=True))

    # Link them
    profile["user_id"] = transaction["user_id"]

    print(f"\nAnalyzing linked transaction and user profile...")
    print(f"User ID: {transaction['user_id']}")
    print(f"Transaction Amount: ${transaction['amount']:.2f}")
    print(f"Profile Email: {profile['email']}")

    result = orchestrator.analyze_comprehensive(
        transaction_data=transaction, user_profile=profile, auto_investigate=False
    )

    print("\n" + format_result(result))


def main():
    """Run all demos"""
    print("\n" + "=" * 70)
    print("       FRAUD DETECTION SYSTEM - DEMONSTRATION")
    print("       Multi-Agent AI System for Fraud Prevention")
    print("=" * 70)

    # Initialize components
    print("\nInitializing fraud detection system...")
    generator = SyntheticDataGenerator(fraud_rate=0.25)  # 25% fraud rate for demo
    orchestrator = FraudDetectionOrchestrator(
        enable_llm=False,  # Disable LLM for demo (set True if you have API key)
        auto_investigate_threshold=70.0,
    )
    print("System ready!\n")

    # Run demos
    demo_transaction_analysis(orchestrator, generator)
    demo_insurance_analysis(orchestrator, generator)
    demo_identity_analysis(orchestrator, generator)
    demo_ecommerce_analysis(orchestrator, generator)
    demo_batch_analysis(orchestrator, generator)
    demo_comprehensive_analysis(orchestrator, generator)

    print_header("DEMO COMPLETE")
    print("The fraud detection system successfully analyzed:")
    print("  - Financial transactions")
    print("  - Insurance claims")
    print("  - User identity profiles")
    print("  - E-commerce orders")
    print("\nThe system detected fraud patterns including:")
    print("  - Velocity attacks")
    print("  - Amount anomalies")
    print("  - Geographic risks")
    print("  - Identity fraud indicators")
    print("  - Chargeback abuse")
    print("\nTo enable LLM-powered investigation, set OPENAI_API_KEY")
    print("environment variable and enable_llm=True in orchestrator.")
    print()


if __name__ == "__main__":
    main()
