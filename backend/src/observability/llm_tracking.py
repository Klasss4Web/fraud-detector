"""
LLM Usage Tracking for Fraud Detection System.

Tracks token usage, costs, and performance metrics for all LLM calls.
Persists data to PostgreSQL for historical tracking.
"""

import time
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from collections import defaultdict
import threading

logger = logging.getLogger(__name__)


# Pricing per 1M tokens (as of 2024 - update as needed)
MODEL_PRICING = {
    # OpenAI models
    "gpt-4": {"input": 30.00, "output": 60.00},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-4o": {"input": 5.00, "output": 15.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    # OpenRouter models
    "openai/gpt-4o": {"input": 5.00, "output": 15.00},
    "openai/gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "openai/gpt-oss-120b": {"input": 0.00, "output": 0.00},  # Free tier
    "anthropic/claude-3-opus": {"input": 15.00, "output": 75.00},
    "anthropic/claude-3-sonnet": {"input": 3.00, "output": 15.00},
    "anthropic/claude-3-haiku": {"input": 0.25, "output": 1.25},
    "meta-llama/llama-3-70b": {"input": 0.59, "output": 0.79},
    "mistralai/mixtral-8x7b": {"input": 0.24, "output": 0.24},
    # Default for unknown models
    "default": {"input": 1.00, "output": 2.00},
}


@dataclass
class LLMCall:
    """Record of a single LLM API call."""
    
    call_id: str
    model: str
    timestamp: datetime
    
    # Token usage
    input_tokens: int
    output_tokens: int
    total_tokens: int
    
    # Cost (in USD)
    input_cost: float
    output_cost: float
    total_cost: float
    
    # Performance
    latency_ms: float
    success: bool
    
    # Context
    agent_name: str
    operation: str  # "analyze", "recommend", "investigate", etc.
    entity_id: Optional[str] = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "call_id": self.call_id,
            "model": self.model,
            "timestamp": self.timestamp.isoformat(),
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "input_cost": round(self.input_cost, 6),
            "output_cost": round(self.output_cost, 6),
            "total_cost": round(self.total_cost, 6),
            "latency_ms": round(self.latency_ms, 2),
            "success": self.success,
            "agent_name": self.agent_name,
            "operation": self.operation,
            "entity_id": self.entity_id,
            "error": self.error,
        }


@dataclass
class LLMUsageStats:
    """Aggregated LLM usage statistics."""
    
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    
    total_cost: float = 0.0
    
    total_latency_ms: float = 0.0
    min_latency_ms: float = float('inf')
    max_latency_ms: float = 0.0
    
    # Per-model breakdown
    by_model: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Per-agent breakdown
    by_agent: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Per-operation breakdown
    by_operation: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    @property
    def avg_latency_ms(self) -> float:
        return self.total_latency_ms / self.total_calls if self.total_calls > 0 else 0
    
    @property
    def success_rate(self) -> float:
        return self.successful_calls / self.total_calls if self.total_calls > 0 else 0
    
    @property
    def avg_tokens_per_call(self) -> float:
        return self.total_tokens / self.total_calls if self.total_calls > 0 else 0
    
    @property
    def avg_cost_per_call(self) -> float:
        return self.total_cost / self.total_calls if self.total_calls > 0 else 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_calls": self.total_calls,
            "successful_calls": self.successful_calls,
            "failed_calls": self.failed_calls,
            "success_rate": round(self.success_rate, 4),
            "tokens": {
                "input": self.total_input_tokens,
                "output": self.total_output_tokens,
                "total": self.total_tokens,
                "avg_per_call": round(self.avg_tokens_per_call, 1),
            },
            "cost": {
                "total_usd": round(self.total_cost, 4),
                "avg_per_call_usd": round(self.avg_cost_per_call, 6),
            },
            "latency": {
                "avg_ms": round(self.avg_latency_ms, 2),
                "min_ms": round(self.min_latency_ms, 2) if self.min_latency_ms != float('inf') else 0,
                "max_ms": round(self.max_latency_ms, 2),
            },
            "by_model": self.by_model,
            "by_agent": self.by_agent,
            "by_operation": self.by_operation,
        }


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> tuple:
    """Calculate cost based on model pricing."""
    # Normalize model name
    model_key = model.lower()
    
    # Find matching pricing
    pricing = MODEL_PRICING.get(model_key)
    if not pricing:
        # Try partial match
        for key in MODEL_PRICING:
            if key in model_key or model_key in key:
                pricing = MODEL_PRICING[key]
                break
    
    if not pricing:
        pricing = MODEL_PRICING["default"]
    
    # Calculate costs (pricing is per 1M tokens)
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    
    return input_cost, output_cost


class LLMUsageTracker:
    """
    Tracks and aggregates LLM usage across the application.
    
    Thread-safe singleton that records all LLM API calls.
    Persists to PostgreSQL when available, with in-memory fallback.
    """
    
    def __init__(self):
        self._calls: List[LLMCall] = []
        self._lock = threading.Lock()
        self._call_counter = 0
        self._db_available = False
        
        # Try to initialize database connection
        self._init_db()
    
    def _init_db(self):
        """Initialize database connection if available."""
        try:
            from db.session import get_db
            self._db_available = True
            logger.info("LLM tracker: Database persistence enabled")
        except ImportError:
            self._db_available = False
            logger.warning("LLM tracker: Database not available, using in-memory storage")
    
    def _get_db_session(self):
        """Get a database session."""
        if not self._db_available:
            return None
        try:
            from db.session import SessionLocal
            return SessionLocal()
        except Exception as e:
            logger.warning(f"Failed to get DB session: {e}")
            return None
    
    def record_call(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: float,
        success: bool,
        agent_name: str,
        operation: str,
        entity_id: Optional[str] = None,
        error: Optional[str] = None,
    ) -> LLMCall:
        """
        Record an LLM API call.
        
        Args:
            model: Model name (e.g., "gpt-4o-mini")
            input_tokens: Number of input/prompt tokens
            output_tokens: Number of output/completion tokens
            latency_ms: Call latency in milliseconds
            success: Whether the call succeeded
            agent_name: Name of the agent making the call
            operation: Type of operation (analyze, recommend, etc.)
            entity_id: Optional entity being processed
            error: Error message if call failed
            
        Returns:
            LLMCall record
        """
        input_cost, output_cost = calculate_cost(model, input_tokens, output_tokens)
        
        with self._lock:
            self._call_counter += 1
            call_id = f"llm_{self._call_counter:06d}"
        
        call = LLMCall(
            call_id=call_id,
            model=model,
            timestamp=datetime.utcnow(),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            input_cost=input_cost,
            output_cost=output_cost,
            total_cost=input_cost + output_cost,
            latency_ms=latency_ms,
            success=success,
            agent_name=agent_name,
            operation=operation,
            entity_id=entity_id,
            error=error,
        )
        
        # Store in memory
        with self._lock:
            self._calls.append(call)
            # Keep only last 1000 calls in memory
            if len(self._calls) > 1000:
                self._calls = self._calls[-1000:]
        
        # Persist to database
        self._persist_to_db(call)
        
        logger.info(
            f"LLM call recorded: {model} | {input_tokens}+{output_tokens} tokens | "
            f"${call.total_cost:.4f} | {latency_ms:.0f}ms | {agent_name}/{operation}"
        )
        
        return call
    
    def _persist_to_db(self, call: LLMCall):
        """Persist call to database."""
        db = self._get_db_session()
        if not db:
            return
        
        try:
            from db.metrics_repository import LLMUsageRepository
            repo = LLMUsageRepository(db)
            repo.record_call(
                call_id=call.call_id,
                model=call.model,
                input_tokens=call.input_tokens,
                output_tokens=call.output_tokens,
                total_tokens=call.total_tokens,
                input_cost=call.input_cost,
                output_cost=call.output_cost,
                total_cost=call.total_cost,
                latency_ms=call.latency_ms,
                success=call.success,
                agent_name=call.agent_name,
                operation=call.operation,
                entity_id=call.entity_id,
                error_message=call.error,
            )
        except Exception as e:
            logger.warning(f"Failed to persist LLM call to database: {e}")
        finally:
            db.close()
    
    def get_stats(self, since: Optional[datetime] = None, hours: int = 24) -> Dict[str, Any]:
        """
        Get aggregated usage statistics.
        
        Args:
            since: Only include calls after this time
            hours: Hours to look back (used if since is None)
            
        Returns:
            Dictionary with aggregated metrics
        """
        # Try database first
        db = self._get_db_session()
        if db:
            try:
                from db.metrics_repository import LLMUsageRepository
                repo = LLMUsageRepository(db)
                return repo.get_usage_stats(hours=hours)
            except Exception as e:
                logger.warning(f"Failed to get stats from database: {e}")
            finally:
                db.close()
        
        # Fall back to in-memory
        return self._get_stats_from_memory(since)
    
    def _get_stats_from_memory(self, since: Optional[datetime] = None) -> Dict[str, Any]:
        """Get stats from in-memory storage."""
        stats = LLMUsageStats()
        stats.by_model = defaultdict(lambda: {
            "calls": 0, "tokens": 0, "cost": 0.0, "latency_ms": 0.0
        })
        stats.by_agent = defaultdict(lambda: {
            "calls": 0, "tokens": 0, "cost": 0.0, "latency_ms": 0.0
        })
        stats.by_operation = defaultdict(lambda: {
            "calls": 0, "tokens": 0, "cost": 0.0, "latency_ms": 0.0
        })
        
        with self._lock:
            calls = self._calls if since is None else [
                c for c in self._calls if c.timestamp >= since
            ]
        
        for call in calls:
            stats.total_calls += 1
            
            if call.success:
                stats.successful_calls += 1
            else:
                stats.failed_calls += 1
            
            stats.total_input_tokens += call.input_tokens
            stats.total_output_tokens += call.output_tokens
            stats.total_tokens += call.total_tokens
            stats.total_cost += call.total_cost
            stats.total_latency_ms += call.latency_ms
            stats.min_latency_ms = min(stats.min_latency_ms, call.latency_ms)
            stats.max_latency_ms = max(stats.max_latency_ms, call.latency_ms)
            
            # By model
            stats.by_model[call.model]["calls"] += 1
            stats.by_model[call.model]["tokens"] += call.total_tokens
            stats.by_model[call.model]["cost"] += call.total_cost
            
            # By agent
            stats.by_agent[call.agent_name]["calls"] += 1
            stats.by_agent[call.agent_name]["tokens"] += call.total_tokens
            stats.by_agent[call.agent_name]["cost"] += call.total_cost
            
            # By operation
            stats.by_operation[call.operation]["calls"] += 1
            stats.by_operation[call.operation]["tokens"] += call.total_tokens
            stats.by_operation[call.operation]["cost"] += call.total_cost
        
        # Convert to dict format
        for breakdown in [stats.by_model, stats.by_agent, stats.by_operation]:
            for key in breakdown:
                breakdown[key]["cost"] = round(breakdown[key]["cost"], 4)
        
        stats.by_model = dict(stats.by_model)
        stats.by_agent = dict(stats.by_agent)
        stats.by_operation = dict(stats.by_operation)
        
        return stats.to_dict()
    
    def get_recent_calls(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent LLM calls."""
        # Try database first
        db = self._get_db_session()
        if db:
            try:
                from db.metrics_repository import LLMUsageRepository
                repo = LLMUsageRepository(db)
                return repo.get_recent_calls(limit=limit)
            except Exception as e:
                logger.warning(f"Failed to get recent calls from database: {e}")
            finally:
                db.close()
        
        # Fall back to in-memory
        with self._lock:
            recent = self._calls[-limit:]
        return [call.to_dict() for call in reversed(recent)]
    
    def get_hourly_stats(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get hourly breakdown of usage for the last N hours."""
        # Try database first
        db = self._get_db_session()
        if db:
            try:
                from db.metrics_repository import LLMUsageRepository
                repo = LLMUsageRepository(db)
                return repo.get_hourly_stats(hours=hours)
            except Exception as e:
                logger.warning(f"Failed to get hourly stats from database: {e}")
            finally:
                db.close()
        
        # Fall back to in-memory calculation
        now = datetime.utcnow()
        hourly = []
        
        for h in range(hours):
            start = now - timedelta(hours=h+1)
            end = now - timedelta(hours=h)
            
            with self._lock:
                calls = [c for c in self._calls if start <= c.timestamp < end]
            
            hourly.append({
                "hour": end.strftime("%Y-%m-%d %H:00"),
                "calls": len(calls),
                "tokens": sum(c.total_tokens for c in calls),
                "cost": round(sum(c.total_cost for c in calls), 4),
            })
        
        return list(reversed(hourly))


# Global tracker instance
_tracker: Optional[LLMUsageTracker] = None


def get_llm_tracker() -> LLMUsageTracker:
    """Get the global LLM usage tracker."""
    global _tracker
    if _tracker is None:
        _tracker = LLMUsageTracker()
    return _tracker


def record_llm_call(
    model: str,
    input_tokens: int,
    output_tokens: int,
    latency_ms: float,
    success: bool = True,
    agent_name: str = "unknown",
    operation: str = "unknown",
    entity_id: Optional[str] = None,
    error: Optional[str] = None,
) -> LLMCall:
    """Convenience function to record an LLM call."""
    return get_llm_tracker().record_call(
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_ms=latency_ms,
        success=success,
        agent_name=agent_name,
        operation=operation,
        entity_id=entity_id,
        error=error,
    )


