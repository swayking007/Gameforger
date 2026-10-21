"""
GameForge -- Platformer Package
===============================
Mario-inspired 2D platformer integrated with the GameForge compiler pipeline
and Three-Address Code (TAC) interpreter runtime.
"""

from .bridge import CompilerGameBridge
from .world import LevelWorld, create_default_world
from .entities import Player, Enemy, Coin, Platform, Goal, Particle
from .engine import PlatformerCanvas

__all__ = [
    "CompilerGameBridge",
    "LevelWorld",
    "create_default_world",
    "Player",
    "Enemy",
    "Coin",
    "Platform",
    "Goal",
    "Particle",
    "PlatformerCanvas",
]
