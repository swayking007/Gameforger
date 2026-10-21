"""
GameForge Compiler -- Game State (Phase 6)
==========================================
A lightweight container that holds the runtime state of a GameScript program:
  * variable values (dict[str, int])
  * game status string ("RUNNING", "GAME_OVER", "LEVEL_COMPLETE")
  * execution log lines

The initial state is constructed from DECLARE instructions.
State persists across multiple event triggers (variables are NOT reset
between events).  Only Reset() restores the original initial values.
"""

from dataclasses import dataclass, field
from typing import Dict, List


class GameState:
    """Mutable runtime state for a compiled GameScript program."""

    STATUS_RUNNING        = "RUNNING"
    STATUS_GAME_OVER      = "GAME_OVER"
    STATUS_LEVEL_COMPLETE = "LEVEL_COMPLETE"

    def __init__(self):
        self._variables: Dict[str, int] = {}
        self._initial:   Dict[str, int] = {}   # saved for Reset
        self.status:     str            = self.STATUS_RUNNING
        self.log:        List[str]      = []

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def init_variable(self, name: str, value: int):
        """Declare a variable and set its initial value."""
        self._variables[name] = value
        self._initial[name]   = value

    def reset(self):
        """Restore all variables to their initial values and clear status."""
        self._variables = dict(self._initial)
        self.status     = self.STATUS_RUNNING
        self.log        = []

    # ------------------------------------------------------------------
    # Variable access
    # ------------------------------------------------------------------

    def get(self, name: str) -> int:
        """Return the current value of *name*.  Raises KeyError if unknown."""
        if name not in self._variables:
            raise KeyError(f"Runtime error: undefined variable '{name}'")
        return self._variables[name]

    def set(self, name: str, value: int):
        """Update the current value of *name*.  Raises KeyError if unknown."""
        if name not in self._variables:
            raise KeyError(f"Runtime error: undefined variable '{name}'")
        self._variables[name] = value

    def contains(self, name: str) -> bool:
        return name in self._variables

    # ------------------------------------------------------------------
    # Status helpers
    # ------------------------------------------------------------------

    def set_game_over(self):
        self.status = self.STATUS_GAME_OVER

    def set_level_complete(self):
        self.status = self.STATUS_LEVEL_COMPLETE

    def is_terminal(self) -> bool:
        """True when execution has ended (GAME_OVER or LEVEL_COMPLETE)."""
        return self.status in (self.STATUS_GAME_OVER, self.STATUS_LEVEL_COMPLETE)

    # ------------------------------------------------------------------
    # Log helpers
    # ------------------------------------------------------------------

    def append_log(self, msg: str):
        self.log.append(msg)

    def clear_log(self):
        self.log = []

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def snapshot(self) -> Dict[str, int]:
        """Return a copy of the current variable dictionary."""
        return dict(self._variables)

    def initial_snapshot(self) -> Dict[str, int]:
        """Return a copy of the initial variable dictionary."""
        return dict(self._initial)

    def all_variables(self) -> List[str]:
        """Variable names in declaration order."""
        return list(self._variables.keys())

    def format_state(self) -> str:
        """Human-readable variable listing."""
        lines = []
        for name, val in self._variables.items():
            lines.append(f"  {name} = {val}")
        lines.append(f"  status = {self.status}")
        return "\n".join(lines)

    def __repr__(self) -> str:
        return f"GameState(vars={self._variables}, status={self.status!r})"
