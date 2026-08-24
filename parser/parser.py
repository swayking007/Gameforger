"""
GameForge Compiler -- Recursive-Descent Parser (Phase 2)
========================================================
Consumes a token stream from the Lexer and produces an AST.

Grammar (simplified):
    PROGRAM             -> STATEMENT*
    STATEMENT           -> PLAYER_DECLARATION | EVENT_BLOCK | IF_STATEMENT
    PLAYER_DECLARATION  -> PLAYER IDENTIFIER ASSIGN NUMBER NEWLINE
    EVENT_BLOCK         -> WHEN IDENTIFIER NEWLINE INDENT BLOCK DEDENT
    IF_STATEMENT        -> IF CONDITION NEWLINE INDENT BLOCK DEDENT
    BLOCK               -> (ACTION NEWLINE)+
    ACTION              -> ASSIGNMENT | COMMAND
    ASSIGNMENT          -> IDENTIFIER (ASSIGN | PLUS_ASSIGN | MINUS_ASSIGN) VALUE
    COMMAND             -> GAME_OVER | LEVEL_COMPLETE
    CONDITION           -> IDENTIFIER REL_OP VALUE
    VALUE               -> NUMBER | IDENTIFIER
    REL_OP              -> > | < | >= | <= | == | !=
"""

from lexer.token import Token, TokenType
from errors.errors import SyntaxError as GFSyntaxError
from .ast_nodes import (
    ProgramNode, PlayerDeclarationNode, EventNode, IfNode,
    AssignmentNode, CommandNode, ConditionNode,
    LiteralNode, IdentifierNode,
)


# Tokens that represent relational operators
_REL_OPS = {
    TokenType.GREATER, TokenType.LESS,
    TokenType.GREATER_EQUAL, TokenType.LESS_EQUAL,
    TokenType.EQUAL_EQUAL, TokenType.NOT_EQUAL,
}

# Tokens that represent assignment operators
_ASSIGN_OPS = {
    TokenType.ASSIGN, TokenType.PLUS_ASSIGN, TokenType.MINUS_ASSIGN,
}

# Tokens that represent commands
_COMMAND_TOKENS = {
    TokenType.COMMAND_GAME_OVER, TokenType.COMMAND_LEVEL_COMPLETE,
}


class Parser:
    """Recursive-descent parser for GameScript."""

    def __init__(self, tokens: list[Token], verbose: bool = True):
        self.tokens = tokens
        self.verbose = verbose
        self.pos = 0   # index into self.tokens

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse(self) -> ProgramNode:
        """Parse the full program and return the root AST node."""
        self._log_header()
        self._log("Starting parse...")
        self._log("Parsing program...")
        program = self._parse_program()
        self._log_ast(program)
        return program

    # ------------------------------------------------------------------
    # Grammar rules
    # ------------------------------------------------------------------

    def _parse_program(self) -> ProgramNode:
        statements = []
        while not self._check(TokenType.EOF):
            self._skip_newlines()
            if self._check(TokenType.EOF):
                break
            stmt = self._parse_statement()
            statements.append(stmt)
        return ProgramNode(statements=statements)

    def _parse_statement(self):
        if self._check(TokenType.KEYWORD_PLAYER):
            return self._parse_player_declaration()
        if self._check(TokenType.KEYWORD_WHEN):
            return self._parse_event_block()
        if self._check(TokenType.KEYWORD_IF):
            return self._parse_if_statement()
        # If we see an identifier or command at the top level, give a helpful error
        tok = self._current()
        raise GFSyntaxError(
            f"Unexpected token '{tok.value}'. "
            f"Expected PLAYER, WHEN, or IF at top level.",
            line=tok.line, column=tok.column,
        )

    # --- PLAYER declaration ---

    def _parse_player_declaration(self) -> PlayerDeclarationNode:
        player_tok = self._expect(TokenType.KEYWORD_PLAYER)
        self._log("Parsing PLAYER declaration...")
        name_tok = self._expect(
            TokenType.IDENTIFIER,
            msg="Expected identifier after PLAYER.",
        )
        self._expect(
            TokenType.ASSIGN,
            msg="Expected '=' after variable name in PLAYER declaration.",
        )
        value_tok = self._expect(
            TokenType.NUMBER,
            msg="Expected number value in PLAYER declaration.",
        )
        self._expect_newline()
        name_node = IdentifierNode(name=name_tok.value, line=name_tok.line)
        value_node = LiteralNode(value=int(value_tok.value), line=value_tok.line)
        self._log(f"  -> PlayerDeclaration({name_tok.value} = {value_tok.value})")
        return PlayerDeclarationNode(name=name_node, value=value_node, line=player_tok.line)

    # --- EVENT block ---

    def _parse_event_block(self) -> EventNode:
        when_tok = self._expect(TokenType.KEYWORD_WHEN)
        self._log("Parsing EVENT block...")
        name_tok = self._expect(
            TokenType.IDENTIFIER,
            msg="Expected event name after WHEN.",
        )
        self._expect_newline()
        self._expect(
            TokenType.INDENT,
            msg="Expected indented block after WHEN event.",
        )
        body = self._parse_block()
        self._expect(
            TokenType.DEDENT,
            msg="Expected end of indented block after WHEN body.",
        )
        name_node = IdentifierNode(name=name_tok.value, line=name_tok.line)
        self._log(f"  -> Event({name_tok.value}) with {len(body)} action(s)")
        return EventNode(name=name_node, body=body, line=when_tok.line)

    # --- IF statement ---

    def _parse_if_statement(self) -> IfNode:
        if_tok = self._expect(TokenType.KEYWORD_IF)
        self._log("Parsing IF statement...")
        condition = self._parse_condition()
        self._expect_newline()
        self._expect(
            TokenType.INDENT,
            msg="Expected indented block after IF condition.",
        )
        body = self._parse_block()
        self._expect(
            TokenType.DEDENT,
            msg="Expected end of indented block after IF body.",
        )
        self._log(f"  -> If({condition})")
        return IfNode(condition=condition, body=body, line=if_tok.line)

    # --- BLOCK (one or more actions) ---

    def _parse_block(self) -> list:
        actions = []
        while not self._check(TokenType.DEDENT) and not self._check(TokenType.EOF):
            self._skip_newlines()
            if self._check(TokenType.DEDENT) or self._check(TokenType.EOF):
                break
            action = self._parse_action()
            actions.append(action)
            # Consume newline after action (if present)
            if self._check(TokenType.NEWLINE):
                self._advance()
        if not actions:
            tok = self._current()
            raise GFSyntaxError(
                "Expected at least one action inside block.",
                line=tok.line, column=tok.column,
            )
        return actions

    # --- ACTION (assignment or command) ---

    def _parse_action(self):
        if self._check_any(_COMMAND_TOKENS):
            return self._parse_command()
        if self._check(TokenType.IDENTIFIER):
            return self._parse_assignment()
        tok = self._current()
        raise GFSyntaxError(
            f"Expected assignment or command, got '{tok.value}'.",
            line=tok.line, column=tok.column,
        )

    # --- ASSIGNMENT ---

    def _parse_assignment(self) -> AssignmentNode:
        self._log("Parsing assignment...")
        var_tok = self._expect(TokenType.IDENTIFIER)
        if not self._check_any(_ASSIGN_OPS):
            tok = self._current()
            raise GFSyntaxError(
                f"Expected assignment operator after '{var_tok.value}', "
                f"got '{tok.value}'.",
                line=tok.line, column=tok.column,
            )
        op_tok = self._advance()
        value_node = self._parse_value(
            msg=f"Expected value after '{op_tok.value}'."
        )
        var_node = IdentifierNode(name=var_tok.value, line=var_tok.line)
        self._log(f"  -> Assignment({var_tok.value} {op_tok.value} {value_node})")
        return AssignmentNode(
            variable=var_node, operator=op_tok.value,
            value=value_node, line=var_tok.line,
        )

    # --- COMMAND ---

    def _parse_command(self) -> CommandNode:
        tok = self._advance()
        self._log(f"Parsing command: {tok.value}")
        return CommandNode(name=tok.value, line=tok.line)

    # --- CONDITION ---

    def _parse_condition(self) -> ConditionNode:
        left_tok = self._expect(
            TokenType.IDENTIFIER,
            msg="Expected variable name in condition.",
        )
        if not self._check_any(_REL_OPS):
            tok = self._current()
            raise GFSyntaxError(
                f"Expected relational operator in condition, got '{tok.value}'.",
                line=tok.line, column=tok.column,
            )
        op_tok = self._advance()
        right_node = self._parse_value(
            msg="Expected value on right side of condition."
        )
        left_node = IdentifierNode(name=left_tok.value, line=left_tok.line)
        return ConditionNode(
            left=left_node, operator=op_tok.value,
            right=right_node, line=left_tok.line,
        )

    # --- VALUE ---

    def _parse_value(self, msg="Expected a value."):
        if self._check(TokenType.NUMBER):
            tok = self._advance()
            return LiteralNode(value=int(tok.value), line=tok.line)
        if self._check(TokenType.IDENTIFIER):
            tok = self._advance()
            return IdentifierNode(name=tok.value, line=tok.line)
        tok = self._current()
        raise GFSyntaxError(msg, line=tok.line, column=tok.column)

    # ------------------------------------------------------------------
    # Token-stream helpers
    # ------------------------------------------------------------------

    def _current(self) -> Token:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        # Should not happen if EOF is always present
        return Token(TokenType.EOF, "<EOF>", line=0, column=0)

    def _advance(self) -> Token:
        tok = self._current()
        self.pos += 1
        return tok

    def _check(self, ttype: TokenType) -> bool:
        return self._current().type == ttype

    def _check_any(self, ttypes: set[TokenType]) -> bool:
        return self._current().type in ttypes

    def _expect(self, ttype: TokenType, msg: str | None = None) -> Token:
        tok = self._current()
        if tok.type != ttype:
            err_msg = msg or f"Expected {ttype.name}, got {tok.type.name} ('{tok.value}')."
            raise GFSyntaxError(err_msg, line=tok.line, column=tok.column)
        return self._advance()

    def _expect_newline(self):
        """Consume a NEWLINE token if present; tolerate EOF."""
        if self._check(TokenType.NEWLINE):
            self._advance()

    def _skip_newlines(self):
        while self._check(TokenType.NEWLINE):
            self._advance()

    # ------------------------------------------------------------------
    # Pretty-print AST
    # ------------------------------------------------------------------

    def _log_ast(self, program: ProgramNode):
        if not self.verbose:
            return
        print()
        print("-" * 60)
        print("  ABSTRACT SYNTAX TREE")
        print("-" * 60)
        self._print_tree(program, prefix="  ", is_last=True)
        print()
        print("  PHASE 2 COMPLETE")
        print("  [OK] Syntax analysis successful")
        print("=" * 60)

    def _print_tree(self, node, prefix="", is_last=True):
        """Recursively print the AST as a visual tree."""
        connector = "\\-- " if is_last else "+-- "

        if isinstance(node, ProgramNode):
            print(f"{prefix}Program")
            for i, stmt in enumerate(node.statements):
                last = (i == len(node.statements) - 1)
                self._print_tree(stmt, prefix + "  ", is_last=last)

        elif isinstance(node, PlayerDeclarationNode):
            print(f"{prefix}{connector}PlayerDeclaration")
            child_prefix = prefix + ("    " if is_last else "|   ")
            print(f"{child_prefix}+-- {node.name.name}")
            print(f"{child_prefix}\\-- {node.value.value}")

        elif isinstance(node, EventNode):
            print(f"{prefix}{connector}Event")
            child_prefix = prefix + ("    " if is_last else "|   ")
            print(f"{child_prefix}+-- {node.name.name}")
            for i, action in enumerate(node.body):
                last = (i == len(node.body) - 1)
                self._print_tree(action, child_prefix, is_last=last)

        elif isinstance(node, IfNode):
            print(f"{prefix}{connector}If")
            child_prefix = prefix + ("    " if is_last else "|   ")
            print(f"{child_prefix}+-- Condition: {node.condition.left.name} "
                  f"{node.condition.operator} {node.condition.right}")
            for i, action in enumerate(node.body):
                last = (i == len(node.body) - 1)
                self._print_tree(action, child_prefix, is_last=last)

        elif isinstance(node, AssignmentNode):
            print(f"{prefix}{connector}Assignment")
            child_prefix = prefix + ("    " if is_last else "|   ")
            print(f"{child_prefix}+-- {node.variable.name}")
            print(f"{child_prefix}+-- {node.operator}")
            print(f"{child_prefix}\\-- {node.value}")

        elif isinstance(node, CommandNode):
            print(f"{prefix}{connector}Command({node.name})")

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def _log_header(self):
        if self.verbose:
            print()
            print("=" * 60)
            print("  PHASE 2: SYNTAX ANALYSIS")
            print("=" * 60)
            print()

    def _log(self, msg: str):
        if self.verbose:
            print(f"  [PARSER] {msg}")
