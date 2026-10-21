"""
GameForge -- Platformer World & Level Design
============================================
Defines the layout of platforms, coins, enemies, obstacles, and decorative
scenery for the Mario-inspired side-scrolling platformer.
"""

from typing import List
from .entities import Player, Coin, Enemy, Platform, Goal


class LevelWorld:
    """Encapsulates all entities and scenery in a platformer level."""

    def __init__(self, width: float = 2300.0, height: float = 380.0):
        self.width = width
        self.height = height
        self.ground_y = 330.0

        self.player: Player = Player(x=60.0, y=self.ground_y - 40.0)
        self.platforms: List[Platform] = []
        self.coins: List[Coin] = []
        self.enemies: List[Enemy] = []
        self.goal: Goal = Goal(x=2050.0, y=self.ground_y)

    def reset(self):
        """Reset player and all entities to their initial state."""
        self.player.reset()
        for c in self.coins:
            c.reset()
        for e in self.enemies:
            e.reset()
        self.goal.reset()


def create_default_world() -> LevelWorld:
    """Construct the standard Mario-style level layout."""
    world = LevelWorld(width=2300.0, height=380.0)
    gy = world.ground_y

    # ─────────────────────────────────────────────────────────────────
    # 1. Ground & Platforms
    # ─────────────────────────────────────────────────────────────────
    # Section 1 Ground (x: 0 -> 600)
    world.platforms.append(Platform(0.0, gy, 600.0, 50.0, kind="ground"))

    # Pit 1 is between x=600 and x=680
    world.platforms.append(Platform(620.0, gy - 60.0, 48.0, 20.0, kind="brick"))  # Stepping brick over pit 1

    # Section 2 Ground (x: 680 -> 1380)
    world.platforms.append(Platform(680.0, gy, 700.0, 50.0, kind="ground"))

    # Pit 2 is between x=1380 and x=1460
    world.platforms.append(Platform(1400.0, gy - 70.0, 48.0, 20.0, kind="question"))  # Question block over pit 2

    # Section 3 Ground (x: 1460 -> 2300)
    world.platforms.append(Platform(1460.0, gy, 840.0, 50.0, kind="ground"))

    # Elevated Blocks & Pipes — Section 1
    # Classic ? [brick] ? [brick] pattern
    world.platforms.append(Platform(180.0, gy - 90.0, 32.0, 32.0, kind="question"))
    world.platforms.append(Platform(212.0, gy - 90.0, 32.0, 32.0, kind="brick"))
    world.platforms.append(Platform(244.0, gy - 90.0, 32.0, 32.0, kind="question"))
    world.platforms.append(Platform(276.0, gy - 90.0, 32.0, 32.0, kind="brick"))

    # Pipes
    world.platforms.append(Platform(380.0, gy - 55.0, 48.0, 55.0, kind="pipe"))
    world.platforms.append(Platform(520.0, gy - 80.0, 48.0, 80.0, kind="pipe"))

    # Elevated Blocks & Pipes — Section 2
    world.platforms.append(Platform(760.0, gy - 110.0, 120.0, 24.0, kind="brick"))
    world.platforms.append(Platform(805.0, gy - 180.0, 32.0, 32.0, kind="question"))
    world.platforms.append(Platform(960.0, gy - 65.0, 48.0, 65.0, kind="pipe"))

    # Stepping pyramid
    world.platforms.append(Platform(1120.0, gy - 30.0, 32.0, 30.0, kind="brick"))
    world.platforms.append(Platform(1152.0, gy - 60.0, 32.0, 60.0, kind="brick"))
    world.platforms.append(Platform(1184.0, gy - 90.0, 64.0, 90.0, kind="brick"))
    world.platforms.append(Platform(1248.0, gy - 60.0, 32.0, 60.0, kind="brick"))
    world.platforms.append(Platform(1280.0, gy - 30.0, 32.0, 30.0, kind="brick"))

    # Elevated Blocks — Section 3
    world.platforms.append(Platform(1600.0, gy - 90.0, 32.0, 32.0, kind="question"))
    world.platforms.append(Platform(1632.0, gy - 90.0, 32.0, 32.0, kind="brick"))
    world.platforms.append(Platform(1664.0, gy - 90.0, 32.0, 32.0, kind="question"))
    world.platforms.append(Platform(1800.0, gy - 70.0, 48.0, 70.0, kind="pipe"))

    # Victory steps before flagpole
    world.platforms.append(Platform(1920.0, gy - 25.0, 28.0, 25.0, kind="brick"))
    world.platforms.append(Platform(1948.0, gy - 50.0, 28.0, 50.0, kind="brick"))
    world.platforms.append(Platform(1976.0, gy - 75.0, 28.0, 75.0, kind="brick"))

    # ─────────────────────────────────────────────────────────────────
    # 2. Collectible Coins (10 coins placed strategically)
    # ─────────────────────────────────────────────────────────────────
    world.coins.append(Coin(187.0, gy - 125.0))   # Above question block 1
    world.coins.append(Coin(251.0, gy - 125.0))   # Above question block 2
    world.coins.append(Coin(395.0, gy - 90.0))    # Above pipe 1
    world.coins.append(Coin(635.0, gy - 95.0))    # Over pit 1
    world.coins.append(Coin(785.0, gy - 145.0))   # On high brick platform
    world.coins.append(Coin(812.0, gy - 215.0))   # Above highest question block
    world.coins.append(Coin(1050.0, gy - 35.0))   # On ground
    world.coins.append(Coin(1200.0, gy - 125.0))  # At top of pyramid
    world.coins.append(Coin(1415.0, gy - 105.0))  # Over pit 2
    world.coins.append(Coin(1610.0, gy - 125.0))  # Above section 3 question block
    world.coins.append(Coin(1674.0, gy - 125.0))  # Above section 3 question block 2

    # ─────────────────────────────────────────────────────────────────
    # 3. Enemies (Goombas patrolling distinct zones)
    # ─────────────────────────────────────────────────────────────────
    # Goomba 1 (between spawn and first pipe)
    world.enemies.append(Enemy(x=310.0, y=gy - 24.0, min_x=120.0, max_x=370.0, speed=1.2))
    # Goomba 2 (between pipe 1 and pipe 2)
    world.enemies.append(Enemy(x=470.0, y=gy - 24.0, min_x=435.0, max_x=510.0, speed=1.4))
    # Goomba 3 (in section 2)
    world.enemies.append(Enemy(x=730.0, y=gy - 24.0, min_x=690.0, max_x=940.0, speed=1.5))
    # Goomba 4 (on top of pyramid)
    world.enemies.append(Enemy(x=1200.0, y=gy - 114.0, min_x=1185.0, max_x=1240.0, speed=1.0))
    # Goomba 5 (section 3 ground patrol)
    world.enemies.append(Enemy(x=1720.0, y=gy - 24.0, min_x=1500.0, max_x=1790.0, speed=1.6))

    # ─────────────────────────────────────────────────────────────────
    # 4. Goal Flagpole
    # ─────────────────────────────────────────────────────────────────
    world.goal = Goal(x=2050.0, y=gy, height=180.0)

    return world
