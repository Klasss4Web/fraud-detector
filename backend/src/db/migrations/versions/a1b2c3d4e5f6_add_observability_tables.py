"""add_observability_tables

Revision ID: a1b2c3d4e5f6
Revises: f042ec99245d
Create Date: 2026-05-08 15:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "f042ec99245d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create observability and metrics tables."""

    # MetricSnapshot table - stores periodic system metrics
    op.create_table(
        "metric_snapshots",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("granularity", sa.String(20), nullable=False),
        sa.Column("alerts_received", sa.Integer, default=0),
        sa.Column("alerts_processed", sa.Integer, default=0),
        sa.Column("decisions_total", sa.Integer, default=0),
        sa.Column("decisions_allow", sa.Integer, default=0),
        sa.Column("decisions_block", sa.Integer, default=0),
        sa.Column("decisions_review", sa.Integer, default=0),
        sa.Column("escalations_total", sa.Integer, default=0),
        sa.Column("escalations_pending", sa.Integer, default=0),
        sa.Column("avg_processing_time_ms", sa.Float, default=0.0),
        sa.Column("risk_scores", postgresql.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Indexes for metric_snapshots
    op.create_index("ix_metric_time_granularity", "metric_snapshots", ["timestamp", "granularity"])
    op.create_unique_constraint(
        "uq_metric_snapshot", "metric_snapshots", ["timestamp", "granularity"]
    )

    # AgentPerformance table - stores agent execution metrics
    op.create_table(
        "agent_performance",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("granularity", sa.String(20), nullable=False),
        sa.Column("agent_name", sa.String(100), nullable=False, index=True),
        sa.Column("total_executions", sa.Integer, default=0),
        sa.Column("successful_executions", sa.Integer, default=0),
        sa.Column("failed_executions", sa.Integer, default=0),
        sa.Column("total_execution_time_ms", sa.Float, default=0.0),
        sa.Column("min_execution_time_ms", sa.Float),
        sa.Column("max_execution_time_ms", sa.Float),
        sa.Column("avg_execution_time_ms", sa.Float),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Indexes for agent_performance
    op.create_index("ix_agent_perf_time", "agent_performance", ["agent_name", "timestamp"])
    op.create_unique_constraint(
        "uq_agent_performance", "agent_performance", ["timestamp", "granularity", "agent_name"]
    )

    # EvaluationRecord table - stores predictions for evaluation
    op.create_table(
        "evaluation_records",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("prediction_id", sa.String(100), index=True),
        sa.Column("entity_id", sa.String(255), nullable=False, index=True),
        sa.Column("entity_type", sa.String(50), nullable=False, index=True),
        sa.Column("predicted_action", sa.String(50), nullable=False),
        sa.Column("predicted_risk_score", sa.Float, nullable=False),
        sa.Column("predicted_confidence", sa.Float),
        sa.Column("model_name", sa.String(100)),
        sa.Column("model_version", sa.String(50)),
        sa.Column(
            "actual_outcome",
            sa.Enum(
                "true_positive",
                "true_negative",
                "false_positive",
                "false_negative",
                name="evaluation_outcome_type",
            ),
        ),
        sa.Column("human_decision", sa.String(50)),
        sa.Column("feedback_source", sa.String(50)),
        sa.Column("feedback_received_at", sa.DateTime(timezone=True)),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )

    # Indexes for evaluation_records
    op.create_index("ix_eval_entity", "evaluation_records", ["entity_type", "entity_id"])
    op.create_index("ix_eval_outcome", "evaluation_records", ["actual_outcome", "created_at"])
    op.create_index("ix_eval_time", "evaluation_records", ["created_at"])

    # ConfusionMatrixSnapshot table - stores periodic accuracy snapshots
    op.create_table(
        "confusion_matrix_snapshots",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("granularity", sa.String(20), nullable=False),
        sa.Column("entity_type", sa.String(50)),
        sa.Column("model_name", sa.String(100)),
        sa.Column("true_positives", sa.Integer, default=0),
        sa.Column("true_negatives", sa.Integer, default=0),
        sa.Column("false_positives", sa.Integer, default=0),
        sa.Column("false_negatives", sa.Integer, default=0),
        sa.Column("precision", sa.Float),
        sa.Column("recall", sa.Float),
        sa.Column("f1_score", sa.Float),
        sa.Column("accuracy", sa.Float),
        sa.Column("total_evaluated", sa.Integer, default=0),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Indexes for confusion_matrix_snapshots
    op.create_index("ix_confusion_time", "confusion_matrix_snapshots", ["timestamp", "granularity"])
    op.create_unique_constraint(
        "uq_confusion_snapshot",
        "confusion_matrix_snapshots",
        ["timestamp", "granularity", "entity_type", "model_name"],
    )

    # LLMUsageRecord table - stores individual LLM API calls
    op.create_table(
        "llm_usage_records",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("call_id", sa.String(100), unique=True, index=True),
        sa.Column("model", sa.String(100), nullable=False, index=True),
        sa.Column("provider", sa.String(50)),
        sa.Column("input_tokens", sa.Integer, nullable=False),
        sa.Column("output_tokens", sa.Integer, nullable=False),
        sa.Column("total_tokens", sa.Integer, nullable=False),
        sa.Column("input_cost", sa.Float, default=0.0),
        sa.Column("output_cost", sa.Float, default=0.0),
        sa.Column("total_cost", sa.Float, default=0.0),
        sa.Column("latency_ms", sa.Float),
        sa.Column("success", sa.Boolean, default=True),
        sa.Column("error_message", sa.Text),
        sa.Column("agent_name", sa.String(100), index=True),
        sa.Column("operation", sa.String(100)),
        sa.Column("entity_id", sa.String(255)),
        sa.Column("request_metadata", postgresql.JSONB),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), index=True
        ),
    )

    # Indexes for llm_usage_records
    op.create_index("ix_llm_model_time", "llm_usage_records", ["model", "created_at"])
    op.create_index("ix_llm_agent_time", "llm_usage_records", ["agent_name", "created_at"])

    # LLMUsageSummary table - stores aggregated LLM usage
    op.create_table(
        "llm_usage_summaries",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("granularity", sa.String(20), nullable=False),
        sa.Column("model", sa.String(100)),
        sa.Column("agent_name", sa.String(100)),
        sa.Column("total_calls", sa.Integer, default=0),
        sa.Column("successful_calls", sa.Integer, default=0),
        sa.Column("failed_calls", sa.Integer, default=0),
        sa.Column("total_input_tokens", sa.Integer, default=0),
        sa.Column("total_output_tokens", sa.Integer, default=0),
        sa.Column("total_tokens", sa.Integer, default=0),
        sa.Column("total_cost", sa.Float, default=0.0),
        sa.Column("avg_latency_ms", sa.Float),
        sa.Column("min_latency_ms", sa.Float),
        sa.Column("max_latency_ms", sa.Float),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Indexes for llm_usage_summaries
    op.create_index("ix_llm_summary_time", "llm_usage_summaries", ["timestamp", "granularity"])
    op.create_unique_constraint(
        "uq_llm_summary", "llm_usage_summaries", ["timestamp", "granularity", "model", "agent_name"]
    )


def downgrade() -> None:
    """Drop observability tables."""
    op.drop_table("llm_usage_summaries")
    op.drop_table("llm_usage_records")
    op.drop_table("confusion_matrix_snapshots")
    op.drop_table("evaluation_records")
    op.drop_table("agent_performance")
    op.drop_table("metric_snapshots")

    # Drop the enum type
    op.execute("DROP TYPE IF EXISTS evaluation_outcome_type")
