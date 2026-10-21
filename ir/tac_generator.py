"""
GameForge Compiler -- TAC Generator (Phase 4)
=============================================
Walks the validated AST produced by the semantic analyzer and emits a
flat list of TAC instructions.

Design notes
------------
* One single pass over the AST -- no multi-pass look-ahead required.
* Each AST node type maps to a small set of TAC instructions.
* Event handler bodies are wrapped in LABEL … RETURN pairs so the runtime
  can locate and execute them independently.
* IF statements produce conditional branches with auto-generated labels.
* Temporary variables are NOT needed for the current GameScript grammar
  (all assignments use a single variable on the left and a single
  literal/identifier on the right).  They would be required if the
  grammar supported compound expressions like  x = a + b - c.
* Labels are generated with a monotonically increasing counter to
  guarantee uniqueness across the entire instruction list.
"""

from parser.ast_nodes import (
    ProgramNode, PlayerDeclarationNode, EventNode, IfNode,
    AssignmentNode, CommandNode, LiteralNode, IdentifierNode,
)
from .instructions import (
    Instruction, DeclareInstr, MovInstr, AddInstr, SubInstr,
    LabelInstr, GotoInstr, IfInstr, ReturnInstr, CommandInstr,
    REL_OP_TO_IF,
)


class TACGenerator:
    """Converts a validated AST into a list of TAC instructions."""

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self._instructions: list[Instruction] = []
        self._label_counter: int = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(self, program: ProgramNode) -> list[Instruction]:
        """
        Walk *program* and produce the full TAC instruction list.
        Returns the list so the caller can store or display it.
        """
        self._instructions = []
        self._label_counter = 0

        self._log_header()
        self._log("Generating TAC instructions...")

        for stmt in program.statements:
            if isinstance(stmt, PlayerDeclarationNode):
                self._gen_player_declaration(stmt)
            elif isinstance(stmt, EventNode):
                self._gen_event(stmt)
            elif isinstance(stmt, IfNode):
                self._gen_if(stmt)
            else:
                raise ValueError(
                    f"[TAC] Unknown statement type: {type(stmt).__name__}"
                )

        self._log_tac()
        return self._instructions

    # ------------------------------------------------------------------
    # Node generators
    # ------------------------------------------------------------------

    def _gen_player_declaration(self, node: PlayerDeclarationNode):
        """PLAYER name = value  ->  DECLARE name, value"""
        self._log(f"  PlayerDeclaration: {node.name.name} = {node.value.value}")
        instr = DeclareInstr(dest=node.name.name, value=node.value.value,
                             line=node.line)
        self._emit(instr)

    def _gen_event(self, node: EventNode):
        """
        WHEN event_name
            body...
        ->
            LABEL  event_<name>
            <body instructions>
            RETURN
        """
        label_name = f"event_{node.name.name}"
        self._log(f"  EventNode: {node.name.name} -> LABEL {label_name}")
        self._emit(LabelInstr(name=label_name, line=node.line))

        for action in node.body:
            self._gen_action(action)

        self._emit(ReturnInstr(line=node.line))

    def _gen_if(self, node: IfNode):
        """
        IF left op right
            body...
        ->
            IF_<op>  left, right, L_true
            GOTO     L_end
            LABEL    L_true
            <body instructions>
            LABEL    L_end
        """
        # Generate unique labels
        true_label = self._new_label()
        end_label  = self._new_label()

        cond = node.condition
        left  = cond.left.name
        right = self._operand(cond.right)
        if_op = REL_OP_TO_IF.get(cond.operator, "IF_LE")

        self._log(
            f"  IfNode: {left} {cond.operator} {right}"
            f" -> {if_op} / labels {true_label}, {end_label}"
        )

        self._emit(IfInstr(if_opcode=if_op, src1=left, src2=right,
                           target=true_label, line=node.line))
        self._emit(GotoInstr(target=end_label, line=node.line))
        self._emit(LabelInstr(name=true_label, line=node.line))

        for action in node.body:
            self._gen_action(action)

        self._emit(LabelInstr(name=end_label, line=node.line))

    # ------------------------------------------------------------------
    # Action generators (used inside event bodies and IF bodies)
    # ------------------------------------------------------------------

    def _gen_action(self, node):
        if isinstance(node, AssignmentNode):
            self._gen_assignment(node)
        elif isinstance(node, CommandNode):
            self._gen_command(node)
        else:
            raise ValueError(
                f"[TAC] Unknown action type: {type(node).__name__}"
            )

    def _gen_assignment(self, node: AssignmentNode):
        """
        Three cases:

          var = value    ->  MOV  var, value
          var += value   ->  ADD  var, var, value
          var -= value   ->  SUB  var, var, value
        """
        var   = node.variable.name
        value = self._operand(node.value)
        op    = node.operator

        self._log(f"  Assignment: {var} {op} {value}")

        if op == "=":
            self._emit(MovInstr(dest=var, src=value, line=node.line))
        elif op == "+=":
            self._emit(AddInstr(dest=var, src1=var, src2=value, line=node.line))
        elif op == "-=":
            self._emit(SubInstr(dest=var, src1=var, src2=value, line=node.line))
        else:
            raise ValueError(f"[TAC] Unknown assignment operator: {op}")

    def _gen_command(self, node: CommandNode):
        """GAME_OVER / LEVEL_COMPLETE  ->  COMMAND GAME_OVER / LEVEL_COMPLETE"""
        self._log(f"  Command: {node.name}")
        self._emit(CommandInstr(name=node.name, line=node.line))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _operand(self, node) -> "str | int":
        """Convert a LiteralNode or IdentifierNode to a TAC operand value."""
        if isinstance(node, LiteralNode):
            return node.value       # int
        if isinstance(node, IdentifierNode):
            return node.name        # str
        raise ValueError(f"[TAC] Unknown operand node: {type(node).__name__}")

    def _new_label(self) -> str:
        """Generate the next unique label string, e.g. L1, L2, L3 …"""
        self._label_counter += 1
        return f"L{self._label_counter}"

    def _emit(self, instr: Instruction):
        self._instructions.append(instr)

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def _log(self, msg: str):
        if self.verbose:
            print(f"  [TAC GEN] {msg}")

    def _log_header(self):
        if not self.verbose:
            return
        print()
        print("=" * 60)
        print("  PHASE 4: TAC GENERATION")
        print("=" * 60)
        print()

    def _log_tac(self):
        if not self.verbose:
            return
        print()
        print("-" * 60)
        print("  THREE-ADDRESS CODE")
        print("-" * 60)
        for i, instr in enumerate(self._instructions, start=1):
            print(f"  {i:04d}  {instr}")
        print()
        print(f"  TAC instructions generated: {len(self._instructions)}")
        print()
        print("  PHASE 4 COMPLETE")
        print("  [OK] TAC generation successful")
        print("=" * 60)
