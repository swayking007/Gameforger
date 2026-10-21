"""
GameForge Compiler -- Compiler Service
=======================================
Single entry point for the entire compilation pipeline.
Used by both the CLI driver (main.py) and the UI (ui/app.py).

compile_source(source, optimize=False)
---------------------------------------
Runs:
  1. Lexical Analysis
  2. Syntax Analysis
  3. Semantic Analysis
  4. TAC Generation
  5. Optional Optimization

Returns a CompilationResult dataclass.

The runtime (Phase 6) is kept separate so the user can inspect TAC before
triggering events.  Create a TACInterpreter from result.active_tac to execute.
"""

import sys
import os
from dataclasses import dataclass, field
from typing import Optional

# Ensure project root is importable when this module is imported directly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lexer import Lexer
from parser import Parser
from parser.ast_nodes import ProgramNode
from semantic import SemanticAnalyzer
from semantic.symbol_table import SymbolTable
from ir import TACGenerator
from ir.instructions import Instruction
from ir.tac_printer import TACPrinter
from optimizer import Optimizer
from optimizer.optimizer import OptimizationReport
from errors.errors import (
    LexicalError, SyntaxError as GFSyntaxError, SemanticError,
)


# ------------------------------------------------------------------
# Phase status constants
# ------------------------------------------------------------------

STATUS_NOT_RUN = "Not Run"
STATUS_RUNNING = "Running"
STATUS_PASSED  = "Passed"
STATUS_FAILED  = "Failed"
STATUS_SKIPPED = "Skipped"


@dataclass
class PhaseStatus:
    name:    str
    status:  str  = STATUS_NOT_RUN
    message: str  = ""


@dataclass
class CompilationResult:
    """
    Complete output of a compile_source() call.

    Attributes
    ----------
    success         True if all required phases passed.
    source          The original source code string.
    tokens          Token list from Phase 1 (may be empty on lex error).
    ast             AST root node from Phase 2 (None on parse/lex error).
    symbol_table    SymbolTable from Phase 3 (None on semantic/earlier error).
    original_tac    TAC instruction list from Phase 4 (None on earlier error).
    optimized_tac   Optimized TAC (None if optimization was skipped or failed).
    opt_report      OptimizationReport (None if optimization was skipped).
    active_tac      The TAC to execute: optimized_tac if available, else original_tac.
    phases          List of PhaseStatus records, one per compiler phase.
    errors          List of error message strings (one per failed phase).
    optimize        Whether optimization was requested.
    """
    success:        bool                         = False
    source:         str                          = ""
    tokens:         list                         = field(default_factory=list)
    ast:            Optional[ProgramNode]        = None
    symbol_table:   Optional[SymbolTable]        = None
    original_tac:   Optional[list[Instruction]]  = None
    optimized_tac:  Optional[list[Instruction]]  = None
    opt_report:     Optional[OptimizationReport] = None
    active_tac:     Optional[list[Instruction]]  = None
    phases:         list                         = field(default_factory=list)
    errors:         list[str]                    = field(default_factory=list)
    optimize:       bool                         = False

    def tac_listing(self, use_optimized: bool = False) -> str:
        """Return the numbered TAC listing string."""
        tac = self.optimized_tac if (use_optimized and self.optimized_tac) else self.original_tac
        if tac is None:
            return "(TAC not available)"
        return TACPrinter.format_listing(tac)

    def symbol_table_rows(self) -> list[dict]:
        """Return symbol table as list of dicts for UI display."""
        if self.symbol_table is None:
            return []
        return [
            {
                "name":  sym.name,
                "type":  sym.var_type,
                "value": sym.value,
                "line":  sym.line,
            }
            for sym in self.symbol_table.all_symbols()
        ]

    def token_rows(self) -> list[dict]:
        """Return token list as list of dicts for UI display."""
        return [
            {
                "index":  i,
                "type":   tok.type.name,
                "value":  tok.value,
                "line":   tok.line,
                "column": tok.column,
            }
            for i, tok in enumerate(self.tokens, start=1)
        ]


# ------------------------------------------------------------------
# Main pipeline function
# ------------------------------------------------------------------

def compile_source(
    source: str,
    optimize: bool = False,
    verbose: bool = False,
) -> CompilationResult:
    """
    Run the full GameForge compilation pipeline on *source*.

    Parameters
    ----------
    source   : GameScript source code string
    optimize : if True, run Phase 5 (optimizer) after TAC generation
    verbose  : if True, print debug output from each compiler phase

    Returns
    -------
    CompilationResult
    """
    result = CompilationResult(source=source, optimize=optimize)

    # Set up phase tracking
    phases = [
        PhaseStatus("Lexical Analysis"),
        PhaseStatus("Syntax Analysis"),
        PhaseStatus("Semantic Analysis"),
        PhaseStatus("TAC Generation"),
        PhaseStatus("Optimization"),
        PhaseStatus("Execution"),
    ]
    result.phases = phases

    # Alias for brevity
    p = {ph.name: ph for ph in phases}

    # ------------------------------------------------------------------
    # Phase 1: Lexical Analysis
    # ------------------------------------------------------------------
    p["Lexical Analysis"].status = STATUS_RUNNING
    try:
        lexer = Lexer(source, verbose=verbose)
        result.tokens = lexer.tokenize()
        p["Lexical Analysis"].status = STATUS_PASSED
    except LexicalError as e:
        p["Lexical Analysis"].status = STATUS_FAILED
        p["Lexical Analysis"].message = str(e)
        result.errors.append(str(e))
        _mark_remaining_skipped(phases, from_index=1)
        return result

    # ------------------------------------------------------------------
    # Phase 2: Syntax Analysis
    # ------------------------------------------------------------------
    p["Syntax Analysis"].status = STATUS_RUNNING
    try:
        parser = Parser(result.tokens, verbose=verbose)
        result.ast = parser.parse()
        p["Syntax Analysis"].status = STATUS_PASSED
    except GFSyntaxError as e:
        p["Syntax Analysis"].status = STATUS_FAILED
        p["Syntax Analysis"].message = str(e)
        result.errors.append(str(e))
        _mark_remaining_skipped(phases, from_index=2)
        return result

    # ------------------------------------------------------------------
    # Phase 3: Semantic Analysis
    # ------------------------------------------------------------------
    p["Semantic Analysis"].status = STATUS_RUNNING
    try:
        analyzer = SemanticAnalyzer(verbose=verbose)
        result.symbol_table = analyzer.analyze(result.ast)
        p["Semantic Analysis"].status = STATUS_PASSED
    except SemanticError as e:
        p["Semantic Analysis"].status = STATUS_FAILED
        p["Semantic Analysis"].message = str(e)
        result.errors.append(str(e))
        _mark_remaining_skipped(phases, from_index=3)
        return result

    # ------------------------------------------------------------------
    # Phase 4: TAC Generation
    # ------------------------------------------------------------------
    p["TAC Generation"].status = STATUS_RUNNING
    try:
        gen = TACGenerator(verbose=verbose)
        result.original_tac = gen.generate(result.ast)
        result.active_tac   = result.original_tac
        p["TAC Generation"].status = STATUS_PASSED
    except Exception as e:
        p["TAC Generation"].status = STATUS_FAILED
        p["TAC Generation"].message = str(e)
        result.errors.append(f"TAC Generation error: {e}")
        _mark_remaining_skipped(phases, from_index=4)
        return result

    # ------------------------------------------------------------------
    # Phase 5: Optimization (optional)
    # ------------------------------------------------------------------
    if optimize:
        p["Optimization"].status = STATUS_RUNNING
        try:
            opt = Optimizer(verbose=verbose)
            result.optimized_tac, result.opt_report = opt.optimize(
                result.original_tac
            )
            result.active_tac = result.optimized_tac
            p["Optimization"].status = STATUS_PASSED
        except Exception as e:
            p["Optimization"].status = STATUS_FAILED
            p["Optimization"].message = str(e)
            result.errors.append(f"Optimization error: {e}")
            # Non-fatal -- continue with original TAC
            result.active_tac = result.original_tac
    else:
        p["Optimization"].status = STATUS_SKIPPED

    # ------------------------------------------------------------------
    # Execution phase status (set to PASSED once actually run by caller)
    # ------------------------------------------------------------------
    p["Execution"].status = STATUS_NOT_RUN

    result.success = True
    return result


# ------------------------------------------------------------------
# Helper
# ------------------------------------------------------------------

def _mark_remaining_skipped(phases: list[PhaseStatus], from_index: int):
    for ph in phases[from_index:]:
        if ph.status == STATUS_NOT_RUN:
            ph.status = STATUS_SKIPPED
