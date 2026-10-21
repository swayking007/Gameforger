"""
GameForge Compiler -- Extended Test Suite (Phases 4-6)
=======================================================
Tests cover TAC generation, optimization, execution and end-to-end integration.
All 29 original Phase 1-3 tests are preserved in tests/test_compiler.py.

Run with:
    python -m unittest tests.test_phases_4_6 -v
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from compiler_service import compile_source, STATUS_PASSED, STATUS_SKIPPED, STATUS_FAILED
from ir.instructions import (
    DeclareInstr, MovInstr, AddInstr, SubInstr,
    LabelInstr, GotoInstr, IfInstr, ReturnInstr, CommandInstr,
)
from runtime import TACInterpreter, GameState
from optimizer import Optimizer


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _compile(source: str, optimize: bool = False):
    return compile_source(source, optimize=optimize, verbose=False)


def _make_interp(source: str, optimize: bool = False):
    result = _compile(source, optimize=optimize)
    assert result.success, f"Compilation failed: {result.errors}"
    return TACInterpreter(result.active_tac, verbose=False), result


# ======================================================================
#  Phase 4 -- TAC Generation Tests
# ======================================================================

class TestTACGeneration(unittest.TestCase):
    """Tests for Phase 4: Three-Address Code generation."""

    # --- Variable declarations ---

    def test_declare_generates_declare_instr(self):
        r = _compile("PLAYER health = 100")
        tac = r.original_tac
        declares = [i for i in tac if isinstance(i, DeclareInstr)]
        self.assertEqual(len(declares), 1)
        self.assertEqual(declares[0].dest, "health")
        self.assertEqual(declares[0].value, 100)

    def test_two_declares(self):
        r = _compile("PLAYER health = 100\nPLAYER coins = 0")
        declares = [i for i in r.original_tac if isinstance(i, DeclareInstr)]
        self.assertEqual(len(declares), 2)
        names = [d.dest for d in declares]
        self.assertIn("health", names)
        self.assertIn("coins", names)

    def test_declare_preserves_initial_value(self):
        r = _compile("PLAYER score = 42")
        declares = [i for i in r.original_tac if isinstance(i, DeclareInstr)]
        self.assertEqual(declares[0].value, 42)

    def test_declare_zero_value(self):
        r = _compile("PLAYER coins = 0")
        declares = [i for i in r.original_tac if isinstance(i, DeclareInstr)]
        self.assertEqual(declares[0].value, 0)

    # --- Assignment operators ---

    def test_plus_assign_generates_add(self):
        src = "PLAYER coins = 0\nWHEN collect_coin\n    coins += 10"
        r = _compile(src)
        adds = [i for i in r.original_tac if isinstance(i, AddInstr)]
        self.assertEqual(len(adds), 1)
        self.assertEqual(adds[0].dest, "coins")
        self.assertEqual(adds[0].src1, "coins")
        self.assertEqual(adds[0].src2, 10)

    def test_minus_assign_generates_sub(self):
        src = "PLAYER health = 100\nWHEN enemy_attack\n    health -= 20"
        r = _compile(src)
        subs = [i for i in r.original_tac if isinstance(i, SubInstr)]
        self.assertEqual(len(subs), 1)
        self.assertEqual(subs[0].dest, "health")
        self.assertEqual(subs[0].src1, "health")
        self.assertEqual(subs[0].src2, 20)

    def test_equal_assign_generates_mov(self):
        src = "PLAYER health = 100\nWHEN enemy_attack\n    health = 50"
        r = _compile(src)
        movs = [i for i in r.original_tac if isinstance(i, MovInstr)]
        self.assertEqual(len(movs), 1)
        self.assertEqual(movs[0].dest, "health")
        self.assertEqual(movs[0].src, 50)

    # --- Event handler structure ---

    def test_event_generates_label(self):
        src = "PLAYER health = 100\nWHEN enemy_attack\n    health -= 20"
        r = _compile(src)
        labels = [i for i in r.original_tac if isinstance(i, LabelInstr)]
        label_names = [l.name for l in labels]
        self.assertIn("event_enemy_attack", label_names)

    def test_event_generates_return(self):
        src = "PLAYER health = 100\nWHEN enemy_attack\n    health -= 20"
        r = _compile(src)
        returns = [i for i in r.original_tac if isinstance(i, ReturnInstr)]
        self.assertGreaterEqual(len(returns), 1)

    def test_event_body_between_label_and_return(self):
        src = "PLAYER health = 100\nWHEN enemy_attack\n    health -= 20"
        r = _compile(src)
        tac = r.original_tac
        # Find label index
        label_idx = next(
            i for i, x in enumerate(tac)
            if isinstance(x, LabelInstr) and x.name == "event_enemy_attack"
        )
        return_idx = next(
            i for i, x in enumerate(tac)
            if isinstance(x, ReturnInstr) and i > label_idx
        )
        # Body instruction must be between them
        body = tac[label_idx + 1: return_idx]
        self.assertTrue(len(body) >= 1)
        self.assertIsInstance(body[0], SubInstr)

    def test_multiple_events_generate_multiple_labels(self):
        src = (
            "PLAYER health = 100\nPLAYER coins = 0\n"
            "WHEN enemy_attack\n    health -= 20\n"
            "WHEN collect_coin\n    coins += 10"
        )
        r = _compile(src)
        labels = {i.name for i in r.original_tac if isinstance(i, LabelInstr)}
        self.assertIn("event_enemy_attack", labels)
        self.assertIn("event_collect_coin", labels)

    # --- IF conditions ---

    def test_if_generates_if_instr(self):
        src = "PLAYER health = 100\nIF health <= 0\n    GAME_OVER"
        r = _compile(src)
        ifs = [i for i in r.original_tac if isinstance(i, IfInstr)]
        self.assertEqual(len(ifs), 1)
        self.assertEqual(ifs[0].if_opcode, "IF_LE")
        self.assertEqual(ifs[0].src1, "health")
        self.assertEqual(ifs[0].src2, 0)

    def test_if_generates_goto(self):
        src = "PLAYER health = 100\nIF health <= 0\n    GAME_OVER"
        r = _compile(src)
        gotos = [i for i in r.original_tac if isinstance(i, GotoInstr)]
        self.assertGreaterEqual(len(gotos), 1)

    def test_if_generates_two_labels(self):
        src = "PLAYER health = 100\nIF health <= 0\n    GAME_OVER"
        r = _compile(src)
        control_labels = [
            i for i in r.original_tac
            if isinstance(i, LabelInstr) and not i.name.startswith("event_")
        ]
        self.assertEqual(len(control_labels), 2)

    def test_if_labels_are_unique(self):
        src = (
            "PLAYER health = 100\nPLAYER coins = 0\n"
            "IF health <= 0\n    GAME_OVER\n"
            "IF coins >= 10\n    LEVEL_COMPLETE"
        )
        r = _compile(src)
        all_labels = [i.name for i in r.original_tac if isinstance(i, LabelInstr)]
        self.assertEqual(len(all_labels), len(set(all_labels)),
                         "Duplicate labels found!")

    def test_command_generates_command_instr(self):
        src = "PLAYER health = 100\nIF health <= 0\n    GAME_OVER"
        r = _compile(src)
        cmds = [i for i in r.original_tac if isinstance(i, CommandInstr)]
        self.assertEqual(len(cmds), 1)
        self.assertEqual(cmds[0].name, "GAME_OVER")

    def test_level_complete_command(self):
        src = "PLAYER coins = 0\nIF coins >= 10\n    LEVEL_COMPLETE"
        r = _compile(src)
        cmds = [i for i in r.original_tac if isinstance(i, CommandInstr)]
        self.assertEqual(cmds[0].name, "LEVEL_COMPLETE")

    # --- Relational operator mapping ---

    def test_ge_condition_maps_to_if_ge(self):
        src = "PLAYER coins = 0\nIF coins >= 10\n    LEVEL_COMPLETE"
        r = _compile(src)
        ifs = [i for i in r.original_tac if isinstance(i, IfInstr)]
        self.assertEqual(ifs[0].if_opcode, "IF_GE")

    def test_gt_condition_maps_to_if_gt(self):
        src = "PLAYER coins = 0\nIF coins > 10\n    LEVEL_COMPLETE"
        r = _compile(src)
        ifs = [i for i in r.original_tac if isinstance(i, IfInstr)]
        self.assertEqual(ifs[0].if_opcode, "IF_GT")

    def test_lt_condition_maps_to_if_lt(self):
        src = "PLAYER health = 100\nIF health < 10\n    GAME_OVER"
        r = _compile(src)
        ifs = [i for i in r.original_tac if isinstance(i, IfInstr)]
        self.assertEqual(ifs[0].if_opcode, "IF_LT")

    def test_eq_condition_maps_to_if_eq(self):
        src = "PLAYER health = 100\nIF health == 0\n    GAME_OVER"
        r = _compile(src)
        ifs = [i for i in r.original_tac if isinstance(i, IfInstr)]
        self.assertEqual(ifs[0].if_opcode, "IF_EQ")

    def test_ne_condition_maps_to_if_ne(self):
        src = "PLAYER health = 100\nIF health != 0\n    GAME_OVER"
        r = _compile(src)
        ifs = [i for i in r.original_tac if isinstance(i, IfInstr)]
        self.assertEqual(ifs[0].if_opcode, "IF_NE")

    def test_tac_not_generated_after_lex_error(self):
        r = _compile("PLAYER health @= 100")
        self.assertFalse(r.success)
        self.assertIsNone(r.original_tac)

    def test_tac_not_generated_after_semantic_error(self):
        r = _compile("WHEN enemy_attack\n    gems -= 20")
        self.assertFalse(r.success)
        self.assertIsNone(r.original_tac)

    def test_tac_phase_status_passed_on_success(self):
        r = _compile("PLAYER health = 100")
        tac_phase = next(p for p in r.phases if p.name == "TAC Generation")
        self.assertEqual(tac_phase.status, STATUS_PASSED)

    def test_tac_phase_status_skipped_on_lex_error(self):
        r = _compile("PLAYER health @= 100")
        tac_phase = next(p for p in r.phases if p.name == "TAC Generation")
        self.assertEqual(tac_phase.status, STATUS_SKIPPED)


# ======================================================================
#  Phase 5 -- Optimizer Tests
# ======================================================================

class TestOptimizer(unittest.TestCase):
    """Tests for Phase 5: Code Optimization."""

    def test_optimization_disabled_preserves_tac(self):
        r = _compile("PLAYER health = 100\nWHEN enemy_attack\n    health -= 20")
        self.assertIsNotNone(r.original_tac)
        self.assertIsNone(r.optimized_tac)
        self.assertIs(r.active_tac, r.original_tac)

    def test_optimization_enabled_returns_optimized_tac(self):
        r = _compile("PLAYER health = 100\nWHEN enemy_attack\n    health -= 20",
                     optimize=True)
        self.assertIsNotNone(r.optimized_tac)

    def test_remove_add_zero(self):
        # Build instructions manually to test zero-removal pass
        instrs = [AddInstr(dest="x", src1="x", src2=0)]
        opt = Optimizer(verbose=False)
        result, report = opt.optimize(instrs)
        self.assertEqual(len(result), 0)
        self.assertEqual(report.instructions_removed, 1)
        self.assertTrue(len(report.changes) >= 1)

    def test_remove_sub_zero(self):
        instrs = [SubInstr(dest="x", src1="x", src2=0)]
        opt = Optimizer(verbose=False)
        result, report = opt.optimize(instrs)
        self.assertEqual(len(result), 0)
        self.assertEqual(report.instructions_removed, 1)

    def test_constant_folding_add(self):
        instrs = [AddInstr(dest="t1", src1=10, src2=20)]
        opt = Optimizer(verbose=False)
        result, report = opt.optimize(instrs)
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], MovInstr)
        self.assertEqual(result[0].src, 30)

    def test_constant_folding_sub(self):
        instrs = [SubInstr(dest="t1", src1=50, src2=20)]
        opt = Optimizer(verbose=False)
        result, report = opt.optimize(instrs)
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], MovInstr)
        self.assertEqual(result[0].src, 30)

    def test_optimizer_does_not_remove_labels(self):
        instrs = [LabelInstr(name="event_test"), ReturnInstr()]
        opt = Optimizer(verbose=False)
        result, _ = opt.optimize(instrs)
        self.assertTrue(any(isinstance(i, LabelInstr) for i in result))
        self.assertTrue(any(isinstance(i, ReturnInstr) for i in result))

    def test_optimizer_does_not_remove_declares(self):
        instrs = [DeclareInstr(dest="health", value=100)]
        opt = Optimizer(verbose=False)
        result, _ = opt.optimize(instrs)
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], DeclareInstr)

    def test_optimizer_does_not_remove_commands(self):
        instrs = [CommandInstr(name="GAME_OVER")]
        opt = Optimizer(verbose=False)
        result, _ = opt.optimize(instrs)
        self.assertEqual(len(result), 1)

    def test_optimizer_preserves_goto(self):
        instrs = [GotoInstr(target="L1"), LabelInstr(name="L1")]
        opt = Optimizer(verbose=False)
        result, _ = opt.optimize(instrs)
        self.assertTrue(any(isinstance(i, GotoInstr) for i in result))

    def test_no_change_report_when_nothing_optimized(self):
        r = _compile("PLAYER health = 100\nWHEN enemy_attack\n    health -= 20",
                     optimize=True)
        self.assertFalse(r.opt_report.any_change)
        self.assertEqual(r.opt_report.instructions_removed, 0)

    def test_opt_phase_skipped_when_not_requested(self):
        r = _compile("PLAYER health = 100")
        opt_phase = next(p for p in r.phases if p.name == "Optimization")
        self.assertEqual(opt_phase.status, STATUS_SKIPPED)

    def test_opt_phase_passed_when_requested(self):
        r = _compile("PLAYER health = 100", optimize=True)
        opt_phase = next(p for p in r.phases if p.name == "Optimization")
        self.assertEqual(opt_phase.status, STATUS_PASSED)

    def test_optimizer_does_not_mutate_original(self):
        r = _compile(
            "PLAYER health = 100\nWHEN enemy_attack\n    health -= 20",
            optimize=True
        )
        # Original and optimized should be separate lists
        self.assertIsNot(r.original_tac, r.optimized_tac)


# ======================================================================
#  Phase 6 -- Execution Tests
# ======================================================================

class TestExecution(unittest.TestCase):
    """Tests for Phase 6: TAC Interpreter / Execution Engine."""

    _BASIC = (
        "PLAYER health = 100\n"
        "PLAYER coins = 0\n"
        "WHEN enemy_attack\n"
        "    health -= 20\n"
        "WHEN collect_coin\n"
        "    coins += 10\n"
        "IF health <= 0\n"
        "    GAME_OVER\n"
    )

    def _build(self, source=None):
        s = source or self._BASIC
        interp, result = _make_interp(s)
        state = interp.initialize()
        return interp, state

    # --- Initial state ---

    def test_initial_health_value(self):
        _, state = self._build()
        self.assertEqual(state.get("health"), 100)

    def test_initial_coins_value(self):
        _, state = self._build()
        self.assertEqual(state.get("coins"), 0)

    def test_initial_status_running(self):
        _, state = self._build()
        self.assertEqual(state.status, GameState.STATUS_RUNNING)

    # --- Event registration ---

    def test_events_registered(self):
        interp, _ = _make_interp(self._BASIC)
        interp.initialize()   # builds the label/event registry
        events = interp.registered_events()
        self.assertIn("enemy_attack", events)
        self.assertIn("collect_coin", events)

    def test_events_not_registered_when_not_in_source(self):
        src = "PLAYER health = 100\nWHEN enemy_attack\n    health -= 20"
        interp, _ = _make_interp(src)
        interp.initialize()
        self.assertNotIn("collect_coin", interp.registered_events())

    # --- Triggering events ---

    def test_enemy_attack_reduces_health(self):
        interp, state = self._build()
        interp.trigger_event("enemy_attack", state)
        self.assertEqual(state.get("health"), 80)

    def test_collect_coin_increases_coins(self):
        interp, state = self._build()
        interp.trigger_event("collect_coin", state)
        self.assertEqual(state.get("coins"), 10)

    def test_repeated_events_accumulate(self):
        interp, state = self._build()
        interp.trigger_event("enemy_attack", state)
        interp.trigger_event("enemy_attack", state)
        interp.trigger_event("enemy_attack", state)
        # 100 - 20*3 = 40
        self.assertEqual(state.get("health"), 40)

    def test_state_persists_between_events(self):
        interp, state = self._build()
        interp.trigger_event("collect_coin", state)  # coins = 10
        interp.trigger_event("collect_coin", state)  # coins = 20
        self.assertEqual(state.get("coins"), 20)

    def test_collect_then_attack_independent(self):
        interp, state = self._build()
        interp.trigger_event("collect_coin", state)   # coins = 10
        interp.trigger_event("enemy_attack", state)   # health = 80
        self.assertEqual(state.get("coins"), 10)
        self.assertEqual(state.get("health"), 80)

    # --- MOV assignment ---

    def test_mov_assignment(self):
        src = "PLAYER health = 100\nWHEN enemy_attack\n    health = 50"
        interp, state = _make_interp(src)[0], _make_interp(src)[0].initialize()
        interp2, _ = _make_interp(src)
        state2 = interp2.initialize()
        interp2.trigger_event("enemy_attack", state2)
        self.assertEqual(state2.get("health"), 50)

    # --- IF conditions ---

    def test_game_over_triggered_when_health_zero(self):
        src = (
            "PLAYER health = 20\n"
            "WHEN enemy_attack\n    health -= 20\n"
            "IF health <= 0\n    GAME_OVER\n"
        )
        interp, state = _make_interp(src)
        interp2, state2 = _make_interp(src)
        state2 = interp2.initialize()
        interp2.trigger_event("enemy_attack", state2)
        self.assertEqual(state2.status, GameState.STATUS_GAME_OVER)

    def test_game_over_not_triggered_when_health_positive(self):
        interp, state = self._build()
        interp.trigger_event("enemy_attack", state)
        self.assertNotEqual(state.status, GameState.STATUS_GAME_OVER)

    def test_level_complete_triggered(self):
        src = (
            "PLAYER coins = 0\n"
            "WHEN collect_coin\n    coins += 10\n"
            "IF coins >= 10\n    LEVEL_COMPLETE\n"
        )
        interp, state = _make_interp(src)
        state = interp.initialize()
        interp.trigger_event("collect_coin", state)
        self.assertEqual(state.status, GameState.STATUS_LEVEL_COMPLETE)

    def test_if_false_does_not_execute_body(self):
        interp, state = self._build()
        # health starts at 100, condition is health <= 0 (false), no GAME_OVER
        self.assertEqual(state.status, GameState.STATUS_RUNNING)

    # --- Runtime state management ---

    def test_reset_restores_initial_values(self):
        interp, state = self._build()
        interp.trigger_event("enemy_attack", state)  # health = 80
        state.reset()
        self.assertEqual(state.get("health"), 100)
        self.assertEqual(state.get("coins"), 0)

    def test_reset_clears_status(self):
        src = (
            "PLAYER health = 20\n"
            "WHEN enemy_attack\n    health -= 20\n"
            "IF health <= 0\n    GAME_OVER\n"
        )
        interp, state = _make_interp(src)
        state = interp.initialize()
        interp.trigger_event("enemy_attack", state)
        state.reset()
        self.assertEqual(state.status, GameState.STATUS_RUNNING)

    def test_unknown_event_handled_gracefully(self):
        interp, state = self._build()
        # Should not raise; appends an error log
        interp.trigger_event("nonexistent_event", state)
        # State should still be intact
        self.assertEqual(state.get("health"), 100)

    # --- GameState helpers ---

    def test_game_state_snapshot(self):
        interp, state = self._build()
        snap = state.snapshot()
        self.assertIsInstance(snap, dict)
        self.assertIn("health", snap)
        self.assertEqual(snap["health"], 100)

    def test_game_state_is_terminal_false_initially(self):
        interp, state = self._build()
        self.assertFalse(state.is_terminal())

    def test_game_state_is_terminal_after_game_over(self):
        src = (
            "PLAYER health = 20\n"
            "WHEN enemy_attack\n    health -= 20\n"
            "IF health <= 0\n    GAME_OVER\n"
        )
        interp, state = _make_interp(src)
        state = interp.initialize()
        interp.trigger_event("enemy_attack", state)
        self.assertTrue(state.is_terminal())


# ======================================================================
#  End-to-End Integration Tests
# ======================================================================

class TestEndToEnd(unittest.TestCase):
    """End-to-end tests covering the full pipeline."""

    def test_valid_source_passes_all_phases(self):
        r = _compile(
            "PLAYER health = 100\nPLAYER coins = 0\n"
            "WHEN enemy_attack\n    health -= 20\n"
            "WHEN collect_coin\n    coins += 10\n"
            "IF health <= 0\n    GAME_OVER\n"
        )
        self.assertTrue(r.success)

    def test_lexical_error_stops_compilation(self):
        r = _compile("PLAYER health @= 100")
        self.assertFalse(r.success)
        lex = next(p for p in r.phases if p.name == "Lexical Analysis")
        self.assertEqual(lex.status, STATUS_FAILED)

    def test_syntax_error_stops_compilation(self):
        r = _compile("PLAYER = 100")
        self.assertFalse(r.success)
        syn = next(p for p in r.phases if p.name == "Syntax Analysis")
        self.assertEqual(syn.status, STATUS_FAILED)

    def test_semantic_error_stops_compilation(self):
        r = _compile("WHEN enemy_attack\n    gems -= 20")
        self.assertFalse(r.success)
        sem = next(p for p in r.phases if p.name == "Semantic Analysis")
        self.assertEqual(sem.status, STATUS_FAILED)

    def test_tac_not_generated_after_failure(self):
        r = _compile("PLAYER = 100")
        self.assertIsNone(r.original_tac)

    def test_optimized_tac_same_result_as_original(self):
        src = (
            "PLAYER health = 100\nPLAYER coins = 0\n"
            "WHEN enemy_attack\n    health -= 20\n"
            "WHEN collect_coin\n    coins += 10\n"
            "IF health <= 0\n    GAME_OVER\n"
        )
        # Run with and without optimization; results should be the same
        r_orig = _compile(src, optimize=False)
        r_opt  = _compile(src, optimize=True)

        interp_o = TACInterpreter(r_orig.active_tac, verbose=False)
        state_o  = interp_o.initialize()
        interp_o.trigger_event("enemy_attack", state_o)

        interp_opt = TACInterpreter(r_opt.active_tac, verbose=False)
        state_opt  = interp_opt.initialize()
        interp_opt.trigger_event("enemy_attack", state_opt)

        self.assertEqual(state_o.snapshot(), state_opt.snapshot())

    def test_error_list_populated_on_failure(self):
        r = _compile("PLAYER health @= 100")
        self.assertTrue(len(r.errors) > 0)

    def test_token_rows_returned_on_success(self):
        r = _compile("PLAYER health = 100")
        rows = r.token_rows()
        self.assertIsInstance(rows, list)
        self.assertGreater(len(rows), 0)

    def test_symbol_table_rows_returned_on_success(self):
        r = _compile("PLAYER health = 100\nPLAYER coins = 0")
        rows = r.symbol_table_rows()
        self.assertEqual(len(rows), 2)
        names = [row["name"] for row in rows]
        self.assertIn("health", names)

    def test_tac_listing_string_nonempty(self):
        r = _compile("PLAYER health = 100")
        listing = r.tac_listing()
        self.assertIn("DECLARE", listing)
        self.assertIn("health", listing)


if __name__ == "__main__":
    unittest.main()
