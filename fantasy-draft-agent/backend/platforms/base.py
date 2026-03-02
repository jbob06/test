"""Abstract base class for platform connectors."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from draft_engine import DraftState, Player


class BasePlatformConnector(ABC):
    """
    Each platform connector must:
      1. connect()    — authenticate and subscribe to draft events
      2. sync_state() — pull latest picks/available players into DraftState
      3. make_pick()  — submit a pick to the platform
      4. disconnect() — clean up
    """

    @abstractmethod
    async def connect(self) -> None: ...

    @abstractmethod
    async def sync_state(self, state: "DraftState") -> None: ...

    @abstractmethod
    async def make_pick(self, player: "Player", state: "DraftState") -> None: ...

    async def disconnect(self) -> None:
        pass
