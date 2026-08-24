"""
GameForge Compiler -- Test Suite
================================
Tests cover all three compiler phases:
  - Lexer (tokenization, error handling)
  - Parser (AST generation, syntax errors)
  - Semantic Analyzer (symbol table, all semantic rules)

Run with:
    python -m pytest tests/test_compiler.py -v
  or:
    python -m unittest tests.test_compiler -v
"""

import sys
import os
import unittest

# Ensure project root is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lexer import Lexer, TokenType
from parser import Parser
from parser.ast_nodes import (
    ProgramNode, PlayerDeclarationNode, EventNode, IfNode,
    AssignmentNode, CommandNode,
)
from semantic import SemanticAnalyzer
from errors.errors import LexicalError, SyntaxError as GFSyntaxError, SemanticError


# ======================================================================
#  Helper -- run all three phases silently
# ======================================================================

def _tokenize(source: str):
    return Lexer(source, verbose=False).tokenize()


def _parse(source: str):
    tokens = _tokenize(source)
    return Parser(tokens, verbose=False).parse()


def _analyze(source: str):
    ast = _parse(source)
    analyzer = SemanticAnalyzer(verbose=False)
    return analyzer.analyze(ast), ast


# ======================================================================
#  Phase 1 -- Lexer Tests
# ======================================================================

class TestLexer(unittest.TestCase):
    """Tests for the GameScript lexer."""

    def test_player_declaration_tokens(self):
        tokens = _tokenize("PLAYER health = 100")
        types = [t.type for t in tokens]
        self.assertIn(TokenType.KEYWORD_PLAYER, types)
        self.assertIn(TokenType.IDENTIFIER, types)
        self.assertIn(TokenType.ASSIGN, types)
        self.assertIn(TokenType.NUMBER, types)
        self.assertIn(TokenType.EOF, types)

    def test_keywords_recognised(self):
        tokens = _tokenize("PLAYER x = 1\nWHEN enemy_attack\n    x -= 1\nIF x <= 0\n    GAME_OVER")
        types = [t.type for t in tokens]
        self.assertIn(TokenType.KEYWORD_PLAYER, types)
        self.assertIn(TokenType.KEYWORD_WHEN, types)
        self.assertIn(TokenType.KEYWORD_IF, types)

    def test_operators(self):
        tokens = _tokenize("PLAYER x = 1\nWHEN enemy_attack\n    x += 10\n    x -= 5")
        types = [t.type for t in tokens]
        self.assertIn(TokenType.PLUS_ASSIGN, types)
        self.assertIn(TokenType.MINUS_ASSIGN, types)

    def test_relational_operators(self):
        tokens = _tokenize("PLAYER x = 1\nIF x >= 0\n    GAME_OVER")
        types = [t.type for t in tokens]
        self.assertIn(TokenType.GREATER_EQUAL, types)

    def test_commands_recognised(self):
        tokens = _tokenize("PLAYER x = 1\nIF x <= 0\n    GAME_OVER")
        types = [t.type for t in tokens]
        self.assertIn(TokenType.COMMAND_GAME_OVER, types)

    def test_comment_ignored(self):
        tokens = _tokenize("# This is a comment\nPLAYER health = 100")
        # Comment should not produce any token -- only PLAYER line + EOF
        values = [t.value for t in tokens if t.type == TokenType.IDENTIFIER]
        self.assertIn("health", values)

    def test_indent_dedent(self):
        tokens = _tokenize("WHEN enemy_attack\n    health -= 20")
        types = [t.type for t in tokens]
        self.assertIn(TokenType.INDENT, types)
        self.assertIn(TokenType.DEDENT, types)

    def test_line_numbers(self):
        tokens = _tokenize("PLAYER health = 100\nPLAYER coins = 0")
        player_tokens = [t for t in tokens if t.type == TokenType.KEYWORD_PLAYER]
        self.assertEqual(player_tokens[0].line, 1)
        self.assertEqual(player_tokens[1].line, 2)

    def test_invalid_character(self):
        with self.assertRaises(LexicalError):
            _tokenize("PLAYER health @= 100")

    def test_invalid_character_message(self):
        try:
            _tokenize("PLAYER health @= 100")
            self.fail("Expected LexicalError")
        except LexicalError as e:
            self.assertIn("@", e.message)

    def test_eof_always_present(self):
        tokens = _tokenize("")
        self.assertEqual(tokens[-1].type, TokenType.EOF)


# ======================================================================
#  Phase 2 -- Parser Tests
# ======================================================================

class TestParser(unittest.TestCase):
    """Tests for the GameScript parser."""

    def test_player_declaration(self):
        ast = _parse("PLAYER health = 100")
        self.assertIsInstance(ast, ProgramNode)
        self.assertEqual(len(ast.statements), 1)
        self.assertIsInstance(ast.statements[0], PlayerDeclarationNode)
        self.assertEqual(ast.statements[0].name.name, "health")
        self.assertEqual(ast.statements[0].value.value, 100)

    def test_event_block(self):
        ast = _parse("WHEN enemy_attack\n    health -= 20")
        self.assertEqual(len(ast.statements), 1)
        event = ast.statements[0]
        self.assertIsInstance(event, EventNode)
        self.assertEqual(event.name.name, "enemy_attack")
        self.assertEqual(len(event.body), 1)
        self.assertIsInstance(event.body[0], AssignmentNode)

    def test_if_statement(self):
        ast = _parse("PLAYER health = 100\nIF health <= 0\n    GAME_OVER")
        if_node = ast.statements[1]
        self.assertIsInstance(if_node, IfNode)
        self.assertEqual(if_node.condition.operator, "<=")
        self.assertEqual(len(if_node.body), 1)
        self.assertIsInstance(if_node.body[0], CommandNode)
        self.assertEqual(if_node.body[0].name, "GAME_OVER")

    def test_multiple_actions_in_event(self):
        src = "WHEN collect_coin\n    coins += 10\n    score += 5"
        ast = _parse(src)
        event = ast.statements[0]
        self.assertEqual(len(event.body), 2)

    def test_full_program(self):
        src = (
            "PLAYER health = 100\n"
            "PLAYER coins = 0\n"
            "WHEN enemy_attack\n"
            "    health -= 20\n"
            "WHEN collect_coin\n"
            "    coins += 10\n"
            "IF health <= 0\n"
            "    GAME_OVER\n"
        )
        ast = _parse(src)
        self.assertEqual(len(ast.statements), 5)

    def test_syntax_error_missing_identifier(self):
        with self.assertRaises(GFSyntaxError):
            _parse("PLAYER = 100")

    def test_syntax_error_missing_value(self):
        with self.assertRaises(GFSyntaxError):
            _parse("WHEN enemy_attack\n    health -=")

    def test_syntax_error_bad_top_level(self):
        with self.assertRaises(GFSyntaxError):
            _parse("RANDOMWORD stuff")


# ======================================================================
#  Phase 3 -- Semantic Analysis Tests
# ======================================================================

class TestSemanticAnalyzer(unittest.TestCase):
    """Tests for the GameScript semantic analyzer."""

    def test_symbol_table_populated(self):
        st, _ = _analyze("PLAYER health = 100\nPLAYER coins = 0")
        self.assertTrue(st.contains("health"))
        self.assertTrue(st.contains("coins"))

    def test_symbol_table_values(self):
        st, _ = _analyze("PLAYER health = 100")
        sym = st.lookup("health")
        self.assertEqual(sym.var_type, "INTEGER")
        self.assertEqual(sym.value, 100)

    def test_undeclared_variable(self):
        with self.assertRaises(SemanticError) as ctx:
            _analyze("WHEN enemy_attack\n    gems -= 20")
        self.assertIn("gems", ctx.exception.message)

    def test_duplicate_declaration(self):
        with self.assertRaises(SemanticError) as ctx:
            _analyze("PLAYER health = 100\nPLAYER health = 200")
        self.assertIn("already declared", ctx.exception.message)

    def test_unknown_event(self):
        with self.assertRaises(SemanticError) as ctx:
            _analyze("PLAYER health = 100\nWHEN enemy_attak\n    health -= 20")
        self.assertIn("enemy_attak", ctx.exception.message)

    def test_valid_event(self):
        # Should not raise
        _analyze(
            "PLAYER health = 100\n"
            "WHEN enemy_attack\n"
            "    health -= 20\n"
        )

    def test_condition_undeclared_var(self):
        with self.assertRaises(SemanticError):
            _analyze("IF energy <= 0\n    GAME_OVER")

    def test_valid_full_program(self):
        src = (
            "PLAYER health = 100\n"
            "PLAYER coins = 0\n"
            "PLAYER score = 0\n"
            "WHEN enemy_attack\n"
            "    health -= 20\n"
            "WHEN collect_coin\n"
            "    coins += 10\n"
            "WHEN player_move\n"
            "    score += 5\n"
            "IF health <= 0\n"
            "    GAME_OVER\n"
        )
        st, _ = _analyze(src)
        self.assertEqual(len(st.all_symbols()), 3)

    def test_undeclared_variable_in_event(self):
        src = (
            "PLAYER health = 100\n"
            "WHEN enemy_attack\n"
            "    gems -= 20\n"
        )
        with self.assertRaises(SemanticError):
            _analyze(src)

    def test_assignment_with_equal(self):
        """IDENTIFIER = VALUE inside an event should also work."""
        src = (
            "PLAYER health = 100\n"
            "WHEN enemy_attack\n"
            "    health = 50\n"
        )
        _analyze(src)  # should not raise


if __name__ == "__main__":
    unittest.main()
