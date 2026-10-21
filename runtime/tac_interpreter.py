"""
GameForge Compiler -- TAC Interpreter (Phase 6)
===============================================

Executes a flat list of TAC instructions produced by the TACGenerator
(or the Optimizer).  The interpreter does NOT re-parse GameScript source.

Architecture
------------
1. Initialization pass
   Scans all DECLARE instructions and populates the GameState.
   Scans all LABEL instructions and builds a label -> index map.

2. Top-level evaluation pass
   Executes instructions that appear OUTSIDE event handler labels:
     - Top-level IF conditions are evaluated here.
     - DECLARE instructions are skipped (already processed).
     - Event LABEL … RETURN blocks are skipped (registered, not executed).

3. Event execution
   When the user triggers an event, execute its block from
   LABEL event_<name>  (exclusive) to RETURN (inclusive).

Condition evaluation semantics
-------------------------------
Top-level IF conditions are evaluated ONCE -- after initialization and
after EACH event completes -- in the order they appear in the TAC.
This means:
  * IF health <= 0  is checked at startup (initial values may already
    satisfy it) and again after every event changes variables.
  * This is consistent with the "game rule" interpretation: conditions
    represent persistent game rules that are re-evaluated continually.

Runtime error handling
-----------------------
All runtime errors produce a RuntimeError message that is appended to the
game log.  They do not raise Python exceptions to the caller; instead the
interpreter sets a safe error state.
"""

from ir.instructions import (
    Instruction, DeclareInstr, MovInstr, AddInstr, SubInstr,
    LabelInstr, GotoInstr, IfInstr, ReturnInstr, CommandInstr,
)
from .game_state import GameState


class TACInterpreter:
    """
    Executes a TAC instruction list against a GameState.

    Usage:
        interp = TACInterpreter(instructions, verbose=True)
        state  = interp.initialize()       # sets up variables
        log    = interp.trigger_event("enemy_attack", state)
    """

    def __init__(self, instructions: list[Instruction], verbose: bool = True):
        self.instructions = instructions
        self.verbose = verbose

        # Built during initialize()
        self._label_index: dict[str, int] = {}   # label name -> instruction index
        self._event_labels: list[str]     = []   # event_* labels in order
        self._state: GameState | None     = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def initialize(self) -> GameState:
        """
        Scan the instruction list, build the label map, populate a fresh
        GameState from DECLARE instructions, and run the top-level IF
        evaluation pass.

        Returns the initialised GameState.
        """
        self._log_section("Initializing game state")

        state = GameState()
        self._label_index = {}
        self._event_labels = []

        # --- Pass 1: build label index and collect event labels ---
        for i, instr in enumerate(self.instructions):
            if isinstance(instr, LabelInstr):
                if instr.name in self._label_index:
                    self._log(f"WARNING: duplicate label '{instr.name}' at index {i}")
                self._label_index[instr.name] = i
                if instr.name.startswith("event_"):
                    self._event_labels.append(instr.name)
                    self._log(f"Registered event handler: {instr.name}")

        # --- Pass 2: execute DECLARE instructions ---
        for instr in self.instructions:
            if isinstance(instr, DeclareInstr):
                state.init_variable(instr.dest, instr.value)
                self._log(f"  {instr.dest} = {instr.value}")

        self._state = state

        # Display initial state
        self._log_section("Initial game state")
        for name in state.all_variables():
            val = state.get(name)
            state.append_log(f"  {name} = {val}")
            self._log(f"  {name} = {val}")

        # --- Pass 3: evaluate top-level IF conditions ---
        self._run_top_level_ifs(state)

        return state

    def trigger_event(self, event_name: str, state: GameState) -> list[str]:
        """
        Execute the TAC handler for *event_name* and update *state*.
        Returns a list of log lines produced during this execution.

        *event_name* must be one of the registered event names (without the
        'event_' prefix, e.g. "enemy_attack").

        The game state persists between calls (variables are NOT reset).
        """
        label_name = f"event_{event_name}"
        if label_name not in self._label_index:
            msg = f"Runtime error: No handler registered for event '{event_name}'"
            state.append_log(msg)
            self._log(msg)
            return [msg]

        log_before = list(state.log)

        self._log_section(f"Triggering event: {event_name}")
        state.append_log(f"\nEvent Triggered: {event_name}")

        start_idx = self._label_index[label_name]
        # Execute instructions after the LABEL until RETURN
        self._execute_block(start_idx + 1, state)

        # After the event, re-evaluate top-level IF conditions
        self._run_top_level_ifs(state)

        # Return only new log lines
        new_log = state.log[len(log_before):]
        return new_log

    def registered_events(self) -> list[str]:
        """
        Return the list of registered event names (without the 'event_' prefix).
        """
        return [lbl[len("event_"):] for lbl in self._event_labels]

    # ------------------------------------------------------------------
    # Instruction execution engine
    # ------------------------------------------------------------------

    def _execute_block(self, start: int, state: GameState):
        """
        Execute instructions from *start* until RETURN or end of list.
        Supports GOTO and conditional IF_* jumps.
        """
        pc = start
        max_steps = len(self.instructions) * 2 + 100   # safety guard

        while pc < len(self.instructions) and max_steps > 0:
            max_steps -= 1
            instr = self.instructions[pc]

            if isinstance(instr, ReturnInstr):
                self._log("  [RETURN] Event handler finished")
                state.append_log("[RETURN]")
                break

            # Skip nested labels (don't execute another event block)
            if isinstance(instr, LabelInstr):
                break

            pc = self._execute_one(instr, pc, state)

        if max_steps <= 0:
            msg = "Runtime error: Execution limit exceeded (possible infinite loop)"
            state.append_log(msg)
            self._log(msg)

    def _execute_one(self, instr: Instruction, pc: int, state: GameState) -> int:
        """
        Execute *instr* and return the next program counter value.
        Falls back to pc+1 for sequential execution.
        """
        try:
            if isinstance(instr, DeclareInstr):
                # Already processed during initialization
                return pc + 1

            elif isinstance(instr, MovInstr):
                val = self._resolve(instr.src, state)
                old = state.get(instr.dest) if state.contains(instr.dest) else None
                state.set(instr.dest, val)
                self._log_change(instr.dest, old, val, state)
                return pc + 1

            elif isinstance(instr, AddInstr):
                v1 = self._resolve(instr.src1, state)
                v2 = self._resolve(instr.src2, state)
                old = state.get(instr.dest) if state.contains(instr.dest) else None
                result = v1 + v2
                state.set(instr.dest, result)
                self._log(f"  ADD {instr.dest}, {instr.src1}, {instr.src2}")
                self._log_change(instr.dest, old, result, state)
                return pc + 1

            elif isinstance(instr, SubInstr):
                v1 = self._resolve(instr.src1, state)
                v2 = self._resolve(instr.src2, state)
                old = state.get(instr.dest) if state.contains(instr.dest) else None
                result = v1 - v2
                state.set(instr.dest, result)
                self._log(f"  SUB {instr.dest}, {instr.src1}, {instr.src2}")
                self._log_change(instr.dest, old, result, state)
                return pc + 1

            elif isinstance(instr, GotoInstr):
                target = instr.target
                if target not in self._label_index:
                    raise RuntimeError(f"Unknown label '{target}'")
                self._log(f"  GOTO {target}")
                return self._label_index[target] + 1   # skip the LABEL itself

            elif isinstance(instr, IfInstr):
                return self._execute_if(instr, pc, state)

            elif isinstance(instr, CommandInstr):
                return self._execute_command(instr, pc, state)

            elif isinstance(instr, LabelInstr):
                return pc + 1   # labels are no-ops during execution

            else:
                msg = f"Runtime error: Unknown TAC opcode '{instr.opcode()}'"
                state.append_log(msg)
                self._log(msg)
                return pc + 1

        except KeyError as e:
            msg = str(e)
            state.append_log(msg)
            self._log(msg)
            return pc + 1

    def _execute_if(self, instr: IfInstr, pc: int, state: GameState) -> int:
        """Evaluate a conditional branch and return the next PC."""
        v1 = self._resolve(instr.src1, state)
        v2 = self._resolve(instr.src2, state)
        op = instr.if_opcode

        cond = self._evaluate_condition(op, v1, v2)
        self._log(f"  {op} {instr.src1}({v1}), {instr.src2}({v2}) -> {'TRUE' if cond else 'FALSE'}")

        if cond:
            if instr.target not in self._label_index:
                msg = f"Runtime error: Unknown label '{instr.target}'"
                state.append_log(msg)
                self._log(msg)
                return pc + 1
            return self._label_index[instr.target] + 1
        else:
            return pc + 1

    def _execute_command(self, instr: CommandInstr, pc: int, state: GameState) -> int:
        """Execute a built-in game command."""
        cmd = instr.name
        self._log(f"  COMMAND {cmd}")

        if cmd == "GAME_OVER":
            state.set_game_over()
            msg = ">>> GAME OVER <<<"
            state.append_log(msg)
            self._log(msg)
        elif cmd == "LEVEL_COMPLETE":
            state.set_level_complete()
            msg = ">>> LEVEL COMPLETE <<<"
            state.append_log(msg)
            self._log(msg)
        else:
            msg = f"Runtime error: Unknown command '{cmd}'"
            state.append_log(msg)
            self._log(msg)

        return pc + 1

    # ------------------------------------------------------------------
    # Top-level IF evaluation
    # ------------------------------------------------------------------

    def _run_top_level_ifs(self, state: GameState):
        """
        Walk the top-level TAC and execute any IF_* / GOTO / LABEL / COMMAND
        sequences that appear outside event handler blocks.

        Top-level IFs are those that are not inside any LABEL event_… RETURN
        block.  They represent game rules that are evaluated continuously.
        """
        in_event = False
        pc = 0

        while pc < len(self.instructions):
            instr = self.instructions[pc]

            if isinstance(instr, LabelInstr):
                if instr.name.startswith("event_"):
                    in_event = True
                else:
                    # This is a generated control-flow label (L1, L2 …)
                    # We may land here via GOTO during top-level evaluation
                    pass
                pc += 1
                continue

            if isinstance(instr, ReturnInstr):
                in_event = False
                pc += 1
                continue

            if in_event:
                pc += 1
                continue

            # Execute top-level control flow
            if isinstance(instr, (IfInstr, GotoInstr, CommandInstr, MovInstr,
                                   AddInstr, SubInstr)):
                pc = self._execute_one(instr, pc, state)
            else:
                pc += 1

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _resolve(self, operand: "str | int", state: GameState) -> int:
        """Resolve an operand to its integer value."""
        if isinstance(operand, int):
            return operand
        # It must be a variable name
        return state.get(operand)

    @staticmethod
    def _evaluate_condition(op: str, v1: int, v2: int) -> bool:
        """Evaluate a relational operator."""
        ops = {
            "IF_LE": v1 <= v2,
            "IF_LT": v1 <  v2,
            "IF_GE": v1 >= v2,
            "IF_GT": v1 >  v2,
            "IF_EQ": v1 == v2,
            "IF_NE": v1 != v2,
        }
        if op not in ops:
            raise RuntimeError(f"Unknown conditional operator: {op}")
        return ops[op]

    def _log_change(self, name: str, old, new: int, state: GameState):
        """Log and record a variable value change."""
        if old is not None and old != new:
            msg = f"  {name}: {old} -> {new}"
            state.append_log(msg)
            self._log(msg)
        elif old is None:
            msg = f"  {name} = {new}"
            state.append_log(msg)
            self._log(msg)

    def _log(self, msg: str):
        if self.verbose:
            print(f"  [EXECUTOR] {msg}")

    def _log_section(self, title: str):
        if self.verbose:
            print()
            print(f"  [EXECUTOR] {title}")
            print(f"  {'-' * (len(title) + 2)}")
