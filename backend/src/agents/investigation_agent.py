"""
Investigation Agent with LLM Reasoning
=======================================

Uses OpenAI GPT for intelligent fraud investigation:
- Natural language analysis of fraud patterns
- Contextual reasoning about signals
- Investigation recommendations
- Report generation
"""

import os
import json
from typing import Dict, Any, List, Optional
from .base_agent import BaseAgent, AgentResult, FraudSignal, RiskLevel
from .risk_scoring_agent import AggregatedRisk

MODEL = "openai/gpt-oss-120b"

class InvestigationAgent(BaseAgent):
    """
    Agent that uses LLM for deep investigation and reasoning
    about potential fraud cases.
    """

    SYSTEM_PROMPT = """You are an expert fraud investigator and analyst. Your role is to:
1. Analyze fraud detection signals and evidence
2. Provide clear reasoning about the likelihood of fraud
3. Identify patterns that may indicate specific fraud schemes
4. Recommend specific investigation steps
5. Generate clear, actionable reports

Be precise, factual, and focus on the evidence provided. 
Do not speculate beyond what the data supports.
Prioritize protecting legitimate customers while identifying true fraud."""

    def __init__(self, api_key: str = None):
        super().__init__("InvestigationAgent")
        # self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = "https://openrouter.ai/api/v1"
        # self.api_key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY")
        self.api_key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY")
        self.client = None
        # print(f"API KEYS:  {self.api_key}")

        if self.api_key:
            try:
                from openai import OpenAI

                self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
                self.log("OpenAI client initialized")
            except ImportError:
                self.log(
                    "OpenAI package not installed. Install with: pip install openai"
                )
        else:
            self.log("No API key provided. LLM features disabled.")

    def analyze(self, data: Dict[str, Any]) -> AgentResult:
        """Basic analysis - use investigate() for full investigation"""
        return self._create_result(
            entity_id=data.get("entity_id", "unknown"),
            risk_score=0,
            signals=[],
            recommendation="Use investigate() for full LLM-powered investigation",
        )

    def investigate(
        self,
        aggregated_risk: AggregatedRisk,
        raw_data: Dict[str, Any],
        include_recommendations: bool = True,
    ) -> Dict[str, Any]:
        """
        Perform deep investigation using LLM reasoning.

        Args:
            aggregated_risk: Risk assessment from RiskScoringAgent
            raw_data: Original entity data
            include_recommendations: Whether to generate investigation recommendations

        Returns:
            Investigation report with LLM analysis
        """
        self.log(
            f"Investigating {aggregated_risk.entity_type} {aggregated_risk.entity_id}"
        )

        if not self.client:
            return self._generate_fallback_report(aggregated_risk, raw_data)

        # Prepare context for LLM
        context = self._prepare_investigation_context(aggregated_risk, raw_data)

        # Generate analysis
        try:
            analysis = self._llm_analyze(context, aggregated_risk.entity_type)

            # Generate recommendations if requested
            recommendations = []
            if include_recommendations and aggregated_risk.requires_investigation:
                recommendations = self._llm_recommend_actions(context, analysis)

            return {
                "entity_id": aggregated_risk.entity_id,
                "entity_type": aggregated_risk.entity_type,
                "risk_score": aggregated_risk.final_risk_score,
                "risk_level": aggregated_risk.risk_level.value,
                "llm_analysis": analysis,
                "fraud_probability": self._extract_probability(analysis),
                "recommended_actions": recommendations,
                "signals_summary": self._summarize_signals(aggregated_risk.top_signals),
                "investigation_priority": self._calculate_priority(aggregated_risk),
                "status": "completed",
            }

        except Exception as e:
            self.log(f"LLM analysis failed: {e}")
            return self._generate_fallback_report(aggregated_risk, raw_data)

    def _prepare_investigation_context(
        self, risk: AggregatedRisk, raw_data: Dict[str, Any]
    ) -> str:
        """Prepare context string for LLM"""

        signals_text = "\n".join(
            [
                f"- {s.name}: {s.description} (weight: {s.weight:.2f}, category: {s.category})"
                for s in risk.top_signals
            ]
        )

        # Sanitize raw data (remove sensitive fields for LLM)
        safe_data = {
            k: v
            for k, v in raw_data.items()
            if k not in ["ssn", "ssn_last4", "password", "api_key"]
        }

        context = f"""
FRAUD INVESTIGATION CASE

Entity Type: {risk.entity_type}
Entity ID: {risk.entity_id}
Risk Score: {risk.final_risk_score}/100
Risk Level: {risk.risk_level.value}
Confidence: {risk.confidence}

DETECTED SIGNALS:
{signals_text if signals_text else "No specific signals detected"}

AGENT SCORES:
{json.dumps(risk.agent_scores, indent=2)}

ENTITY DATA:
{json.dumps(safe_data, indent=2, default=str)}

INITIAL RECOMMENDATION:
{risk.recommendation}
"""
        return context

    def _llm_analyze(self, context: str, entity_type: str) -> str:
        """Get LLM analysis of the case"""

        prompt = f"""Analyze this potential fraud case and provide your assessment.

{context}

Provide a concise analysis (2-3 paragraphs) covering:
1. Assessment of fraud likelihood based on the signals
2. Pattern recognition - what type of fraud scheme this might represent
3. Key evidence that supports or contradicts fraud
4. Confidence in your assessment

Be specific and reference the actual signals and data provided."""

        response = self.client.chat.completions.create(
            # model="openai/gpt-4o-mini",
            model=MODEL,
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            max_tokens=600,
            temperature=0.3,
        )

        return response.choices[0].message.content

    def _llm_recommend_actions(self, context: str, analysis: str) -> List[str]:
        """Get LLM recommendations for investigation actions"""

        prompt = f"""Based on this fraud case analysis, recommend specific investigation actions.

CASE CONTEXT:
{context}

ANALYSIS:
{analysis}

Provide 3-5 specific, actionable investigation steps. 
Format as a numbered list. Be specific to this case."""

        response = self.client.chat.completions.create(
            # model="openai/gpt-4o-mini",
            model=MODEL,
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            max_tokens=400,
            temperature=0.3,
        )

        # Parse numbered list
        content = response.choices[0].message.content
        lines = content.strip().split("\n")
        recommendations = []

        for line in lines:
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith("-")):
                # Remove number/bullet prefix
                clean = line.lstrip("0123456789.-) ").strip()
                if clean:
                    recommendations.append(clean)

        return recommendations[:5]

    def _extract_probability(self, analysis: str) -> str:
        """Extract fraud probability estimate from analysis"""
        analysis_lower = analysis.lower()

        if any(
            word in analysis_lower
            for word in [
                "highly likely",
                "strong evidence",
                "clear indication",
                "definite",
            ]
        ):
            return "high"
        elif any(
            word in analysis_lower
            for word in ["likely", "probable", "suggests", "indicates"]
        ):
            return "medium"
        elif any(
            word in analysis_lower for word in ["possible", "may", "could", "uncertain"]
        ):
            return "low"
        else:
            return "undetermined"

    def _summarize_signals(self, signals: List[FraudSignal]) -> List[Dict[str, Any]]:
        """Create summary of top signals"""
        return [
            {
                "name": s.name,
                "description": s.description,
                "severity": "high"
                if s.weight >= 0.7
                else "medium"
                if s.weight >= 0.4
                else "low",
            }
            for s in signals
        ]

    def _calculate_priority(self, risk: AggregatedRisk) -> str:
        """Calculate investigation priority"""
        if risk.final_risk_score >= 80:
            return "critical"
        elif risk.final_risk_score >= 60:
            return "high"
        elif risk.final_risk_score >= 40:
            return "medium"
        else:
            return "low"

    def _generate_fallback_report(
        self, risk: AggregatedRisk, raw_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate report without LLM when unavailable"""

        signals_summary = self._summarize_signals(risk.top_signals)

        # Rule-based analysis
        if risk.final_risk_score >= 80:
            analysis = "High-risk case with multiple strong fraud indicators. Immediate review recommended."
            probability = "high"
        elif risk.final_risk_score >= 60:
            analysis = (
                "Elevated risk with concerning patterns. Investigation warranted."
            )
            probability = "medium"
        elif risk.final_risk_score >= 40:
            analysis = (
                "Moderate risk indicators present. Enhanced monitoring recommended."
            )
            probability = "low"
        else:
            analysis = "Low risk profile. Standard processing appropriate."
            probability = "very_low"

        # Generate basic recommendations
        recommendations = []
        if risk.final_risk_score >= 60:
            recommendations = [
                "Review all signals and supporting evidence",
                "Check historical patterns for this entity",
                "Verify identity/documentation if applicable",
                "Escalate to senior analyst if high-value",
            ]

        return {
            "entity_id": risk.entity_id,
            "entity_type": risk.entity_type,
            "risk_score": risk.final_risk_score,
            "risk_level": risk.risk_level.value,
            "llm_analysis": analysis,
            "fraud_probability": probability,
            "recommended_actions": recommendations,
            "signals_summary": signals_summary,
            "investigation_priority": self._calculate_priority(risk),
            "status": "completed_without_llm",
        }

    def generate_report(
        self, investigation_result: Dict[str, Any], format: str = "text"
    ) -> str:
        """
        Generate formatted investigation report.

        Args:
            investigation_result: Result from investigate()
            format: Output format ('text', 'markdown', 'json')

        Returns:
            Formatted report string
        """
        if format == "json":
            return json.dumps(investigation_result, indent=2)

        # Text/Markdown format
        report = []
        report.append("=" * 60)
        report.append("FRAUD INVESTIGATION REPORT")
        report.append("=" * 60)
        report.append("")
        report.append(f"Entity ID: {investigation_result['entity_id']}")
        report.append(f"Entity Type: {investigation_result['entity_type']}")
        report.append(f"Risk Score: {investigation_result['risk_score']}/100")
        report.append(f"Risk Level: {investigation_result['risk_level'].upper()}")
        report.append(
            f"Fraud Probability: {investigation_result['fraud_probability'].upper()}"
        )
        report.append(
            f"Investigation Priority: {investigation_result['investigation_priority'].upper()}"
        )
        report.append("")
        report.append("-" * 40)
        report.append("ANALYSIS")
        report.append("-" * 40)
        report.append(investigation_result["llm_analysis"])
        report.append("")

        if investigation_result["signals_summary"]:
            report.append("-" * 40)
            report.append("KEY SIGNALS")
            report.append("-" * 40)
            for signal in investigation_result["signals_summary"]:
                severity = signal["severity"].upper()
                report.append(f"[{severity}] {signal['name']}: {signal['description']}")
            report.append("")

        if investigation_result["recommended_actions"]:
            report.append("-" * 40)
            report.append("RECOMMENDED ACTIONS")
            report.append("-" * 40)
            for i, action in enumerate(investigation_result["recommended_actions"], 1):
                report.append(f"{i}. {action}")
            report.append("")

        report.append("=" * 60)

        return "\n".join(report)
