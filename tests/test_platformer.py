"""
GameForge -- Platformer & Compiler-Bridge Test Suite
===================================================
Tests the integration between the platformer game engine, the CompilerGameBridge,
and the GameForge Three-Address Code (TAC) interpreter runtime.
"""

import unittest
from compiler_service import compile_source
from runtime.tac_interpreter import TACInterpreter
from runtime.game_state import GameState
from platformer.bridge import CompilerGameBridge
from platformer.world import create_default_world, LevelWorld
from platformer.entities import Player, Enemy, Coin, Platform, Goal


class TestCompilerGameBridge(unittest.TestCase):
    """Verify that the bridge accurately proxies game actions to the TAC runtime."""

    def setUp(self):
        self.src = """\
PLAYER health = 100
PLAYER coins = 0
PLAYER score = 0

WHEN collect_coin
    coins += 10
    score += 50

WHEN enemy_attack
    health -= 25

WHEN player_move
    score += 1

IF health <= 0
    GAME_OVER

IF coins >= 30
    LEVEL_COMPLETE
"""
        self.result = compile_source(self.src, optimize=False, verbose=False)
        self.assertTrue(self.result.success)
        self.interp = TACInterpreter(self.result.active_tac, verbose=False)
        self.state = self.interp.initialize()
        self.is_stale = False
        self.event_log = []

        def on_event(event_name, changes, state, logs):
            self.event_log.append((event_name, changes, state.status))

        self.bridge = CompilerGameBridge(
            get_interpreter=lambda: self.interp,
            get_state=lambda: self.state,
            is_stale_fn=lambda: self.is_stale,
            on_event_executed=on_event,
        )

    def test_bridge_is_ready(self):
        self.assertTrue(self.bridge.is_ready())
        self.assertEqual(self.bridge.get_status(), "RUNNING")
        self.assertEqual(self.bridge.get_var("health"), 100)
        self.assertEqual(self.bridge.get_var("coins"), 0)
        self.assertEqual(self.bridge.get_var("score"), 0)

    def test_bridge_stale_detection(self):
        self.is_stale = True
        self.assertTrue(self.bridge.is_stale())
        self.assertFalse(self.bridge.is_ready())

    def test_collect_coin_executes_tac(self):
        res = self.bridge.trigger_event("collect_coin")
        self.assertTrue(res["success"])
        self.assertEqual(self.bridge.get_var("coins"), 10)
        self.assertEqual(self.bridge.get_var("score"), 50)
        self.assertIn("coins", res["changes"])
        self.assertEqual(res["changes"]["coins"], (0, 10))
        self.assertEqual(res["changes"]["score"], (0, 50))
        self.assertEqual(len(self.event_log), 1)

    def test_enemy_attack_reduces_health(self):
        res = self.bridge.trigger_event("enemy_attack")
        self.assertTrue(res["success"])
        self.assertEqual(self.bridge.get_var("health"), 75)
        self.assertEqual(res["changes"]["health"], (100, 75))

    def test_health_depletion_triggers_game_over(self):
        # 4 enemy attacks = 4 * 25 = 100 dmg -> health = 0
        for _ in range(4):
            self.bridge.trigger_event("enemy_attack")

        self.assertEqual(self.bridge.get_var("health"), 0)
        self.assertEqual(self.bridge.get_status(), GameState.STATUS_GAME_OVER)
        self.assertTrue(self.bridge.is_terminal())

        # Further events should be rejected in terminal state
        res = self.bridge.trigger_event("collect_coin")
        self.assertFalse(res["success"])
        self.assertIn("terminal state", res["message"])

    def test_coins_threshold_triggers_level_complete(self):
        # 3 coins = 30 coins -> triggers IF coins >= 30 LEVEL_COMPLETE
        for _ in range(3):
            self.bridge.trigger_event("collect_coin")

        self.assertEqual(self.bridge.get_var("coins"), 30)
        self.assertEqual(self.bridge.get_status(), GameState.STATUS_LEVEL_COMPLETE)
        self.assertTrue(self.bridge.is_terminal())

    def test_unhandled_event_gracefully_rejected(self):
        res = self.bridge.trigger_event("non_existent_event")
        self.assertFalse(res["success"])
        self.assertIn("not defined", res["message"])

    def test_reset_restores_initial_values(self):
        self.bridge.trigger_event("collect_coin")
        self.bridge.trigger_event("enemy_attack")
        self.assertEqual(self.bridge.get_var("coins"), 10)
        self.assertEqual(self.bridge.get_var("health"), 75)

        self.state.reset()
        self.assertEqual(self.bridge.get_var("coins"), 0)
        self.assertEqual(self.bridge.get_var("health"), 100)
        self.assertEqual(self.bridge.get_status(), GameState.STATUS_RUNNING)

    def test_cooldown_mechanism(self):
        self.assertTrue(self.bridge.can_trigger("enemy_attack", 10.0, cooldown=1.0))
        self.bridge.mark_triggered("enemy_attack", 10.0)
        # Immediately after, should be on cooldown
        self.assertFalse(self.bridge.can_trigger("enemy_attack", 10.5, cooldown=1.0))
        # After cooldown duration, ready again
        self.assertTrue(self.bridge.can_trigger("enemy_attack", 11.1, cooldown=1.0))


class TestPlatformerEntities(unittest.TestCase):
    """Test player physics, enemy logic, and level world construction."""

    def setUp(self):
        self.world = create_default_world()

    def test_world_initialization(self):
        self.assertGreater(len(self.world.platforms), 5)
        self.assertGreaterEqual(len(self.world.coins), 10)
        self.assertGreaterEqual(len(self.world.enemies), 5)
        self.assertIsNotNone(self.world.player)
        self.assertIsNotNone(self.world.goal)

    def test_player_jump(self):
        player = self.world.player
        player.grounded = True
        player.jump(jump_speed=10.0)
        self.assertEqual(player.vy, -10.0)
        self.assertFalse(player.grounded)

    def test_player_take_hit(self):
        player = self.world.player
        player.take_hit(knockback_x=5.0)
        self.assertGreater(player.hurt_timer, 0.0)
        self.assertEqual(player.vx, 5.0)
        self.assertEqual(player.vy, -6.0)

    def test_player_death(self):
        player = self.world.player
        player.die()
        self.assertTrue(player.is_dead)
        self.assertEqual(player.vy, -10.0)

    def test_enemy_patrol_movement(self):
        enemy = Enemy(x=100.0, y=300.0, min_x=90.0, max_x=120.0, speed=2.0)
        self.assertEqual(enemy.vx, -2.0)
        enemy.update(dt=0.1)
        self.assertLess(enemy.x, 100.0)
        # Advance until hitting min_x boundary
        for _ in range(10):
            enemy.update(dt=0.1)
        self.assertGreater(enemy.vx, 0.0)  # Reversed direction

    def test_enemy_squish(self):
        enemy = Enemy(x=100.0, y=300.0, min_x=90.0, max_x=120.0)
        enemy.squish()
        self.assertTrue(enemy.squished)
        self.assertFalse(enemy.alive)
        self.assertEqual(enemy.vx, 0.0)

    def test_world_reset(self):
        player = self.world.player
        player.x = 800.0
        player.die()
        coin = self.world.coins[0]
        coin.collected = True
        enemy = self.world.enemies[0]
        enemy.squish()

        self.world.reset()
        self.assertEqual(player.x, player.spawn_x)
        self.assertFalse(player.is_dead)
        self.assertFalse(coin.collected)
        self.assertTrue(enemy.alive)
        self.assertFalse(enemy.squished)


if __name__ == "__main__":
    unittest.main()
