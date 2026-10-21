"""
GameForge -- Compiler-Game Bridge
=================================
Connects the platformer game engine to the GameForge compiler runtime.
Ensures that all gameplay effects (coin collection, enemy attack, movements,
and game-over / level-complete conditions) are strictly executed through
the Three-Address Code (TAC) interpreter and GameState.
"""

from typing import Callable, Dict, List, Optional, Any, Tuple
from runtime.tac_interpreter import TACInterpreter
from runtime.game_state import GameState


class CompilerGameBridge:
    """
    Bridge between the 2D platformer engine and the GameForge TAC runtime.
    Guarantees that GameState remains the sole source of truth for all
    DSL-declared variables and conditions.
    """

    def __init__(
        self,
        get_interpreter: Callable[[], Optional[TACInterpreter]],
        get_state: Callable[[], Optional[GameState]],
        is_stale_fn: Optional[Callable[[], bool]] = None,
        on_event_executed: Optional[Callable[[str, Dict[str, Tuple[int, int]], GameState, List[str]], None]] = None,
    ):
        self._get_interpreter = get_interpreter
        self._get_state = get_state
        self._is_stale_fn = is_stale_fn or (lambda: False)
        self._on_event_executed = on_event_executed

        # Event cooldowns to prevent multiple firings on the same collision frame
        self._cooldowns: Dict[str, float] = {}

    # ------------------------------------------------------------------
    # Status & Inspection
    # ------------------------------------------------------------------

    def is_ready(self) -> bool:
        """True if a valid compiled interpreter and state are active."""
        interp = self._get_interpreter()
        state = self._get_state()
        return interp is not None and state is not None and not self.is_stale()

    def is_stale(self) -> bool:
        """True if the source code was edited after the last compilation."""
        return self._is_stale_fn()

    def get_status(self) -> str:
        """Return the current game status from the authoritative GameState."""
        state = self._get_state()
        if state is None:
            return "NOT_COMPILED"
        return state.status

    def is_terminal(self) -> bool:
        """True if the game has ended (GAME_OVER or LEVEL_COMPLETE)."""
        state = self._get_state()
        if state is None:
            return False
        return state.is_terminal()

    def get_var(self, name: str, default: int = 0) -> int:
        """
        Retrieve a variable's current value directly from GameState.
        Raises no exception; falls back to default if variable is undefined.
        """
        state = self._get_state()
        if state is None or not state.contains(name):
            return default
        return state.get(name)

    def get_all_vars(self) -> Dict[str, int]:
        """Return snapshot of all variables in GameState."""
        state = self._get_state()
        if state is None:
            return {}
        return state.snapshot()

    def has_event(self, event_name: str) -> bool:
        """Check if *event_name* has a registered handler in the current TAC."""
        interp = self._get_interpreter()
        if interp is None:
            return False
        return event_name in interp.registered_events()

    def registered_events(self) -> List[str]:
        """List all events registered in the current TAC program."""
        interp = self._get_interpreter()
        if interp is None:
            return []
        return interp.registered_events()

    # ------------------------------------------------------------------
    # Event Dispatch (TAC Execution)
    # ------------------------------------------------------------------

    def trigger_event(self, event_name: str, context: str = "") -> Dict[str, Any]:
        """
        Execute the TAC handler for *event_name* using the existing TAC interpreter.
        
        Returns a dict:
            {
                "success": bool,
                "event": str,
                "changes": {var: (old_val, new_val)},
                "status": str,
                "logs": list[str],
                "message": str
            }
        """
        interp = self._get_interpreter()
        state = self._get_state()

        if interp is None or state is None:
            return {
                "success": False,
                "event": event_name,
                "changes": {},
                "status": "NOT_COMPILED",
                "logs": [],
                "message": "Cannot trigger event: compiler has not compiled code yet.",
            }

        if state.is_terminal():
            return {
                "success": False,
                "event": event_name,
                "changes": {},
                "status": state.status,
                "logs": [],
                "message": f"Game already in terminal state: {state.status}",
            }

        if not self.has_event(event_name):
            # Event is not declared in GameScript program (e.g. program has no 'WHEN collect_coin')
            return {
                "success": False,
                "event": event_name,
                "changes": {},
                "status": state.status,
                "logs": [f"Notice: event '{event_name}' is not handled in current GameScript."],
                "message": f"Event '{event_name}' not defined in program.",
            }

        prev_snap = state.snapshot()
        logs = interp.trigger_event(event_name, state)
        curr_snap = state.snapshot()

        # Compute variable changes
        changes: Dict[str, Tuple[int, int]] = {}
        for var, old_val in prev_snap.items():
            new_val = curr_snap.get(var, old_val)
            if old_val != new_val:
                changes[var] = (old_val, new_val)

        # Notify callback (UI logs, output panel, etc.)
        if self._on_event_executed:
            try:
                self._on_event_executed(event_name, changes, state, logs)
            except Exception:
                pass

        return {
            "success": True,
            "event": event_name,
            "changes": changes,
            "status": state.status,
            "logs": logs,
            "message": f"Event '{event_name}' executed successfully.",
        }

    # ------------------------------------------------------------------
    # Cooldown Management
    # ------------------------------------------------------------------

    def can_trigger(self, event_name: str, current_time: float, cooldown: float = 0.5) -> bool:
        """Check if an event is off cooldown."""
        last_time = self._cooldowns.get(event_name, -999.0)
        return (current_time - last_time) >= cooldown

    def mark_triggered(self, event_name: str, current_time: float):
        """Record the timestamp when an event was triggered."""
        self._cooldowns[event_name] = current_time

    def reset_cooldowns(self):
        """Clear all event cooldowns."""
        self._cooldowns.clear()
