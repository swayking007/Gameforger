"""
GameForge Compiler -- Error Definitions
=======================================
All compiler error types for Phases 1-3.
Each error carries a message, a line number, and optionally a column number.
"""


class GameForgeError(Exception):
    """Base class for all GameForge compiler errors."""

    def __init__(self, message, line=None, column=None):
        self.message = message
        self.line = line
        self.column = column
        super().__init__(self.format())

    def format(self):
        location = ""
        if self.line is not None:
            location += f"  Line: {self.line}"
        if self.column is not None:
            location += f", Column: {self.column}"
        return f"{self.error_type()}:\n  {self.message}\n{location}"

    def error_type(self):
        return "COMPILER ERROR"


class LexicalError(GameForgeError):
    """Raised when the lexer encounters an invalid character or token."""

    def error_type(self):
        return "LEXICAL ERROR"


class SyntaxError(GameForgeError):
    """Raised when the parser encounters an unexpected token sequence."""

    def error_type(self):
        return "SYNTAX ERROR"


class SemanticError(GameForgeError):
    """Raised when the semantic analyzer detects a logic error."""

    def error_type(self):
        return "SEMANTIC ERROR"
