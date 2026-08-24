"""
GameForge Compiler -- Symbol Table
==================================
A simple dictionary-backed symbol table that stores variable metadata.
"""

from dataclasses import dataclass


@dataclass
class Symbol:
    """One entry in the symbol table."""
    name: str
    var_type: str    # "INTEGER" for now
    value: int
    line: int        # line where declared


class SymbolTable:
    """Dictionary-based symbol table for GameScript variables."""

    def __init__(self):
        self._symbols: dict[str, Symbol] = {}

    def declare(self, name: str, var_type: str, value: int, line: int):
        """Register a new variable.  Returns the created Symbol."""
        sym = Symbol(name=name, var_type=var_type, value=value, line=line)
        self._symbols[name] = sym
        return sym

    def lookup(self, name: str) -> Symbol | None:
        """Look up a variable by name.  Returns None if not found."""
        return self._symbols.get(name)

    def contains(self, name: str) -> bool:
        return name in self._symbols

    def all_symbols(self) -> list[Symbol]:
        """Return all symbols in declaration order (insertion order)."""
        return list(self._symbols.values())

    def __repr__(self):
        return f"SymbolTable({list(self._symbols.keys())})"
