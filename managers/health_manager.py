import time
import threading
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class HealthStatus(Enum):
    """Health status enumeration."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """Health check result."""
    name: str
    status: HealthStatus
    message: str
    timestamp: float
    details: Optional[Dict[str, Any]] = None


class HealthManager:
    """Manages system health checks and monitoring."""
    
    def __init__(self):
        self._health_checks: Dict[str, HealthCheck] = {}
        self._start_time = time.time()
        self._lock = threading.Lock()
        
    def add_health_check(self, name: str, status: HealthStatus, message: str, 
                        details: Optional[Dict[str, Any]] = None) -> None:
        """Add or update a health check result."""
        with self._lock:
            self._health_checks[name] = HealthCheck(
                name=name,
                status=status,
                message=message,
                timestamp=time.time(),
                details=details
            )
    
    def get_health_check(self, name: str) -> Optional[HealthCheck]:
        """Get a specific health check result."""
        with self._lock:
            return self._health_checks.get(name)
    
    def get_all_health_checks(self) -> Dict[str, HealthCheck]:
        """Get all health check results."""
        with self._lock:
            return self._health_checks.copy()
    
    def get_overall_status(self) -> HealthStatus:
        """Get the overall system health status."""
        with self._lock:
            if not self._health_checks:
                return HealthStatus.UNKNOWN
            
            statuses = [check.status for check in self._health_checks.values()]
            
            if HealthStatus.CRITICAL in statuses:
                return HealthStatus.CRITICAL
            elif HealthStatus.WARNING in statuses:
                return HealthStatus.WARNING
            elif all(status == HealthStatus.HEALTHY for status in statuses):
                return HealthStatus.HEALTHY
            else:
                return HealthStatus.UNKNOWN
    
    def get_system_uptime(self) -> float:
        """Get system uptime in seconds."""
        return time.time() - self._start_time
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get a comprehensive health summary."""
        with self._lock:
            total_checks = len(self._health_checks)
            healthy_checks = sum(1 for check in self._health_checks.values() 
                               if check.status == HealthStatus.HEALTHY)
            warning_checks = sum(1 for check in self._health_checks.values() 
                               if check.status == HealthStatus.WARNING)
            critical_checks = sum(1 for check in self._health_checks.values() 
                                if check.status == HealthStatus.CRITICAL)
            
            return {
                "overall_status": self.get_overall_status().value,
                "uptime_seconds": self.get_system_uptime(),
                "total_checks": total_checks,
                "healthy_checks": healthy_checks,
                "warning_checks": warning_checks,
                "critical_checks": critical_checks,
                "health_checks": {
                    name: {
                        "status": check.status.value,
                        "message": check.message,
                        "timestamp": check.timestamp,
                        "details": check.details
                    }
                    for name, check in self._health_checks.items()
                }
            }
    
    def clear_health_checks(self) -> None:
        """Clear all health check results."""
        with self._lock:
            self._health_checks.clear()
    
    def is_healthy(self) -> bool:
        """Check if the system is overall healthy."""
        return self.get_overall_status() in [HealthStatus.HEALTHY, HealthStatus.WARNING]
    
    def requires_attention(self) -> bool:
        """Check if the system requires attention (warning or critical)."""
        return self.get_overall_status() in [HealthStatus.WARNING, HealthStatus.CRITICAL]
    
    def get_critical_issues(self) -> list:
        """Get list of critical health issues."""
        with self._lock:
            return [
                check for check in self._health_checks.values()
                if check.status == HealthStatus.CRITICAL
            ]
    
    def get_warnings(self) -> list:
        """Get list of warning health issues."""
        with self._lock:
            return [
                check for check in self._health_checks.values()
                if check.status == HealthStatus.WARNING
            ]


# Global health manager instance
health_manager = HealthManager() 