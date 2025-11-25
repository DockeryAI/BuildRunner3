"""
Load Balancer for BuildRunner 3.2 Agent Pool

Implements intelligent load balancing across multiple agents with fallback strategies.
Distributes work based on health, availability, capacity, and performance metrics.
"""

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Callable
from abc import ABC, abstractmethod

from .health import AgentHealthMonitor, HealthStatus


class LoadBalancingStrategy(str, Enum):
    """Load balancing strategy types"""

    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED = "weighted"
    HEALTH_AWARE = "health_aware"
    CPU_AWARE = "cpu_aware"
    RANDOM = "random"


@dataclass
class AgentCapacity:
    """Capacity information for an agent"""

    agent_id: str
    max_connections: int = 100
    current_connections: int = 0
    max_cpu_percent: float = 85.0
    max_memory_percent: float = 80.0
    weight: float = 1.0
    available: bool = True
    last_assigned: Optional[datetime] = None

    @property
    def available_connections(self) -> int:
        """Get available connection slots"""
        return max(0, self.max_connections - self.current_connections)

    @property
    def capacity_percentage(self) -> float:
        """Get capacity usage as percentage"""
        if self.max_connections == 0:
            return 0.0
        return (self.current_connections / self.max_connections) * 100

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "agent_id": self.agent_id,
            "max_connections": self.max_connections,
            "current_connections": self.current_connections,
            "available_connections": self.available_connections,
            "capacity_percentage": self.capacity_percentage,
            "max_cpu_percent": self.max_cpu_percent,
            "max_memory_percent": self.max_memory_percent,
            "weight": self.weight,
            "available": self.available,
            "last_assigned": self.last_assigned.isoformat() if self.last_assigned else None,
        }


@dataclass
class LoadBalancingRequest:
    """Load balancing request"""

    request_id: str
    task_type: str
    priority: int = 0
    required_capacity: int = 1
    affinity_agent_id: Optional[str] = None
    deadline: Optional[datetime] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "request_id": self.request_id,
            "task_type": self.task_type,
            "priority": self.priority,
            "required_capacity": self.required_capacity,
            "affinity_agent_id": self.affinity_agent_id,
            "deadline": self.deadline.isoformat() if self.deadline else None,
        }


@dataclass
class LoadBalancingDecision:
    """Result of load balancing decision"""

    request_id: str
    assigned_agent_id: str
    strategy_used: LoadBalancingStrategy
    timestamp: datetime = field(default_factory=datetime.now)
    confidence_score: float = 0.0
    alternative_agents: List[str] = field(default_factory=list)
    reason: str = ""

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "request_id": self.request_id,
            "assigned_agent_id": self.assigned_agent_id,
            "strategy_used": self.strategy_used.value,
            "timestamp": self.timestamp.isoformat(),
            "confidence_score": self.confidence_score,
            "alternative_agents": self.alternative_agents,
            "reason": self.reason,
        }


class BalancingStrategy(ABC):
    """Abstract base class for balancing strategies"""

    @abstractmethod
    async def select_agent(
        self,
        capacities: Dict[str, AgentCapacity],
        health_monitor: Optional[AgentHealthMonitor] = None,
        request: Optional[LoadBalancingRequest] = None,
    ) -> Tuple[Optional[str], float]:
        """
        Select best agent for request

        Args:
            capacities: Dictionary of agent capacities
            health_monitor: Optional health monitor
            request: Optional load balancing request

        Returns:
            Tuple of (agent_id, confidence_score)
        """
        pass


class RoundRobinStrategy(BalancingStrategy):
    """Round robin load balancing"""

    def __init__(self):
        """Initialize round robin strategy"""
        self.last_selected: Dict[str, int] = {}

    async def select_agent(
        self,
        capacities: Dict[str, AgentCapacity],
        health_monitor: Optional[AgentHealthMonitor] = None,
        request: Optional[LoadBalancingRequest] = None,
    ) -> Tuple[Optional[str], float]:
        """Select agent using round robin"""
        available = [a for a in capacities.values() if a.available and a.available_connections > 0]

        if not available:
            return None, 0.0

        # Get available agent IDs
        agent_ids = [a.agent_id for a in available]

        # Track index for this task type
        task_type = request.task_type if request else "default"
        if task_type not in self.last_selected:
            self.last_selected[task_type] = 0

        # Get next agent in rotation
        index = self.last_selected[task_type] % len(agent_ids)
        selected = agent_ids[index]

        # Update index
        self.last_selected[task_type] = (index + 1) % len(agent_ids)

        return selected, 0.7


class LeastConnectionsStrategy(BalancingStrategy):
    """Least connections load balancing"""

    async def select_agent(
        self,
        capacities: Dict[str, AgentCapacity],
        health_monitor: Optional[AgentHealthMonitor] = None,
        request: Optional[LoadBalancingRequest] = None,
    ) -> Tuple[Optional[str], float]:
        """Select agent with fewest connections"""
        available = [a for a in capacities.values() if a.available and a.available_connections > 0]

        if not available:
            return None, 0.0

        # Select agent with least connections
        selected = min(available, key=lambda a: a.current_connections)
        confidence = 1.0 - (selected.capacity_percentage / 100.0)

        return selected.agent_id, confidence


class HealthAwareStrategy(BalancingStrategy):
    """Health-aware load balancing"""

    async def select_agent(
        self,
        capacities: Dict[str, AgentCapacity],
        health_monitor: Optional[AgentHealthMonitor] = None,
        request: Optional[LoadBalancingRequest] = None,
    ) -> Tuple[Optional[str], float]:
        """Select agent considering health status"""
        if not health_monitor:
            # Fall back to least connections
            strategy = LeastConnectionsStrategy()
            return await strategy.select_agent(capacities, health_monitor, request)

        available = [a for a in capacities.values() if a.available and a.available_connections > 0]

        if not available:
            return None, 0.0

        # Score agents based on health and capacity
        scores = {}
        for agent in available:
            health = health_monitor.get_health_status(agent.agent_id)
            health_score = 1.0

            if health:
                if health.status == HealthStatus.HEALTHY:
                    health_score = 1.0
                elif health.status == HealthStatus.DEGRADED:
                    health_score = 0.7
                elif health.status == HealthStatus.FAILING:
                    health_score = 0.2
                else:
                    health_score = 0.0

            capacity_score = 1.0 - (agent.capacity_percentage / 100.0)
            combined_score = (health_score * 0.6) + (capacity_score * 0.4)
            scores[agent.agent_id] = combined_score

        if not scores:
            return None, 0.0

        # Select best scored agent
        selected = max(scores, key=scores.get)
        confidence = scores[selected]

        return selected, confidence


class CPUAwareStrategy(BalancingStrategy):
    """CPU-aware load balancing"""

    async def select_agent(
        self,
        capacities: Dict[str, AgentCapacity],
        health_monitor: Optional[AgentHealthMonitor] = None,
        request: Optional[LoadBalancingRequest] = None,
    ) -> Tuple[Optional[str], float]:
        """Select agent considering CPU usage"""
        if not health_monitor:
            return await LeastConnectionsStrategy().select_agent(
                capacities, health_monitor, request
            )

        available = [a for a in capacities.values() if a.available and a.available_connections > 0]

        if not available:
            return None, 0.0

        # Score based on CPU and capacity
        scores = {}
        for agent in available:
            health = health_monitor.get_health_status(agent.agent_id)
            cpu_score = 1.0

            if health:
                cpu_percent = health.cpu_percent
                if cpu_percent < 50:
                    cpu_score = 1.0
                elif cpu_percent < 75:
                    cpu_score = 0.8
                elif cpu_percent < 90:
                    cpu_score = 0.5
                else:
                    cpu_score = 0.1

            capacity_score = 1.0 - (agent.capacity_percentage / 100.0)
            combined_score = (cpu_score * 0.7) + (capacity_score * 0.3)
            scores[agent.agent_id] = combined_score

        if not scores:
            return None, 0.0

        selected = max(scores, key=scores.get)
        confidence = scores[selected]

        return selected, confidence


class AgentLoadBalancer:
    """Main load balancer for agent pool"""

    def __init__(
        self,
        agent_ids: List[str],
        health_monitor: Optional[AgentHealthMonitor] = None,
        strategy: LoadBalancingStrategy = LoadBalancingStrategy.HEALTH_AWARE,
    ):
        """
        Initialize load balancer

        Args:
            agent_ids: List of agent IDs
            health_monitor: Optional health monitor
            strategy: Initial load balancing strategy
        """
        self.agent_ids = agent_ids
        self.health_monitor = health_monitor
        self.current_strategy = strategy

        # Initialize capacities
        self.capacities: Dict[str, AgentCapacity] = {
            aid: AgentCapacity(agent_id=aid) for aid in agent_ids
        }

        # Load balancing strategies
        self.strategies: Dict[LoadBalancingStrategy, BalancingStrategy] = {
            LoadBalancingStrategy.ROUND_ROBIN: RoundRobinStrategy(),
            LoadBalancingStrategy.LEAST_CONNECTIONS: LeastConnectionsStrategy(),
            LoadBalancingStrategy.HEALTH_AWARE: HealthAwareStrategy(),
            LoadBalancingStrategy.CPU_AWARE: CPUAwareStrategy(),
        }

        # Request tracking
        self.decisions: List[LoadBalancingDecision] = []
        self.active_requests: Dict[str, str] = {}  # request_id -> agent_id

    async def assign_request(self, request: LoadBalancingRequest) -> LoadBalancingDecision:
        """
        Assign request to best agent

        Args:
            request: Load balancing request

        Returns:
            Load balancing decision
        """
        # Check affinity
        if request.affinity_agent_id and request.affinity_agent_id in self.agent_ids:
            capacity = self.capacities[request.affinity_agent_id]
            if capacity.available and capacity.available_connections >= request.required_capacity:
                capacity.current_connections += request.required_capacity
                capacity.last_assigned = datetime.now()

                decision = LoadBalancingDecision(
                    request_id=request.request_id,
                    assigned_agent_id=request.affinity_agent_id,
                    strategy_used=self.current_strategy,
                    confidence_score=1.0,
                    reason="Affinity assignment",
                )

                self.active_requests[request.request_id] = request.affinity_agent_id
                self.decisions.append(decision)
                return decision

        # Use current strategy
        strategy = self.strategies.get(self.current_strategy)
        if not strategy:
            strategy = self.strategies[LoadBalancingStrategy.LEAST_CONNECTIONS]

        selected_agent, confidence = await strategy.select_agent(
            self.capacities, self.health_monitor, request
        )

        if not selected_agent:
            return LoadBalancingDecision(
                request_id=request.request_id,
                assigned_agent_id="",
                strategy_used=self.current_strategy,
                confidence_score=0.0,
                reason="No available agents",
            )

        # Assign to selected agent
        capacity = self.capacities[selected_agent]
        capacity.current_connections += request.required_capacity
        capacity.last_assigned = datetime.now()

        # Get alternative agents
        alternatives = [
            a.agent_id
            for a in sorted(
                [
                    cap
                    for cap in self.capacities.values()
                    if cap.agent_id != selected_agent and cap.available
                ],
                key=lambda x: x.current_connections,
            )[:2]
        ]

        decision = LoadBalancingDecision(
            request_id=request.request_id,
            assigned_agent_id=selected_agent,
            strategy_used=self.current_strategy,
            confidence_score=confidence,
            alternative_agents=alternatives,
            reason=f"Selected via {self.current_strategy.value}",
        )

        self.active_requests[request.request_id] = selected_agent
        self.decisions.append(decision)

        # Keep only last 1000 decisions
        if len(self.decisions) > 1000:
            self.decisions = self.decisions[-1000:]

        return decision

    async def release_request(self, request_id: str, capacity_used: int = 1) -> bool:
        """
        Release request and free capacity

        Args:
            request_id: Request ID
            capacity_used: Capacity to release

        Returns:
            True if released successfully
        """
        agent_id = self.active_requests.pop(request_id, None)
        if not agent_id:
            return False

        capacity = self.capacities.get(agent_id)
        if capacity:
            capacity.current_connections = max(0, capacity.current_connections - capacity_used)
            return True

        return False

    def set_strategy(self, strategy: LoadBalancingStrategy) -> None:
        """
        Set load balancing strategy

        Args:
            strategy: Strategy to use
        """
        if strategy in self.strategies:
            self.current_strategy = strategy

    def set_agent_capacity(self, agent_id: str, max_connections: int, weight: float = 1.0) -> bool:
        """
        Set capacity for agent

        Args:
            agent_id: Agent ID
            max_connections: Maximum connections
            weight: Agent weight for weighted strategies

        Returns:
            True if set successfully
        """
        if agent_id not in self.capacities:
            return False

        capacity = self.capacities[agent_id]
        capacity.max_connections = max_connections
        capacity.weight = weight
        return True

    def set_agent_available(self, agent_id: str, available: bool) -> bool:
        """
        Set agent availability

        Args:
            agent_id: Agent ID
            available: Availability status

        Returns:
            True if set successfully
        """
        if agent_id not in self.capacities:
            return False

        self.capacities[agent_id].available = available
        return True

    def get_agent_load(self, agent_id: str) -> Optional[Dict]:
        """
        Get current load for agent

        Args:
            agent_id: Agent ID

        Returns:
            Agent capacity and load information
        """
        capacity = self.capacities.get(agent_id)
        if not capacity:
            return None

        return {
            **capacity.to_dict(),
            "health": (
                self.health_monitor.get_health_status(agent_id).to_dict()
                if self.health_monitor
                else None
            ),
        }

    def get_load_summary(self) -> Dict:
        """
        Get summary of all agent loads

        Returns:
            Load summary for all agents
        """
        return {
            "timestamp": datetime.now().isoformat(),
            "strategy": self.current_strategy.value,
            "total_agents": len(self.agent_ids),
            "available_agents": sum(1 for c in self.capacities.values() if c.available),
            "agents": {aid: self.capacities[aid].to_dict() for aid in self.agent_ids},
            "total_connections": sum(c.current_connections for c in self.capacities.values()),
            "total_capacity": sum(c.max_connections for c in self.capacities.values()),
            "average_load_percent": (
                (sum(c.capacity_percentage for c in self.capacities.values()) / len(self.agent_ids))
                if self.agent_ids
                else 0.0
            ),
        }

    def get_decision_history(self, limit: int = 100) -> List[Dict]:
        """
        Get decision history

        Args:
            limit: Maximum decisions to return

        Returns:
            List of recent decisions
        """
        return [d.to_dict() for d in self.decisions[-limit:]]

    def save_state(self, filepath: Path) -> None:
        """
        Save load balancer state

        Args:
            filepath: Path to save state file
        """
        state = {
            "timestamp": datetime.now().isoformat(),
            "strategy": self.current_strategy.value,
            "capacities": {aid: self.capacities[aid].to_dict() for aid in self.agent_ids},
            "load_summary": self.get_load_summary(),
        }

        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w") as f:
            json.dump(state, f, indent=2)

    def load_state(self, filepath: Path) -> None:
        """
        Load load balancer state

        Args:
            filepath: Path to load state file
        """
        if not filepath.exists():
            return

        try:
            with open(filepath, "r") as f:
                state = json.load(f)
                # Restore strategy if available
                if "strategy" in state:
                    try:
                        self.current_strategy = LoadBalancingStrategy(state["strategy"])
                    except ValueError:
                        pass
        except Exception as e:
            print(f"Error loading load balancer state: {e}")
