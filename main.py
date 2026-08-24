#!/usr/bin/env python3
"""
GameForge Compiler -- Main Driver
==================================
Orchestrates the three-phase compilation pipeline:

    Phase 1  ->  Lexical Analysis   (source -> tokens)
    Phase 2  ->  Syntax Analysis    (tokens -> AST)
    Phase 3  ->  Semantic Analysis  (AST -> validated symbol table)

Usage:
    python main.py                          # compile examples/basic.gs (default)
    python main.py examples/basic.gs       # compile a specific file
    python main.py examples/basic.gs -q    # quiet mode (no debug output)
"""

import sys
import os

# Ensure project root is on sys.path so imports work from anywhere
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lexer import Lexer
from parser import Parser
from semantic import SemanticAnalyzer
from errors.errors import LexicalError, SyntaxError as GFSyntaxError, SemanticError


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


def print_banner(filepath: str):
    print()
    print("=" * 60)
    print("  GAMEFORGE COMPILER")
    print("=" * 60)
    print(f"  Source file : {filepath}")
    print()


def print_source(source: str):
    print("-" * 60)
    print("  SOURCE CODE")
    print("-" * 60)
    for i, line in enumerate(source.splitlines(), start=1):
        print(f"  {i:>3} | {line}")
    print("-" * 60)


def print_success():
    print()
    print("=" * 60)
    print("  COMPILATION SUCCESSFUL")
    print("=" * 60)
    print()
    print("  [OK] Phase 1 -- Lexical Analysis")
    print("  [OK] Phase 2 -- Syntax Analysis")
    print("  [OK] Phase 3 -- Semantic Analysis")
    print()
    print("  Phases 1-3 completed successfully.")
    print("  (IR / Optimization / Execution belong to future phases.)")
    print("=" * 60)
    print()


def print_failure(phase1: bool, phase2: bool, phase3: bool):
    print()
    print("=" * 60)
    print("  COMPILATION FAILED")
    print("=" * 60)
    print(f"  Phase 1 {'[OK]' if phase1 else '[FAIL]'}")
    print(f"  Phase 2 {'[OK]' if phase2 else '[FAIL]'}")
    print(f"  Phase 3 {'[OK]' if phase3 else '[FAIL]'}")
    print("=" * 60)
    print()


# ------------------------------------------------------------------
# Main compilation pipeline
# ------------------------------------------------------------------

def compile_file(filepath: str, verbose: bool = True):
    """Run the full Phase 1-3 pipeline on *filepath*."""
    source = read_source(filepath)

    print_banner(filepath)
    if verbose:
        print_source(source)

    phase1_ok = False
    phase2_ok = False
    phase3_ok = False

    # -- Phase 1: Lexical Analysis ----------------------------------
    try:
        lexer = Lexer(source, verbose=verbose)
        tokens = lexer.tokenize()
        phase1_ok = True
    except LexicalError as e:
        print(f"\n  {e}\n")
        print_failure(phase1_ok, phase2_ok, phase3_ok)
        return False

    # -- Phase 2: Syntax Analysis -----------------------------------
    try:
        parser = Parser(tokens, verbose=verbose)
        ast = parser.parse()
        phase2_ok = True
    except GFSyntaxError as e:
        print(f"\n  {e}\n")
        print_failure(phase1_ok, phase2_ok, phase3_ok)
        return False

    # -- Phase 3: Semantic Analysis ---------------------------------
    try:
        analyzer = SemanticAnalyzer(verbose=verbose)
        symbol_table = analyzer.analyze(ast)
        phase3_ok = True
    except SemanticError as e:
        print(f"\n  {e}\n")
        print_failure(phase1_ok, phase2_ok, phase3_ok)
        return False

    print_success()
    return True


# ------------------------------------------------------------------
# CLI entry point
# ------------------------------------------------------------------

def main():
    # Determine source file
    if len(sys.argv) >= 2 and not sys.argv[1].startswith("-"):
        filepath = sys.argv[1]
    else:
        filepath = os.path.join(os.path.dirname(__file__), "examples", "basic.gs")

    # Quiet mode?
    verbose = "-q" not in sys.argv and "--quiet" not in sys.argv

    compile_file(filepath, verbose=verbose)


if __name__ == "__main__":
    main()
