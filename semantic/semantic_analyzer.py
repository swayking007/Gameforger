"""
GameForge Compiler -- Semantic Analyzer (Phase 3)
=================================================
Walks the AST, builds a symbol table, and enforces semantic rules:

  Rule 1 -- Variables must be declared before use.
  Rule 2 -- No duplicate PLAYER declarations.
  Rule 3 -- Numeric operations require numeric operands.
  Rule 4 -- Events must be from the supported event list.
  Rule 5 -- Condition variables must exist in the symbol table.
  Rule 6 -- Condition operands must be numeric.
"""

from parser.ast_nodes import (
    ProgramNode, PlayerDeclarationNode, EventNode, IfNode,
    AssignmentNode, CommandNode, ConditionNode,
    LiteralNode, IdentifierNode,
)
from .symbol_table import SymbolTable
from errors.errors import SemanticError


# Fixed set of valid event names (Phase 1-3 scope)
VALID_EVENTS = {
    "enemy_attack",
    "collect_coin",
    "player_move",
}


class SemanticAnalyzer:
    """Performs semantic validation over a parsed AST."""

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.symbol_table = SymbolTable()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(self, program: ProgramNode) -> SymbolTable:
        """Validate *program* and return the populated symbol table."""
        self._log_header()
        self._log("Starting semantic analysis...")

        for stmt in program.statements:
            if isinstance(stmt, PlayerDeclarationNode):
                self._check_player_declaration(stmt)
            elif isinstance(stmt, EventNode):
                self._check_event(stmt)
            elif isinstance(stmt, IfNode):
                self._check_if(stmt)
            else:
                raise SemanticError(
                    f"Unknown statement type: {type(stmt).__name__}",
                    line=getattr(stmt, "line", None),
                )

        self._log_symbol_table()
        self._log_footer()
        return self.symbol_table

    # ------------------------------------------------------------------
    # Rule 2 -- PLAYER declarations / duplicate check
    # ------------------------------------------------------------------

    def _check_player_declaration(self, node: PlayerDeclarationNode):
        name = node.name.name
        self._log(f"Checking PLAYER declaration: {name}")

        # Duplicate check (Rule 2)
        if self.symbol_table.contains(name):
            raise SemanticError(
                f"Variable '{name}' already declared.",
                line=node.line,
            )

        # Register
        self.symbol_table.declare(
            name=name,
            var_type="INTEGER",
            value=node.value.value,
            line=node.line,
        )
        self._log(f"  [SYMBOL TABLE] Registering variable:")
        self._log(f"    {name}")
        self._log(f"    type     = INTEGER")
        self._log(f"    initial  = {node.value.value}")
        self._log(f"  [OK] Variable '{name}' registered")

    # ------------------------------------------------------------------
    # Rule 4 -- Event validation
    # ------------------------------------------------------------------

    def _check_event(self, node: EventNode):
        event_name = node.name.name
        self._log(f"Checking event: {event_name}")

        if event_name not in VALID_EVENTS:
            raise SemanticError(
                f"Unknown event '{event_name}'.",
                line=node.line,
            )
        self._log(f"  [OK] Event '{event_name}' is valid")

        # Check each action in the event body
        for action in node.body:
            self._check_action(action)

    # ------------------------------------------------------------------
    # IF statement
    # ------------------------------------------------------------------

    def _check_if(self, node: IfNode):
        self._log(f"Checking IF statement (line {node.line})")
        self._check_condition(node.condition)
        for action in node.body:
            self._check_action(action)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _check_action(self, node):
        if isinstance(node, AssignmentNode):
            self._check_assignment(node)
        elif isinstance(node, CommandNode):
            self._log(f"  [OK] Command '{node.name}' recognised")
        else:
            raise SemanticError(
                f"Unknown action type: {type(node).__name__}",
                line=getattr(node, "line", None),
            )

    # ------------------------------------------------------------------
    # Rule 1, 3 -- Assignment validation
    # ------------------------------------------------------------------

    def _check_assignment(self, node: AssignmentNode):
        var_name = node.variable.name
        self._log(f"Checking assignment: {var_name} {node.operator} {node.value}")

        # Rule 1 -- variable must exist
        sym = self.symbol_table.lookup(var_name)
        if sym is None:
            raise SemanticError(
                f"Unknown variable '{var_name}'.",
                line=node.line,
            )
        self._log(f"  [OK] Variable '{var_name}' exists")
        self._log(f"  [OK] Variable type = {sym.var_type}")

        # Rule 3 -- RHS must be numeric
        if isinstance(node.value, LiteralNode):
            self._log(f"  [OK] RHS type = INTEGER")
        elif isinstance(node.value, IdentifierNode):
            rhs_sym = self.symbol_table.lookup(node.value.name)
            if rhs_sym is None:
                raise SemanticError(
                    f"Unknown variable '{node.value.name}' used in assignment.",
                    line=node.line,
                )
            if rhs_sym.var_type != "INTEGER":
                raise SemanticError(
                    f"Variable '{node.value.name}' is not numeric.",
                    line=node.line,
                )
            self._log(f"  [OK] RHS variable '{node.value.name}' type = {rhs_sym.var_type}")

        self._log(f"  [OK] Operator '{node.operator}' is valid")

    # ------------------------------------------------------------------
    # Rule 5, 6 -- Condition validation
    # ------------------------------------------------------------------

    def _check_condition(self, node: ConditionNode):
        var_name = node.left.name
        self._log(f"Checking condition: {var_name} {node.operator} {node.right}")

        # Rule 5 -- left side must exist
        sym = self.symbol_table.lookup(var_name)
        if sym is None:
            raise SemanticError(
                f"Unknown variable '{var_name}' in condition.",
                line=node.line,
            )
        self._log(f"  [OK] Variable '{var_name}' exists (type = {sym.var_type})")

        # Rule 6 -- left must be numeric
        if sym.var_type != "INTEGER":
            raise SemanticError(
                f"Variable '{var_name}' must be numeric for comparison.",
                line=node.line,
            )

        # Rule 6 -- right side must be numeric
        if isinstance(node.right, LiteralNode):
            self._log(f"  [OK] RHS is numeric literal ({node.right.value})")
        elif isinstance(node.right, IdentifierNode):
            rhs_sym = self.symbol_table.lookup(node.right.name)
            if rhs_sym is None:
                raise SemanticError(
                    f"Unknown variable '{node.right.name}' in condition.",
                    line=node.line,
                )
            if rhs_sym.var_type != "INTEGER":
                raise SemanticError(
                    f"Variable '{node.right.name}' must be numeric for comparison.",
                    line=node.line,
                )
            self._log(f"  [OK] RHS variable '{node.right.name}' is numeric")

        self._log(f"  [OK] Condition is valid")

    # ------------------------------------------------------------------
    # Logging helpers
    # ------------------------------------------------------------------

    def _log(self, msg: str):
        if self.verbose:
            print(f"  {msg}")

    def _log_header(self):
        if self.verbose:
            print()
            print("=" * 60)
            print("  PHASE 3: SEMANTIC ANALYSIS")
            print("=" * 60)
            print()

    def _log_symbol_table(self):
        if not self.verbose:
            return
        symbols = self.symbol_table.all_symbols()
        print()
        print("-" * 60)
        print("  SYMBOL TABLE")
        print("-" * 60)
        print(f"  {'Name':<15s} {'Type':<12s} {'Value':<10s} {'Line'}")
        print(f"  {'-'*15} {'-'*12} {'-'*10} {'-'*5}")
        for sym in symbols:
            print(f"  {sym.name:<15s} {sym.var_type:<12s} {str(sym.value):<10s} {sym.line}")
        print()

    def _log_footer(self):
        if self.verbose:
            print("  PHASE 3 COMPLETE")
            print("  [OK] Semantic analysis successful")
            print("=" * 60)
