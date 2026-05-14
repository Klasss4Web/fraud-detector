"""
Quick test script for mixed detection analysis.
Run with: python test_mixed_detection.py
"""

import sys

sys.path.insert(0, "src")

from .orchestrator import FraudDetectionOrchestrator


def test_mixed_detection():
    print("=" * 60)
    print("MIXED DETECTION ANALYSIS TEST")
    print("=" * 60)

    # Initialize orchestrator without LLM
    orchestrator = FraudDetectionOrchestrator(
        enable_llm=False,
        auto_investigate_threshold=60.0,
    )

    print("\nGenerating 10 legitimate + 10 fraudulent transactions...")

    # Run mixed detection analysis
    result = orchestrator.run_mixed_detection_analysis(
        num_legitimate=10,
        num_fraudulent=10,
        detection_threshold=60.0,
        use_llm=False,
    )

    # Display results
    print("\n" + "=" * 60)
    print("CONFUSION MATRIX")
    print("=" * 60)
    cm = result["confusion_matrix"]
    print(f"""
                    Predicted
                 Fraud    Legit
    Actual  +---------+---------+
    Fraud   |   {cm["true_positives"]:3d}   |   {cm["false_negatives"]:3d}   |  (TP, FN)
            +---------+---------+
    Legit   |   {cm["false_positives"]:3d}   |   {cm["true_negatives"]:3d}   |  (FP, TN)
            +---------+---------+
    """)

    print("\n" + "=" * 60)
    print("PERFORMANCE METRICS")
    print("=" * 60)
    metrics = result["metrics"]
    print(f"""
    Accuracy:           {metrics["accuracy"]:.2%}
    Precision:          {metrics["precision"]:.2%}
    Recall (TPR):       {metrics["recall"]:.2%}
    F1 Score:           {metrics["f1_score"]:.3f}
    Specificity (TNR):  {metrics["specificity"]:.2%}
    False Positive Rate:{metrics["false_positive_rate"]:.2%}
    False Negative Rate:{metrics["false_negative_rate"]:.2%}
    """)

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    summary = result["summary"]
    print(f"""
    Total Transactions:     {summary["total_transactions"]}
    - Legitimate:           {summary["total_legitimate"]}
    - Fraudulent:           {summary["total_fraudulent"]}
    Detection Threshold:    {summary["detection_threshold"]}
    
    Avg Fraud Score:        {summary["average_fraud_score"]:.1f}
    Avg Legitimate Score:   {summary["average_legitimate_score"]:.1f}
    Score Separation:       {summary["score_separation"]:.1f} (fraud - legit)
    """)

    print("\n" + "=" * 60)
    print("INTERPRETATION")
    print("=" * 60)
    interp = result["interpretation"]
    print(f"""
    {interp["accuracy_meaning"]}
    {interp["precision_meaning"]}
    {interp["recall_meaning"]}
    {interp["fpr_meaning"]}
    {interp["fnr_meaning"]}
    """)

    print("\n" + "=" * 60)
    print("DETAILED RESULTS (Sample)")
    print("=" * 60)
    print(f"\n{'ID':<12} {'Expected':<10} {'Predicted':<10} {'Score':<8} {'Outcome':<16}")
    print("-" * 60)
    for tx in result["detailed_results"][:10]:
        print(
            f"{tx['transaction_id']:<12} "
            f"{'FRAUD' if tx['expected_fraud'] else 'LEGIT':<10} "
            f"{'FRAUD' if tx['predicted_fraud'] else 'LEGIT':<10} "
            f"{tx['risk_score']:<8.1f} "
            f"{tx['outcome']:<16}"
        )

    # Validate results
    print("\n" + "=" * 60)
    print("VALIDATION")
    print("=" * 60)

    total_cm = (
        cm["true_positives"] + cm["true_negatives"] + cm["false_positives"] + cm["false_negatives"]
    )
    assert total_cm == 20, f"Confusion matrix total should be 20, got {total_cm}"
    print("[PASS] Confusion matrix counts sum correctly")

    assert 0 <= metrics["accuracy"] <= 1, "Accuracy out of range"
    assert 0 <= metrics["precision"] <= 1, "Precision out of range"
    assert 0 <= metrics["recall"] <= 1, "Recall out of range"
    print("[PASS] All metrics are in valid range [0, 1]")

    assert summary["score_separation"] > 0, "Fraud scores should be higher than legitimate"
    print("[PASS] System distinguishes fraud from legitimate (positive score separation)")

    assert metrics["accuracy"] > 0.5, "System should perform better than random"
    print("[PASS] System performs better than random chance")

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED!")
    print("=" * 60)

    total_cm = (
        cm["true_positives"] + cm["true_negatives"] + cm["false_positives"] + cm["false_negatives"]
    )
    assert total_cm == 20, f"Confusion matrix total should be 20, got {total_cm}"
    print("✓ Confusion matrix counts sum correctly")

    assert 0 <= metrics["accuracy"] <= 1, "Accuracy out of range"
    assert 0 <= metrics["precision"] <= 1, "Precision out of range"
    assert 0 <= metrics["recall"] <= 1, "Recall out of range"
    print("✓ All metrics are in valid range [0, 1]")

    assert summary["score_separation"] > 0, "Fraud scores should be higher than legitimate"
    print("✓ System distinguishes fraud from legitimate (positive score separation)")

    assert metrics["accuracy"] > 0.5, "System should perform better than random"
    print("✓ System performs better than random chance")

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    test_mixed_detection()
