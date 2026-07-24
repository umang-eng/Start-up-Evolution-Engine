"""Agent Mesh — Inter-agent communication bus.

Agents publish Observations to the bus; other agents subscribe to topics.
Timeouts are enforced — no infinite waits.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict

from backend.agents.types import AgentRole, Observation
from backend.core.logging import logger


class ObservationTimeoutError(Exception):
    """Raised when an agent waits too long for an observation on the bus."""
    pass


class AgentContextBus:
    """Pub/sub bus for agents to share observations within a pipeline run.

    Thread-safe via asyncio.Lock. Timeouts are required on subscribe.
    """

    def __init__(self) -> None:
        self._observations: dict[str, list[Observation]] = defaultdict(list)
        self._waiters: dict[str, list[asyncio.Event]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def publish(self, producer: AgentRole, observation: Observation) -> None:
        """Publish an observation to the bus. Wakes any waiting subscribers."""
        async with self._lock:
            self._observations[observation.topic].append(observation)

            # Wake all waiters for this topic
            for event in self._waiters.get(observation.topic, []):
                event.set()
            self._waiters[observation.topic] = []

        logger.debug(
            f"[ContextBus] Published: topic={observation.topic} "
            f"producer={producer.value}"
        )

    async def subscribe(
        self,
        subscriber: AgentRole,
        topic: str,
        timeout_s: float = 30.0,
    ) -> Observation:
        """Wait for an observation on a topic. Raises ObservationTimeoutError on timeout."""
        # Check if already published
        async with self._lock:
            existing = self._observations.get(topic, [])
            if existing:
                obs = existing[-1]
                logger.debug(
                    f"[ContextBus] {subscriber.value} got existing observation: "
                    f"topic={topic}"
                )
                return obs

        # Wait for new publication
        event = asyncio.Event()
        async with self._lock:
            self._waiters[topic].append(event)

        try:
            await asyncio.wait_for(event.wait(), timeout=timeout_s)
        except asyncio.TimeoutError:
            # Clean up waiter
            async with self._lock:
                if topic in self._waiters and event in self._waiters[topic]:
                    self._waiters[topic].remove(event)
            raise ObservationTimeoutError(
                f"Agent {subscriber.value} timed out waiting for topic '{topic}' "
                f"after {timeout_s}s"
            )

        # Return the observation
        async with self._lock:
            obs_list = self._observations.get(topic, [])
            if not obs_list:
                raise ObservationTimeoutError(
                    f"Agent {subscriber.value} woke up but no observation on topic '{topic}'"
                )
            obs = obs_list[-1]

        logger.debug(
            f"[ContextBus] {subscriber.value} received observation: topic={topic}"
        )
        return obs

    def get_all_observations(self) -> dict[str, list[Observation]]:
        """Return all published observations (for debugging / metadata)."""
        return dict(self._observations)

    def get_observations_for_topic(self, topic: str) -> list[Observation]:
        """Return all observations for a specific topic."""
        return list(self._observations.get(topic, []))

    def clear(self) -> None:
        """Clear all observations and waiters (for testing)."""
        self._observations.clear()
        self._waiters.clear()
