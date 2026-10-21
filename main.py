#!/usr/bin/env python3
"""
GameForge Compiler -- Main Driver (Phases 1-6)
===============================================
Orchestrates the full compilation + execution pipeline:

    Phase 1  ->  Lexical Analysis   (source -> tokens)
    Phase 2  ->  Syntax Analysis    (tokens -> AST)
    Phase 3  ->  Semantic Analysis  (AST -> validated symbol table)
    Phase 4  ->  TAC Generation     (AST -> Three-Address Code)
    Phase 5  ->  Optimization       (TAC -> Optimized TAC, optional)
    Phase 6  ->  TAC Execution      (TAC -> Game State)

Usage:
    python main.py                           # compile examples/basic.gs (default)
    python main.py examples/basic.gs         # compile a specific file
    python main.py examples/basic.gs -q      # quiet mode (no debug output)
    python main.py examples/basic.gs -O      # enable optimization (Phase 5)
    python main.py examples/basic.gs --run   # also execute (run events interactively)
    python main.py examples/basic.gs -O --run  # optimize then run
"""

import sys
import os

# Ensure project root is on sys.path so imports work from anywhere
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from compiler_service import compile_source, STATUS_PASSED, STATUS_SKIPPED
from runtime import TACInterpreter
from ir.tac_printer import TACPrinter


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def read_source(path: str) -> str:
    """Read a GameScript source file and return its contents."""
    if not os.path.isfile(path):
        print(f"\n  ERROR: File not found -> {path}\n")
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def print_banner(filepath: str, optimize: bool):
    print()
    print("=" * 60)
    print("  GAMEFORGE COMPILER")
    print("=" * 60)
    print(f"  Source file : {filepath}")
    print(f"  Optimization: {'ENABLED' if optimize else 'DISABLED'}")
    print()


def print_source(source: str):
    print("-" * 60)
    print("  SOURCE CODE")
    print("-" * 60)
    for i, line in enumerate(source.splitlines(), start=1):
        print(f"  {i:>3} | {line}")
    print("-" * 60)


def print_phase4(result):
    """Print Phase 4 TAC output."""
    print()
    print("=" * 60)
    print("  PHASE 4: THREE-ADDRESS CODE")
    print("=" * 60)
    print()
    print("-" * 60)
    print("  GENERATED TAC")
    print("-" * 60)
    listing = TACPrinter.format_listing(result.original_tac)
    for line in listing.splitlines():
        print(f"  {line}")
    print()
    print(f"  {TACPrinter.summary(result.original_tac)}")
    print()
    print("  PHASE 4 COMPLETE")
    print("  [OK] TAC generation successful")
    print("=" * 60)


def print_phase5(result):
    """Print Phase 5 optimization output."""
    print()
    print("=" * 60)
    print("  PHASE 5: CODE OPTIMIZATION")
    print("=" * 60)
    rep = result.opt_report
    print()
    print("-" * 60)
    print("  ORIGINAL TAC")
    print("-" * 60)
    for line in TACPrinter.format_listing(result.original_tac).splitlines():
        print(f"  {line}")
    print()
    print("-" * 60)
    print("  OPTIMIZED TAC")
    print("-" * 60)
    for line in TACPrinter.format_listing(result.optimized_tac).splitlines():
        print(f"  {line}")
    print()
    print("-" * 60)
    print("  OPTIMIZATION REPORT")
    print("-" * 60)
    print(f"  Instructions before : {rep.original_count}")
    print(f"  Instructions after  : {rep.optimized_count}")
    print(f"  Instructions removed: {rep.instructions_removed}")
    if rep.changes:
        print()
        print("  Changes:")
        for c in rep.changes:
            print(f"    * {c}")
    else:
        print()
        print("  No optimizations applicable. TAC remains unchanged.")
    print()
    print("  PHASE 5 COMPLETE")
    print("=" * 60)


def print_summary(result):
    """Print overall compilation summary."""
    print()
    print("=" * 60)
    if result.success:
        print("  COMPILATION SUCCESSFUL")
    else:
        print("  COMPILATION FAILED")
    print("=" * 60)
    for ph in result.phases:
        icon = {"Passed": "[OK]", "Failed": "[FAIL]", "Skipped": "[SKIP]",
                "Not Run": "[----]"}.get(ph.status, "[????]")
        print(f"  {icon} {ph.name}")
    if result.errors:
        print()
        for err in result.errors:
            print(f"  {err}")
    print("=" * 60)
    print()


def run_interactive(interp: TACInterpreter, state):
    """Simple interactive event trigger loop."""
    events = interp.registered_events()
    if not events:
        print("  No events registered in this program.")
        return

    print()
    print("=" * 60)
    print("  PHASE 6: INTERACTIVE EXECUTION")
    print("=" * 60)
    print()
    print("  Registered events:", ", ".join(events))
    print("  Commands: event name to trigger, 'state' to view, 'quit' to exit")
    print()

    while True:
        cmd = input("  > ").strip().lower()
        if cmd in ("quit", "exit", "q"):
            break
        if cmd == "state":
            print()
            print("  CURRENT GAME STATE")
            print("  " + "-" * 30)
            print(state.format_state())
            print()
        elif cmd in events:
            interp.trigger_event(cmd, state)
            print()
            print("  CURRENT GAME STATE")
            print("  " + "-" * 30)
            print(state.format_state())
            print()
            if state.is_terminal():
                print(f"  Game has ended: {state.status}")
                break
        else:
            print(f"  Unknown command '{cmd}'. Available: {', '.join(events)}, state, quit")


# ------------------------------------------------------------------
# Main compilation pipeline
# ------------------------------------------------------------------

def compile_file(filepath: str, verbose: bool = True, optimize: bool = False,
                 run: bool = False):
    """Run the full pipeline on *filepath*."""
    source = read_source(filepath)

    print_banner(filepath, optimize)
    if verbose:
        print_source(source)

    # Run compiler service (phases 1-5)
    result = compile_source(source, optimize=optimize, verbose=verbose)

    if not result.success:
        print()
        for err in result.errors:
            print(f"\n  {err}\n")
        print_summary(result)
        return False

    # Phase 4 terminal output (non-verbose mode prints this explicitly)
    if not verbose and result.original_tac:
        print_phase4(result)

    # Phase 5 terminal output
    if optimize and result.optimized_tac and not verbose:
        print_phase5(result)

    print_summary(result)

    # Phase 6: execution
    if run and result.active_tac:
        print()
        print("=" * 60)
        print("  PHASE 6: TAC EXECUTION")
        print("=" * 60)
        interp = TACInterpreter(result.active_tac, verbose=True)
        state = interp.initialize()
        run_interactive(interp, state)

    return result.success


# ------------------------------------------------------------------
# CLI entry point
# ------------------------------------------------------------------

def main():
    args = sys.argv[1:]

    # Determine source file
    positional = [a for a in args if not a.startswith("-")]
    if positional:
        filepath = positional[0]
    else:
        filepath = os.path.join(os.path.dirname(__file__), "examples", "basic.gs")

    verbose  = "-q" not in args and "--quiet" not in args
    optimize = "-O" in args or "--optimize" in args
    run      = "--run" in args

    compile_file(filepath, verbose=verbose, optimize=optimize, run=run)


if __name__ == "__main__":
    main()
