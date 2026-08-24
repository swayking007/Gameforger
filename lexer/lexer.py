"""
GameForge Compiler -- Lexer (Phase 1)
=====================================
A hand-written scanner that converts GameScript source text into a stream of
tokens.

Indentation handling
--------------------
GameScript uses indentation for WHEN / IF blocks (like Python).
We track an explicit indent-level stack.  At the start of each logical line we
compare the leading whitespace to the current indent level and emit INDENT /
DEDENT tokens as needed.  Only spaces are counted (tabs are treated as errors
to keep things simple).
"""

from .token import Token, TokenType, KEYWORDS, COMMANDS
from errors.errors import LexicalError


class Lexer:
    """Scans GameScript source code and produces a list of Tokens."""

    def __init__(self, source: str, verbose: bool = True):
        self.source = source
        self.verbose = verbose

        # Scanner state
        self.pos = 0          # Current index into source
        self.line = 1         # Current line number (1-based)
        self.column = 1       # Current column number (1-based)
        self.tokens: list[Token] = []

        # Indent tracking
        self.indent_stack = [0]  # Stack of indentation levels; starts at 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def tokenize(self) -> list[Token]:
        """Scan the entire source and return the token list."""
        self._log_header()

        lines = self.source.split("\n")
        for line_no, raw_line in enumerate(lines, start=1):
            self.line = line_no

            # Strip trailing whitespace / carriage-return but keep leading spaces
            line = raw_line.rstrip()

            # Skip completely blank lines and comment-only lines
            stripped = line.lstrip()
            if stripped == "" or stripped.startswith("#"):
                if stripped.startswith("#"):
                    self._log(f"Skipping comment: {stripped}")
                continue

            # --- Indentation ---
            indent = len(line) - len(stripped)
            self._handle_indentation(indent)

            # --- Scan the (stripped) content of the line ---
            self.pos = 0
            self.column = indent + 1  # column starts after the leading spaces
            self._scan_line(stripped)

            # Emit a NEWLINE after every logical line
            self._add_token(TokenType.NEWLINE, "\\n")

        # Close any remaining indents at EOF
        while len(self.indent_stack) > 1:
            self.indent_stack.pop()
            self._add_token(TokenType.DEDENT, "<DEDENT>")

        self._add_token(TokenType.EOF, "<EOF>")
        self._log_footer()
        return self.tokens

    # ------------------------------------------------------------------
    # Indentation
    # ------------------------------------------------------------------

    def _handle_indentation(self, indent: int):
        current = self.indent_stack[-1]
        if indent > current:
            self.indent_stack.append(indent)
            self._add_token(TokenType.INDENT, "<INDENT>")
            self._log(f"Indentation increased -> level {indent}")
        elif indent < current:
            while self.indent_stack[-1] > indent:
                self.indent_stack.pop()
                self._add_token(TokenType.DEDENT, "<DEDENT>")
                self._log(f"Indentation decreased -> level {indent}")
            if self.indent_stack[-1] != indent:
                raise LexicalError(
                    f"Inconsistent indentation (got {indent} spaces, "
                    f"expected {self.indent_stack[-1]})",
                    line=self.line,
                    column=1,
                )

    # ------------------------------------------------------------------
    # Line scanner
    # ------------------------------------------------------------------

    def _scan_line(self, text: str):
        """Scan a single line (leading whitespace already stripped)."""
        self.pos = 0
        while self.pos < len(text):
            ch = text[self.pos]

            # Skip spaces inside a line (between tokens)
            if ch == " ":
                self.pos += 1
                self.column += 1
                continue

            # --- Multi-character operators first ---
            two = text[self.pos: self.pos + 2]
            if two == "+=":
                self._log(f"Reading: +=")
                self._log("Recognized plus-assign operator")
                self._add_token(TokenType.PLUS_ASSIGN, "+=")
                self.pos += 2
                self.column += 2
                continue
            if two == "-=":
                self._log(f"Reading: -=")
                self._log("Recognized minus-assign operator")
                self._add_token(TokenType.MINUS_ASSIGN, "-=")
                self.pos += 2
                self.column += 2
                continue
            if two == ">=":
                self._log("Reading: >=")
                self._log("Recognized greater-equal operator")
                self._add_token(TokenType.GREATER_EQUAL, ">=")
                self.pos += 2
                self.column += 2
                continue
            if two == "<=":
                self._log("Reading: <=")
                self._log("Recognized less-equal operator")
                self._add_token(TokenType.LESS_EQUAL, "<=")
                self.pos += 2
                self.column += 2
                continue
            if two == "==":
                self._log("Reading: ==")
                self._log("Recognized equal-equal operator")
                self._add_token(TokenType.EQUAL_EQUAL, "==")
                self.pos += 2
                self.column += 2
                continue
            if two == "!=":
                self._log("Reading: !=")
                self._log("Recognized not-equal operator")
                self._add_token(TokenType.NOT_EQUAL, "!=")
                self.pos += 2
                self.column += 2
                continue

            # --- Single-character operators ---
            if ch == "=":
                self._log("Reading: =")
                self._log("Recognized assignment operator")
                self._add_token(TokenType.ASSIGN, "=")
                self.pos += 1
                self.column += 1
                continue
            if ch == ">":
                self._log("Reading: >")
                self._log("Recognized greater-than operator")
                self._add_token(TokenType.GREATER, ">")
                self.pos += 1
                self.column += 1
                continue
            if ch == "<":
                self._log("Reading: <")
                self._log("Recognized less-than operator")
                self._add_token(TokenType.LESS, "<")
                self.pos += 1
                self.column += 1
                continue

            # --- Numbers ---
            if ch.isdigit():
                start = self.pos
                start_col = self.column
                while self.pos < len(text) and text[self.pos].isdigit():
                    self.pos += 1
                    self.column += 1
                number = text[start:self.pos]
                self._log(f"Reading: {number}")
                self._log(f"Recognized number {number}")
                self._add_token(TokenType.NUMBER, number, col=start_col)
                continue

            # --- Words (keywords, commands, identifiers) ---
            if ch.isalpha() or ch == "_":
                start = self.pos
                start_col = self.column
                while self.pos < len(text) and (text[self.pos].isalnum() or text[self.pos] == "_"):
                    self.pos += 1
                    self.column += 1
                word = text[start:self.pos]
                self._log(f"Reading: {word}")

                if word in KEYWORDS:
                    self._log(f"Recognized keyword {word}")
                    self._add_token(KEYWORDS[word], word, col=start_col)
                elif word in COMMANDS:
                    self._log(f"Recognized command {word}")
                    self._add_token(COMMANDS[word], word, col=start_col)
                else:
                    self._log(f"Recognized identifier {word}")
                    self._add_token(TokenType.IDENTIFIER, word, col=start_col)
                continue

            # --- Inline comment ---
            if ch == "#":
                self._log(f"Skipping inline comment")
                break  # rest of line is comment

            # --- Invalid character ---
            raise LexicalError(
                f"Invalid character '{ch}'",
                line=self.line,
                column=self.column,
            )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _add_token(self, ttype: TokenType, value: str, col: int | None = None):
        tok = Token(type=ttype, value=value, line=self.line, column=col or self.column)
        self.tokens.append(tok)

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def _log(self, msg: str):
        if self.verbose:
            print(f"  [LEXER] {msg}")

    def _log_header(self):
        if self.verbose:
            print()
            print("=" * 60)
            print("  PHASE 1: LEXICAL ANALYSIS")
            print("=" * 60)
            print()

    def _log_footer(self):
        if not self.verbose:
            return
        print()
        print("-" * 60)
        print("  TOKEN STREAM")
        print("-" * 60)
        for i, tok in enumerate(self.tokens, start=1):
            # Compact display -- skip NEWLINE/INDENT/DEDENT clutter for readability
            label = f"{tok.type.name:<25s}"
            val = tok.value if tok.type not in (
                TokenType.NEWLINE, TokenType.INDENT, TokenType.DEDENT, TokenType.EOF
            ) else ""
            print(f"  {i:>3}. {label} {val!r:>15s}   (line {tok.line})")
        print()
        print("  PHASE 1 COMPLETE")
        print("  [OK] Lexical analysis successful")
        print("=" * 60)
