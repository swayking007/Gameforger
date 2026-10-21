"""
GameForge Compiler -- Intermediate Representation (IR) Package
==============================================================
Exposes TAC instruction classes, the TAC generator, and the TAC printer.
"""

from .instructions import (
    Instruction, DeclareInstr, MovInstr, AddInstr, SubInstr,
    LabelInstr, GotoInstr, IfInstr, ReturnInstr, CommandInstr,
)
from .tac_generator import TACGenerator
from .tac_printer import TACPrinter

__all__ = [
    "Instruction", "DeclareInstr", "MovInstr", "AddInstr", "SubInstr",
    "LabelInstr", "GotoInstr", "IfInstr", "ReturnInstr", "CommandInstr",
    "TACGenerator", "TACPrinter",
]
