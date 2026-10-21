"""
GameForge Compiler -- Runtime Package (Phase 6)
================================================
Exposes GameState and TACInterpreter.
"""

from .game_state import GameState
from .tac_interpreter import TACInterpreter

__all__ = ["GameState", "TACInterpreter"]
