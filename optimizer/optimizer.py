"""
GameForge Compiler -- TAC Optimizer (Phase 5)
=============================================

This module implements a small, safe set of peephole optimizations over
the TAC instruction list.  Optimization is ALWAYS OPTIONAL -- the compiler
works correctly with or without it.

Implemented passes (applied in order)
--------------------------------------
1. Remove-Zero-Operations
   ADD dest, src, 0  ->  removed  (adding zero is a no-op)
   SUB dest, src, 0  ->  removed  (subtracting zero is a no-op)

2. Constant Folding
   If src1 and src2 in ADD / SUB are both integer literals,
   compute the result at compile time and replace with a MOV instruction.
   Example:
       ADD t1, 10, 20  ->  MOV t1, 30
       SUB t1, 50, 20  ->  MOV t1, 30

Safety rules
------------
* Labels, GOTO, IF_* and RETURN instructions are never removed or
  reordered.  This preserves all control flow.
* Event boundaries (LABEL event_*) are never modified.
* DECLARE instructions are never removed (runtime needs them for init).
* COMMAND instructions are never removed or reordered.
* Optimizations are only applied within a single, flat pass -- we do
  NOT combine operations across different handlers or jump targets.
* If a transformation would change program behaviour, it is skipped.

Note on "speedup"
-----------------
Instruction-count reduction does NOT necessarily mean a measurable runtime
speedup for this educational interpreter.  We report only instruction counts
and the actual removals made.
"""

import copy
from dataclasses import dataclass
from typing import Optional
from ir.instructions import (
    Instruction, AddInstr, SubInstr, MovInstr,
    LabelInstr, GotoInstr, IfInstr, ReturnInstr,
    DeclareInstr, CommandInstr,
)


@dataclass
class OptimizationReport:
    """Records what the optimizer actually changed."""
    original_count: int = 0
    optimized_count: int = 0
    changes: list = None    # list of str descriptions

    def __post_init__(self):
        if self.changes is None:
            self.changes = []

    @property
    def instructions_removed(self) -> int:
        return self.original_count - self.optimized_count

    @property
    def any_change(self) -> bool:
        return self.original_count != self.optimized_count or bool(self.changes)


class Optimizer:
    """
    Applies safe peephole optimizations to a TAC instruction list.
    Call  optimize(instructions)  which returns (new_instructions, report).
    The original instruction list is never mutated.
    """

    def __init__(self, verbose: bool = True):
        self.verbose = verbose

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def optimize(
        self,
        instructions: list[Instruction],
    ) -> tuple[list[Instruction], OptimizationReport]:
        """
        Return a new optimized instruction list and a report.
        The original list is left unchanged.
        """
        self._log_header()

        report = OptimizationReport(original_count=len(instructions))

        # Deep copy so we never modify the caller's list
        working = copy.deepcopy(instructions)

        # Apply passes in sequence
        working, changes_1 = self._pass_remove_zero_ops(working)
        working, changes_2 = self._pass_constant_folding(working)

        report.optimized_count = len(working)
        report.changes = changes_1 + changes_2

        self._log_report(report, working)
        return working, report

    # ------------------------------------------------------------------
    # Pass 1 -- Remove zero-operand additions / subtractions
    # ------------------------------------------------------------------

    def _pass_remove_zero_ops(
        self,
        instructions: list[Instruction],
    ) -> tuple[list[Instruction], list[str]]:
        """
        Remove ADD dest, dest, 0  and  SUB dest, dest, 0.
        These are no-ops because  x = x + 0 = x  and  x = x - 0 = x.
        We only remove them when src1 == dest (compound-assignment form)
        because  y = x + 0  still has the side-effect of assigning x to y.
        """
        result = []
        changes = []
        for instr in instructions:
            removed = False
            if isinstance(instr, (AddInstr, SubInstr)):
                # Check for "dest op= 0" pattern
                if (
                    isinstance(instr.src2, int) and instr.src2 == 0
                    and instr.src1 == instr.dest
                ):
                    verb = "ADD" if isinstance(instr, AddInstr) else "SUB"
                    msg = (
                        f"Removed no-op: {verb} {instr.dest}, "
                        f"{instr.src1}, 0"
                    )
                    changes.append(msg)
                    self._log(f"  [Pass 1] {msg}")
                    removed = True
            if not removed:
                result.append(instr)
        return result, changes

    # ------------------------------------------------------------------
    # Pass 2 -- Constant folding
    # ------------------------------------------------------------------

    def _pass_constant_folding(
        self,
        instructions: list[Instruction],
    ) -> tuple[list[Instruction], list[str]]:
        """
        If both src1 and src2 of an ADD / SUB are integer literals,
        evaluate the result at compile time and replace with MOV dest, result.
        """
        result = []
        changes = []
        for instr in instructions:
            folded = False
            if isinstance(instr, (AddInstr, SubInstr)):
                if isinstance(instr.src1, int) and isinstance(instr.src2, int):
                    if isinstance(instr, AddInstr):
                        value = instr.src1 + instr.src2
                        op_sym = "+"
                    else:
                        value = instr.src1 - instr.src2
                        op_sym = "-"
                    msg = (
                        f"Constant fold: {instr.dest} = "
                        f"{instr.src1} {op_sym} {instr.src2} -> {value}"
                    )
                    changes.append(msg)
                    self._log(f"  [Pass 2] {msg}")
                    result.append(
                        MovInstr(dest=instr.dest, src=value, line=instr.line)
                    )
                    folded = True
            if not folded:
                result.append(instr)
        return result, changes

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def _log(self, msg: str):
        if self.verbose:
            print(f"  {msg}")

    def _log_header(self):
        if not self.verbose:
            return
        print()
        print("=" * 60)
        print("  PHASE 5: CODE OPTIMIZATION")
        print("=" * 60)
        print()

    def _log_report(self, report: OptimizationReport, optimized: list):
        if not self.verbose:
            return
        print()
        print("-" * 60)
        print("  OPTIMIZATION REPORT")
        print("-" * 60)
        print(f"  Original instruction count : {report.original_count}")
        print(f"  Optimized instruction count: {report.optimized_count}")
        print(f"  Instructions removed       : {report.instructions_removed}")
        print()
        if report.changes:
            print("  Changes applied:")
            for change in report.changes:
                print(f"    * {change}")
        else:
            print("  No optimizations applicable. TAC remains unchanged.")
        print()
        print("-" * 60)
        print("  OPTIMIZED THREE-ADDRESS CODE")
        print("-" * 60)
        for i, instr in enumerate(optimized, start=1):
            print(f"  {i:04d}  {instr}")
        print()
        print("  PHASE 5 COMPLETE")
        print(f"  [{'OK' if report.any_change else 'INFO'}] "
              f"{'Optimization applied' if report.any_change else 'No changes needed'}")
        print("=" * 60)
