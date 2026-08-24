"""
GameForge Compiler -- Token Definitions
=======================================
Defines TokenType enum and Token dataclass used throughout the compiler.
"""

from enum import Enum, auto
from dataclasses import dataclass


class TokenType(Enum):
    """Every token type recognised by the GameScript lexer."""

    # --- Keywords ---
    KEYWORD_PLAYER = auto()
    KEYWORD_WHEN = auto()
    KEYWORD_IF = auto()

    # --- Commands ---
    COMMAND_GAME_OVER = auto()
    COMMAND_LEVEL_COMPLETE = auto()

    # --- Identifiers & Literals ---
    IDENTIFIER = auto()
    NUMBER = auto()

    # --- Assignment Operators ---
    ASSIGN = auto()          # =
    PLUS_ASSIGN = auto()     # +=
    MINUS_ASSIGN = auto()    # -=

    # --- Relational Operators ---
    GREATER = auto()         # >
    LESS = auto()            # <
    GREATER_EQUAL = auto()   # >=
    LESS_EQUAL = auto()      # <=
    EQUAL_EQUAL = auto()     # ==
    NOT_EQUAL = auto()       # !=

    # --- Structural ---
    NEWLINE = auto()
    INDENT = auto()
    DEDENT = auto()
    EOF = auto()


# Maps keyword strings to their TokenType
KEYWORDS = {
    "PLAYER": TokenType.KEYWORD_PLAYER,
    "WHEN":   TokenType.KEYWORD_WHEN,
    "IF":     TokenType.KEYWORD_IF,
}

# Maps command strings to their TokenType
COMMANDS = {
    "GAME_OVER":      TokenType.COMMAND_GAME_OVER,
    "LEVEL_COMPLETE": TokenType.COMMAND_LEVEL_COMPLETE,
}


@dataclass
class Token:
    """A single lexical token produced by the lexer."""
    type: TokenType
    value: str
    line: int
    column: int

    def __repr__(self):
        return f"Token({self.type.name}, {self.value!r}, ln={self.line}, col={self.column})"
