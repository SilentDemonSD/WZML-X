import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional

from .. import LOGGER


class ErrorSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class ErrorRecord:
    timestamp: datetime
    error_type: str
    message: str
    severity: ErrorSeverity
    context: Dict[str, Any] = field(default_factory=dict)
    traceback: Optional[str] = None


@dataclass
class HealthMetrics:
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    error_rate: float = 0.0
    avg_response_time: float = 0.0
    last_updated: datetime = field(default_factory=datetime.now)


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED

    def can_execute(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        elif self.state == CircuitState.OPEN:
            if (datetime.now() - self.last_failure_time).seconds >= self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                return True
            return False
        else:
            return True

    def on_success(self):
        self.failure_count = 0
        self.state = CircuitState.CLOSED

    def on_failure(self):
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN


class ErrorMonitor:
    def __init__(self):
        self.errors: List[ErrorRecord] = []
        self.health_metrics: Dict[str, HealthMetrics] = {}
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.max_errors = 1000

    def record_error(self, error_type: str, message: str, severity: ErrorSeverity = ErrorSeverity.MEDIUM, 
                    context: Dict[str, Any] = None, traceback: str = None):
        error_record = ErrorRecord(
            timestamp=datetime.now(),
            error_type=error_type,
            message=message,
            severity=severity,
            context=context or {},
            traceback=traceback
        )
        
        self.errors.append(error_record)
        if len(self.errors) > self.max_errors:
            self.errors.pop(0)

        LOGGER.error(f"Error recorded: {error_type} - {message}")

    def update_health_metrics(self, operation: str, success: bool, response_time: float):
        if operation not in self.health_metrics:
            self.health_metrics[operation] = HealthMetrics()

        metrics = self.health_metrics[operation]
        metrics.total_operations += 1
        
        if success:
            metrics.successful_operations += 1
        else:
            metrics.failed_operations += 1

        metrics.error_rate = metrics.failed_operations / metrics.total_operations
        metrics.avg_response_time = (metrics.avg_response_time * (metrics.total_operations - 1) + response_time) / metrics.total_operations
        metrics.last_updated = datetime.now()

    def get_circuit_breaker(self, operation: str) -> CircuitBreaker:
        if operation not in self.circuit_breakers:
            self.circuit_breakers[operation] = CircuitBreaker()
        return self.circuit_breakers[operation]

    def get_error_summary(self, hours: int = 24) -> Dict[str, Any]:
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_errors = [e for e in self.errors if e.timestamp >= cutoff_time]
        
        return {
            'total_errors': len(recent_errors),
            'errors_by_severity': {
                severity.value: len([e for e in recent_errors if e.severity == severity])
                for severity in ErrorSeverity
            },
            'errors_by_type': {
                error_type: len([e for e in recent_errors if e.error_type == error_type])
                for error_type in set(e.error_type for e in recent_errors)
            },
            'health_metrics': {
                op: {
                    'error_rate': metrics.error_rate,
                    'avg_response_time': metrics.avg_response_time,
                    'total_operations': metrics.total_operations
                }
                for op, metrics in self.health_metrics.items()
            }
        }


error_monitor = ErrorMonitor()


def error_handler(operation: str = None):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            op_name = operation or func.__name__
            start_time = time.time()
            
            circuit_breaker = error_monitor.get_circuit_breaker(op_name)
            if not circuit_breaker.can_execute():
                raise Exception(f"Circuit breaker open for {op_name}")

            try:
                result = await func(*args, **kwargs)
                circuit_breaker.on_success()
                error_monitor.update_health_metrics(op_name, True, time.time() - start_time)
                return result
            except Exception as e:
                circuit_breaker.on_failure()
                error_monitor.update_health_metrics(op_name, False, time.time() - start_time)
                error_monitor.record_error(
                    error_type=type(e).__name__,
                    message=str(e),
                    severity=ErrorSeverity.HIGH,
                    context={'operation': op_name, 'args': str(args), 'kwargs': str(kwargs)}
                )
                raise

        return wrapper
    return decorator


def circuit_breaker(operation: str, failure_threshold: int = 5, recovery_timeout: int = 60):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cb = CircuitBreaker(failure_threshold, recovery_timeout)
            if not cb.can_execute():
                raise Exception(f"Circuit breaker open for {operation}")

            try:
                result = await func(*args, **kwargs)
                cb.on_success()
                return result
            except Exception:
                cb.on_failure()
                raise

        return wrapper
    return decorator