#!/usr/bin/env python3
"""
GameForge -- Full Demo Script (Phases 1-6)
==========================================
Demonstrates all compiler phases + execution WITHOUT needing interactive input.
Run with:  python demo_all_phases.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from compiler_service import compile_source
from runtime import TACInterpreter
from ir.tac_printer import TACPrinter

DEMO_SOURCE = """\
PLAYER health = 100
PLAYER coins = 0
PLAYER score = 0

WHEN enemy_attack
    health -= 20

WHEN collect_coin
    coins += 10

WHEN player_move
    score += 5

IF health <= 0
    GAME_OVER

IF coins >= 10
    LEVEL_COMPLETE
"""

SEP = "=" * 62

def banner(title):
    print()
    print(SEP)
    print(f"  {title}")
    print(SEP)

def mini(title):
    print(f"\n  -- {title} --")

# ── Show source ────────────────────────────────────────────────────────
banner("GAMEFORGE COMPILER -- FULL DEMO (Phases 1-6)")
print("\n  Source Code:")
print("  " + "-" * 44)
for i, ln in enumerate(DEMO_SOURCE.splitlines(), 1):
    print(f"  {i:>3} | {ln}")

# ── Phases 1-4 (verbose, prints own headers) ───────────────────────────
print()
result = compile_source(DEMO_SOURCE, optimize=False, verbose=True)

# ── Phase 5 - Optimization comparison ─────────────────────────────────
banner("PHASE 5: CODE OPTIMIZATION")
result_opt = compile_source(DEMO_SOURCE, optimize=True, verbose=False)
rep = result_opt.opt_report
print(f"\n  Original instructions : {rep.original_count}")
print(f"  Optimized instructions: {rep.optimized_count}")
print(f"  Instructions removed  : {rep.instructions_removed}")
if rep.changes:
    for c in rep.changes:
        print(f"    * {c}")
else:
    print("  No optimizations applicable -- TAC remains unchanged.")
print("\n  [OK] Optimization phase complete")

# ── Phase 6 - Execution ───────────────────────────────────────────────
banner("PHASE 6: TAC INTERPRETER / EXECUTION")

interp = TACInterpreter(result.active_tac, verbose=True)
state  = interp.initialize()

events_to_trigger = [
    ("enemy_attack",  "Trigger 1: enemy_attack (health 100->80)"),
    ("collect_coin",  "Trigger 2: collect_coin (coins 0->10)"),
    ("player_move",   "Trigger 3: player_move  (score 0->5)"),
    ("enemy_attack",  "Trigger 4: enemy_attack (health 80->60)"),
    ("enemy_attack",  "Trigger 5: enemy_attack (health 60->40)"),
    ("enemy_attack",  "Trigger 6: enemy_attack (health 40->20)"),
    ("enemy_attack",  "Trigger 7: enemy_attack (health 20->0, GAME_OVER)"),
]

for event, desc in events_to_trigger:
    mini(desc)
    if state.is_terminal():
        print(f"  (game already ended: {state.status})")
        break
    interp.trigger_event(event, state)

print()
print(SEP)
print("  FINAL GAME STATE")
print(SEP)
print(state.format_state())
print(SEP)

# ── Phase 6b - Fresh runtime, trigger LEVEL_COMPLETE ──────────────────
banner("PHASE 6b: SECOND RUN -- LEVEL_COMPLETE PATH")

result2 = compile_source(DEMO_SOURCE, optimize=False, verbose=False)
interp2 = TACInterpreter(result2.active_tac, verbose=True)
state2  = interp2.initialize()

mini("Trigger: collect_coin x2 -> coins=20 -> LEVEL_COMPLETE")
interp2.trigger_event("collect_coin", state2)
interp2.trigger_event("collect_coin", state2)

print()
print(SEP)
print("  FINAL GAME STATE")
print(SEP)
print(state2.format_state())
print(SEP)

# ── Summary ────────────────────────────────────────────────────────────
banner("DEMO COMPLETE -- ALL PHASES PASSED")
print()
for ph in result.phases:
    icon = {"Passed":"[OK]","Skipped":"[SKIP]","Not Run":"[----]","Failed":"[FAIL]"}.get(ph.status,"[?]")
    print(f"  {icon} {ph.name}")
print()
print("  Run the full test suite:")
print("    python -m unittest tests.test_compiler tests.test_phases_4_6 -v")
print()
print("  Launch the compiler playground UI:")
print("    python ui/app.py")
print()
