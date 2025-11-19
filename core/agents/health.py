"""
Agent Health Monitoring System for BuildRunner 3.2

Implements comprehensive health checks for agent pool with automatic failover detection.
This module monitors agent status, performance metrics, and resource utilization.
"""

import asyncio
import json
import time
import psutil
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set
from abc import ABC, abstractmethod


class HealthStatus(str, Enum):
    """Agent health status enumeration"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILING = "failing"
    OFFLINE = "offline"
    UNKNOWN = "unknown"


class ResourceType(str, Enum):
    """Resource types for monitoring"""
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"


@dataclass
class ResourceMetrics:
    """Resource usage metrics for an agent"""
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    memory_mb: float = 0.0
    disk_percent: float = 0.0
    network_io_sent_mb: float = 0.0
    network_io_recv_mb: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "cpu_percent": self.cpu_percent,
            "memory_percent": self.memory_percent,
            "memory_mb": self.memory_mb,
            "disk_percent": self.disk_percent,
            "network_io_sent_mb": self.network_io_sent_mb,
            "network_io_recv_mb": self.network_io_recv_mb,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class HealthCheckResult:
    """Result of a health check"""
    agent_id: str
    status: HealthStatus
    timestamp: datetime = field(default_factory=datetime.now)
    response_time_ms: float = 0.0
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    memory_mb: float = 0.0
    disk_percent: float = 0.0
    last_successful_check: Optional[datetime] = None
    consecutive_failures: int = 0
    error_message: Optional[str] = None
    healthy_endpoints: int = 0
    total_endpoints: int = 0

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        data = asdict(self)
        data["status"] = self.status.value
        data["timestamp"] = self.timestamp.isoformat()
        if self.last_successful_check:
            data["last_successful_check"] = self.last_successful_check.isoformat()
        return data


class HealthChecker(ABC):
    """Abstract base class for health checkers"""

    @abstractmethod
    async def check(self, agent_id: str) -> HealthCheckResult:
        """
        Perform health check on an agent

        Args:
            agent_id: Agent identifier

        Returns:
            Health check result
        """
        pass

    @abstractmethod
    async def is_healthy(self, agent_id: str) -> bool:
        """
        Quick health check

        Args:
            agent_id: Agent identifier

        Returns:
            True if agent is healthy
        """
        pass


class HTTPHealthChecker(HealthChecker):
    """HTTP-based health checker for agents"""

    def __init__(self, timeout: float = 5.0):
        """
        Initialize HTTP health checker

        Args:
            timeout: Health check timeout in seconds
        """
        self.timeout = timeout
        self.last_results: Dict[str, HealthCheckResult] = {}

    async def check(self, agent_id: str) -> HealthCheckResult:
        """Perform HTTP health check"""
        start_time = time.time()
        result = HealthCheckResult(
            agent_id=agent_id,
            status=HealthStatus.UNKNOWN
        )

        try:
            # Simulate HTTP health check (would use aiohttp in production)
            await asyncio.sleep(0.1)

            # Check endpoint availability
            response_time = (time.time() - start_time) * 1000

            if response_time < 5000:  # Less than 5 seconds
                result.status = HealthStatus.HEALTHY
                result.response_time_ms = response_time
                result.last_successful_check = datetime.now()
                result.consecutive_failures = 0
            elif response_time < 10000:  # Less than 10 seconds
                result.status = HealthStatus.DEGRADED
                result.response_time_ms = response_time
            else:
                result.status = HealthStatus.FAILING
                result.response_time_ms = response_time
                result.error_message = "Health check timeout"

        except Exception as e:
            result.status = HealthStatus.OFFLINE
            result.error_message = str(e)
            if agent_id in self.last_results:
                result.consecutive_failures = self.last_results[agent_id].consecutive_failures + 1

        result.timestamp = datetime.now()
        self.last_results[agent_id] = result
        return result

    async def is_healthy(self, agent_id: str) -> bool:
        """Quick health check"""
        result = await self.check(agent_id)
        return result.status in (HealthStatus.HEALTHY, HealthStatus.DEGRADED)


class ProcessHealthChecker(HealthChecker):
    """Process-based health checker for local agents"""

    def __init__(self, process_ids: Optional[Dict[str, int]] = None):
        """
        Initialize process health checker

        Args:
            process_ids: Mapping of agent IDs to process IDs
        """
        self.process_ids = process_ids or {}
        self.last_results: Dict[str, HealthCheckResult] = {}

    async def check(self, agent_id: str) -> HealthCheckResult:
        """Perform process health check"""
        result = HealthCheckResult(
            agent_id=agent_id,
            status=HealthStatus.UNKNOWN
        )

        pid = self.process_ids.get(agent_id)
        if not pid:
            result.status = HealthStatus.UNKNOWN
            result.error_message = "No process ID configured"
            return result

        try:
            process = psutil.Process(pid)

            # Check if process is running
            if not process.is_running():
                result.status = HealthStatus.OFFLINE
                result.error_message = "Process is not running"
            else:
                # Get resource metrics
                with process.oneshot():
                    cpu_percent = process.cpu_percent(interval=0.1)
                    memory_info = process.memory_info()
                    memory_percent = process.memory_percent()

                result.cpu_percent = cpu_percent
                result.memory_percent = memory_percent
                result.memory_mb = memory_info.rss / (1024 * 1024)

                # Determine health status based on resource usage
                if cpu_percent > 90 or memory_percent > 90:
                    result.status = HealthStatus.FAILING
                    result.error_message = "Resource usage critical"
                elif cpu_percent > 75 or memory_percent > 75:
                    result.status = HealthStatus.DEGRADED
                    result.error_message = "Resource usage high"
                else:
                    result.status = HealthStatus.HEALTHY

                result.last_successful_check = datetime.now()
                result.consecutive_failures = 0

        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            result.status = HealthStatus.OFFLINE
            result.error_message = f"Cannot access process: {str(e)}"
            if agent_id in self.last_results:
                result.consecutive_failures = self.last_results[agent_id].consecutive_failures + 1

        result.timestamp = datetime.now()
        self.last_results[agent_id] = result
        return result

    async def is_healthy(self, agent_id: str) -> bool:
        """Quick health check"""
        result = await self.check(agent_id)
        return result.status == HealthStatus.HEALTHY


class AgentHealthMonitor:
    """Main health monitoring system for agent pool"""

    def __init__(self, agent_ids: List[str], check_interval: float = 10.0):
        """
        Initialize agent health monitor

        Args:
            agent_ids: List of agent IDs to monitor
            check_interval: Time between health checks in seconds
        """
        self.agent_ids = agent_ids
        self.check_interval = check_interval
        self.health_checks: Dict[str, HealthCheckResult] = {}
        self.health_history: Dict[str, List[HealthCheckResult]] = {aid: [] for aid in agent_ids}
        self.http_checker = HTTPHealthChecker()
        self.process_checker = ProcessHealthChecker()
        self.is_running = False
        self.monitoring_task: Optional[asyncio.Task] = None
        self._resource_limits = {
            "cpu_percent": 85.0,
            "memory_percent": 80.0,
            "disk_percent": 90.0,
        }

    def set_resource_limits(self, **limits) -> None:
        """
        Set resource usage limits

        Args:
            **limits: Resource type and limit pairs
        """
        for key, value in limits.items():
            if key in self._resource_limits:
                self._resource_limits[key] = value

    async def start(self) -> None:
        """Start health monitoring"""
        if self.is_running:
            return

        self.is_running = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())

    async def stop(self) -> None:
        """Stop health monitoring"""
        self.is_running = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass

    async def _monitoring_loop(self) -> None:
        """Main monitoring loop"""
        while self.is_running:
            try:
                await self.check_all_agents()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                print(f"Error in monitoring loop: {e}")
                await asyncio.sleep(self.check_interval)

    async def check_all_agents(self) -> Dict[str, HealthCheckResult]:
        """
        Check health of all agents

        Returns:
            Dictionary of agent ID to health check result
        """
        tasks = [self.check_agent(agent_id) for agent_id in self.agent_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for agent_id, result in zip(self.agent_ids, results):
            if isinstance(result, Exception):
                self.health_checks[agent_id] = HealthCheckResult(
                    agent_id=agent_id,
                    status=HealthStatus.OFFLINE,
                    error_message=str(result)
                )
            else:
                self.health_checks[agent_id] = result
                self.health_history[agent_id].append(result)
                # Keep only last 100 checks
                if len(self.health_history[agent_id]) > 100:
                    self.health_history[agent_id] = self.health_history[agent_id][-100:]

        return self.health_checks

    async def check_agent(self, agent_id: str) -> HealthCheckResult:
        """
        Check health of a single agent

        Args:
            agent_id: Agent identifier

        Returns:
            Health check result
        """
        # Primary: HTTP check
        result = await self.http_checker.check(agent_id)

        # Secondary: Process check if available
        if agent_id in self.process_checker.process_ids:
            process_result = await self.process_checker.check(agent_id)
            # Merge results - use worst status
            if process_result.status.value < result.status.value:
                result = process_result

        return result

    def get_health_status(self, agent_id: str) -> Optional[HealthCheckResult]:
        """
        Get current health status of an agent

        Args:
            agent_id: Agent identifier

        Returns:
            Health check result or None
        """
        return self.health_checks.get(agent_id)

    def get_healthy_agents(self) -> List[str]:
        """
        Get list of healthy agents

        Returns:
            List of agent IDs that are healthy
        """
        return [
            aid for aid, check in self.health_checks.items()
            if check and check.status in (HealthStatus.HEALTHY, HealthStatus.DEGRADED)
        ]

    def get_failing_agents(self) -> List[str]:
        """
        Get list of failing agents

        Returns:
            List of agent IDs that are failing
        """
        return [
            aid for aid, check in self.health_checks.items()
            if check and check.status == HealthStatus.FAILING
        ]

    def get_offline_agents(self) -> List[str]:
        """
        Get list of offline agents

        Returns:
            List of agent IDs that are offline
        """
        return [
            aid for aid, check in self.health_checks.items()
            if check and check.status == HealthStatus.OFFLINE
        ]

    def get_summary(self) -> Dict:
        """
        Get health summary for all agents

        Returns:
            Health summary statistics
        """
        healthy = self.get_healthy_agents()
        failing = self.get_failing_agents()
        offline = self.get_offline_agents()

        return {
            "total_agents": len(self.agent_ids),
            "healthy": len(healthy),
            "degraded": len([a for a in healthy if self.health_checks.get(a, {}).status == HealthStatus.DEGRADED]),
            "failing": len(failing),
            "offline": len(offline),
            "healthy_agents": healthy,
            "failing_agents": failing,
            "offline_agents": offline,
            "timestamp": datetime.now().isoformat()
        }

    def get_history(self, agent_id: str, limit: int = 50) -> List[Dict]:
        """
        Get health history for an agent

        Args:
            agent_id: Agent identifier
            limit: Maximum number of historical entries

        Returns:
            List of health check results
        """
        history = self.health_history.get(agent_id, [])
        return [check.to_dict() for check in history[-limit:]]

    def is_resource_critical(self, agent_id: str) -> bool:
        """
        Check if agent has critical resource usage

        Args:
            agent_id: Agent identifier

        Returns:
            True if resources are critical
        """
        result = self.health_checks.get(agent_id)
        if not result:
            return False

        return (
            result.cpu_percent > self._resource_limits["cpu_percent"] or
            result.memory_percent > self._resource_limits["memory_percent"] or
            result.disk_percent > self._resource_limits["disk_percent"]
        )

    def detect_failover_candidates(self) -> List[str]:
        """
        Detect agents that need failover

        Returns:
            List of agent IDs that need failover
        """
        candidates = []
        for agent_id, check in self.health_checks.items():
            if check and (check.status == HealthStatus.FAILING or check.consecutive_failures > 3):
                candidates.append(agent_id)

        return candidates

    def save_state(self, filepath: Path) -> None:
        """
        Save health monitor state to file

        Args:
            filepath: Path to save state file
        """
        state = {
            "timestamp": datetime.now().isoformat(),
            "health_checks": {aid: check.to_dict() for aid, check in self.health_checks.items()},
            "summary": self.get_summary()
        }

        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w") as f:
            json.dump(state, f, indent=2)

    def load_state(self, filepath: Path) -> None:
        """
        Load health monitor state from file

        Args:
            filepath: Path to load state file
        """
        if not filepath.exists():
            return

        try:
            with open(filepath, "r") as f:
                state = json.load(f)
                # Could restore historical data here if needed
        except Exception as e:
            print(f"Error loading health state: {e}")
