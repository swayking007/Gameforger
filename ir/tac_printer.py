"""
GameForge Compiler -- TAC Printer (Phase 4)
===========================================
Utility functions for rendering TAC instruction lists as readable text.
Used by both the terminal driver and the UI.
"""

from .instructions import Instruction


class TACPrinter:
    """Formats a list of TAC instructions as a numbered listing string."""

    @staticmethod
    def format_listing(instructions: list[Instruction]) -> str:
        """
        Return the full numbered TAC listing as a single string.
        Example line:
            0001  DECLARE    health, 100
        """
        lines = []
        for i, instr in enumerate(instructions, start=1):
            lines.append(f"{i:04d}  {instr}")
        return "\n".join(lines)

    @staticmethod
    def format_single(instr: Instruction, index: int) -> str:
        """Format one instruction with its sequence number."""
        return f"{index:04d}  {instr}"

    @staticmethod
    def summary(instructions: list[Instruction]) -> str:
        """One-line count summary."""
        return f"TAC instructions generated: {len(instructions)}"
