"""
GameForge Compiler -- AST Node Definitions
==========================================
Simple dataclass-based AST nodes.  Every node carries the source line number
so that later phases (semantic analysis, error reporting) can refer back to it.
"""

from dataclasses import dataclass, field
from typing import List


# ------------------------------------------------------------------
# Leaf nodes
# ------------------------------------------------------------------

@dataclass
class LiteralNode:
    """A numeric literal (e.g. 100)."""
    value: int
    line: int

    def __repr__(self):
        return f"Literal({self.value})"


@dataclass
class IdentifierNode:
    """A variable or event name (e.g. health, enemy_attack)."""
    name: str
    line: int

    def __repr__(self):
        return f"Identifier({self.name})"


# ------------------------------------------------------------------
# Expression / condition nodes
# ------------------------------------------------------------------

@dataclass
class ConditionNode:
    """A simple relational condition: <left> <op> <right>."""
    left: IdentifierNode
    operator: str            # ">", "<", ">=", "<=", "==", "!="
    right: "LiteralNode | IdentifierNode"
    line: int

    def __repr__(self):
        return f"Condition({self.left.name} {self.operator} {self.right})"


# ------------------------------------------------------------------
# Statement nodes
# ------------------------------------------------------------------

@dataclass
class AssignmentNode:
    """An assignment: <variable> <op> <value> where op is =, +=, or -=."""
    variable: IdentifierNode
    operator: str            # "=", "+=", "-="
    value: "LiteralNode | IdentifierNode"
    line: int

    def __repr__(self):
        return f"Assignment({self.variable.name} {self.operator} {self.value})"


@dataclass
class CommandNode:
    """A built-in command like GAME_OVER or LEVEL_COMPLETE."""
    name: str
    line: int

    def __repr__(self):
        return f"Command({self.name})"


@dataclass
class PlayerDeclarationNode:
    """PLAYER <name> = <value>"""
    name: IdentifierNode
    value: LiteralNode
    line: int

    def __repr__(self):
        return f"PlayerDeclaration({self.name.name} = {self.value.value})"


@dataclass
class EventNode:
    """WHEN <event_name> followed by an indented body of actions."""
    name: IdentifierNode
    body: List["AssignmentNode | CommandNode"] = field(default_factory=list)
    line: int = 0

    def __repr__(self):
        return f"Event({self.name.name}, body={self.body})"


@dataclass
class IfNode:
    """IF <condition> followed by an indented body of actions."""
    condition: ConditionNode
    body: List["AssignmentNode | CommandNode"] = field(default_factory=list)
    line: int = 0

    def __repr__(self):
        return f"If({self.condition}, body={self.body})"


# ------------------------------------------------------------------
# Root node
# ------------------------------------------------------------------

@dataclass
class ProgramNode:
    """The root of the AST -- a sequence of top-level statements."""
    statements: List["PlayerDeclarationNode | EventNode | IfNode"] = field(
        default_factory=list
    )

    def __repr__(self):
        return f"Program({len(self.statements)} statements)"
