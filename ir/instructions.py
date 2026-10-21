"""
GameForge Compiler -- TAC Instruction Definitions (Phase 4)
============================================================

Three-Address Code (TAC) Instruction Format
--------------------------------------------
Each instruction performs one simple operation over at most three named
operands.  The format used throughout GameForge is:

    OPCODE  dest, src1, src2

where dest/src1/src2 are variable names, numeric literals or label strings.
Not every field is used by every instruction type; unused fields are None.

Instruction catalogue
---------------------
  DECLARE  dest, value        -- initialise variable at program start
  MOV      dest, src          -- dest = src  (simple assignment)
  ADD      dest, src1, src2   -- dest = src1 + src2
  SUB      dest, src1, src2   -- dest = src1 - src2
  LABEL    name               -- branch / event target marker
  GOTO     target             -- unconditional jump to LABEL
  IF_op    src1, src2, target -- conditional jump (op is LE, LT, GE, GT, EQ, NE)
  RETURN                      -- end of event handler
  COMMAND  name               -- built-in command (GAME_OVER / LEVEL_COMPLETE)

Conditional jump opcode mapping
---------------------------------
  <=  ->  IF_LE
  <   ->  IF_LT
  >=  ->  IF_GE
  >   ->  IF_GT
  ==  ->  IF_EQ
  !=  ->  IF_NE
"""

from dataclasses import dataclass, field
from typing import Optional


# ------------------------------------------------------------------
# Relational operator -> TAC opcode mapping
# ------------------------------------------------------------------

REL_OP_TO_IF = {
    "<=": "IF_LE",
    "<":  "IF_LT",
    ">=": "IF_GE",
    ">":  "IF_GT",
    "==": "IF_EQ",
    "!=": "IF_NE",
}


# ------------------------------------------------------------------
# Base instruction
# ------------------------------------------------------------------

@dataclass
class Instruction:
    """Abstract base for all TAC instructions."""
    line: Optional[int] = field(default=None, compare=False)

    def opcode(self) -> str:
        raise NotImplementedError

    def operands_str(self) -> str:
        """Human-readable operand list (without opcode)."""
        raise NotImplementedError

    def __str__(self) -> str:
        ops = self.operands_str()
        return f"{self.opcode():<10} {ops}" if ops else self.opcode()


# ------------------------------------------------------------------
# Concrete instruction types
# ------------------------------------------------------------------

@dataclass
class DeclareInstr(Instruction):
    """DECLARE dest, value  --  initialise a variable."""
    dest: str = ""
    value: int = 0

    def opcode(self) -> str:
        return "DECLARE"

    def operands_str(self) -> str:
        return f"{self.dest}, {self.value}"


@dataclass
class MovInstr(Instruction):
    """MOV dest, src  --  dest = src (simple assignment)."""
    dest: str = ""
    src: "str | int" = 0

    def opcode(self) -> str:
        return "MOV"

    def operands_str(self) -> str:
        return f"{self.dest}, {self.src}"


@dataclass
class AddInstr(Instruction):
    """ADD dest, src1, src2  --  dest = src1 + src2."""
    dest: str = ""
    src1: "str | int" = 0
    src2: "str | int" = 0

    def opcode(self) -> str:
        return "ADD"

    def operands_str(self) -> str:
        return f"{self.dest}, {self.src1}, {self.src2}"


@dataclass
class SubInstr(Instruction):
    """SUB dest, src1, src2  --  dest = src1 - src2."""
    dest: str = ""
    src1: "str | int" = 0
    src2: "str | int" = 0

    def opcode(self) -> str:
        return "SUB"

    def operands_str(self) -> str:
        return f"{self.dest}, {self.src1}, {self.src2}"


@dataclass
class LabelInstr(Instruction):
    """LABEL name  --  marks a jump target."""
    name: str = ""

    def opcode(self) -> str:
        return "LABEL"

    def operands_str(self) -> str:
        return self.name

    def __str__(self) -> str:
        # Labels are typically shown un-indented for readability
        return f"LABEL      {self.name}"


@dataclass
class GotoInstr(Instruction):
    """GOTO target  --  unconditional jump."""
    target: str = ""

    def opcode(self) -> str:
        return "GOTO"

    def operands_str(self) -> str:
        return self.target


@dataclass
class IfInstr(Instruction):
    """IF_<op> src1, src2, target  --  conditional jump."""
    if_opcode: str = "IF_LE"   # e.g. IF_LE, IF_GE, IF_EQ …
    src1: "str | int" = ""
    src2: "str | int" = 0
    target: str = ""

    def opcode(self) -> str:
        return self.if_opcode

    def operands_str(self) -> str:
        return f"{self.src1}, {self.src2}, {self.target}"


@dataclass
class ReturnInstr(Instruction):
    """RETURN  --  end of an event handler."""

    def opcode(self) -> str:
        return "RETURN"

    def operands_str(self) -> str:
        return ""


@dataclass
class CommandInstr(Instruction):
    """COMMAND name  --  built-in game command (GAME_OVER / LEVEL_COMPLETE)."""
    name: str = ""

    def opcode(self) -> str:
        return "COMMAND"

    def operands_str(self) -> str:
        return self.name
