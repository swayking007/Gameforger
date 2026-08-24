# GameForge Compiler

A Domain-Specific Language (DSL) compiler for **GameScript** -- a small language
designed to express simple game logic.  Built as a Compiler Design course
project.

## What is GameForge?

GameForge is an educational compiler that processes GameScript source code
through three phases of compilation: lexical analysis, syntax analysis, and
semantic analysis.  It demonstrates real compiler techniques -- every phase
performs genuine processing on the input.

## What is GameScript?

GameScript is a minimal DSL for describing game variables, events, conditions,
and commands.  It uses indentation-based blocks (similar to Python) and a small
fixed vocabulary.

## Current Status

**Currently implemented: Phase 1, Phase 2, Phase 3.**

| Phase | Name              | Status |
|-------|-------------------|--------|
| 1     | Lexical Analysis  | Done   |
| 2     | Syntax Analysis   | Done   |
| 3     | Semantic Analysis | Done   |
| 4     | IR Generation     | Future |
| 5     | Optimization      | Future |
| 6     | Execution Engine  | Future |

---

## Language Syntax

### Variable Declarations

```
PLAYER health = 100
PLAYER coins = 0
```

### Events

```
WHEN enemy_attack
    health -= 20

WHEN collect_coin
    coins += 10
```

Supported events: `enemy_attack`, `collect_coin`, `player_move`.

### Conditions

```
IF health <= 0
    GAME_OVER

IF coins >= 10
    LEVEL_COMPLETE
```

Relational operators: `>`, `<`, `>=`, `<=`, `==`, `!=`

### Assignment Operators

`=`, `+=`, `-=`

### Commands

`GAME_OVER`, `LEVEL_COMPLETE`

### Comments

```
# This is a comment
```

---

## Grammar

```
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
```

---

## Token Types

| Token              | Example         |
|--------------------|-----------------|
| KEYWORD_PLAYER     | `PLAYER`        |
| KEYWORD_WHEN       | `WHEN`          |
| KEYWORD_IF         | `IF`            |
| IDENTIFIER         | `health`        |
| NUMBER             | `100`           |
| ASSIGN             | `=`             |
| PLUS_ASSIGN        | `+=`            |
| MINUS_ASSIGN       | `-=`            |
| GREATER            | `>`             |
| LESS               | `<`             |
| GREATER_EQUAL      | `>=`            |
| LESS_EQUAL         | `<=`            |
| EQUAL_EQUAL        | `==`            |
| NOT_EQUAL          | `!=`            |
| COMMAND_GAME_OVER  | `GAME_OVER`     |
| COMMAND_LEVEL_COMPLETE | `LEVEL_COMPLETE` |
| NEWLINE            | end of line     |
| INDENT             | increased indent|
| DEDENT             | decreased indent|
| EOF                | end of file     |

---

## AST Structure

```
ProgramNode
  +-- PlayerDeclarationNode (name, value)
  +-- EventNode (name, body: [actions])
  +-- IfNode (condition, body: [actions])

Actions:
  +-- AssignmentNode (variable, operator, value)
  +-- CommandNode (name)

Expressions:
  +-- ConditionNode (left, operator, right)
  +-- LiteralNode (integer value)
  +-- IdentifierNode (variable name)
```

---

## Semantic Rules

| Rule | Description |
|------|-------------|
| 1    | Variables must be declared with `PLAYER` before use |
| 2    | No duplicate `PLAYER` declarations |
| 3    | Numeric operations require numeric operands |
| 4    | Events must be from the supported event list |
| 5    | Condition variables must exist in the symbol table |
| 6    | Condition operands must be numeric |

---

## Project Structure

```
gameforge/
|
+-- main.py                        # Compiler driver
|
+-- lexer/
|   +-- __init__.py
|   +-- token.py                   # Token/TokenType definitions
|   +-- lexer.py                   # Hand-written scanner
|
+-- parser/
|   +-- __init__.py
|   +-- ast_nodes.py               # AST node dataclasses
|   +-- parser.py                  # Recursive-descent parser
|
+-- semantic/
|   +-- __init__.py
|   +-- symbol_table.py            # Dictionary-backed symbol table
|   +-- semantic_analyzer.py       # Semantic rule checker
|
+-- errors/
|   +-- __init__.py
|   +-- errors.py                  # LexicalError, SyntaxError, SemanticError
|
+-- examples/
|   +-- basic.gs                   # Valid full program
|   +-- valid_conditions.gs        # Multiple conditions
|   +-- lexical_error.gs           # Invalid character '@'
|   +-- syntax_error.gs            # Missing identifier
|   +-- semantic_error.gs          # Undeclared variable
|   +-- duplicate_var.gs           # Duplicate declaration
|   +-- unknown_event.gs           # Misspelled event
|
+-- tests/
|   +-- __init__.py
|   +-- test_compiler.py           # 29 unit tests
|
+-- README.md
```

---

## How to Run

### Compile a GameScript file (verbose output)

```bash
python main.py examples/basic.gs
```

### Compile with quiet output

```bash
python main.py examples/basic.gs -q
```

### Compile the default example

```bash
python main.py
```

### Run the test suite

```bash
python -m unittest tests.test_compiler -v
```

---

## Example Program

```
PLAYER health = 100
PLAYER coins = 0
PLAYER score = 0

WHEN enemy_attack
    health -= 20

WHEN collect_coin
    coins += 10

WHEN player_move
    score += 5

IF health <= 0
    GAME_OVER
```

---

## Example Output (abbreviated)

```
============================================================
  GAMEFORGE COMPILER
============================================================
  Source file : examples/basic.gs

  PHASE 1: LEXICAL ANALYSIS   ... [OK]
  TOKEN STREAM: 52 tokens generated

  PHASE 2: SYNTAX ANALYSIS    ... [OK]
  AST: 7 statements parsed

  PHASE 3: SEMANTIC ANALYSIS  ... [OK]
  SYMBOL TABLE:
    health    INTEGER  100   line 4
    coins     INTEGER  0     line 5
    score     INTEGER  0     line 6

============================================================
  COMPILATION SUCCESSFUL
============================================================
  [OK] Phase 1 -- Lexical Analysis
  [OK] Phase 2 -- Syntax Analysis
  [OK] Phase 3 -- Semantic Analysis

  Phases 1-3 completed successfully.
============================================================
```

---

## Indentation Design Decision

GameScript uses indentation for `WHEN` and `IF` blocks.  The lexer converts
leading whitespace into explicit `INDENT` / `DEDENT` tokens using an
indent-level stack -- the same approach as CPython's tokenizer, but simplified.

Only spaces are accepted (no tabs).  The indent stack starts at level 0.
When the indentation of a new line exceeds the current level, an `INDENT` token
is emitted.  When it decreases, one or more `DEDENT` tokens are emitted.
Inconsistent indentation raises a `LexicalError`.

---

## Known Limitations

- Only integer values are supported (no strings, floats, or booleans).
- No complex boolean expressions (`AND` / `OR`).
- Fixed set of 3 events.
- No user-defined functions or procedures.
- No loops.
- No execution engine -- compilation stops at semantic validation.
- No IR, optimization, or code generation yet.

---

## Future Phases

The compiler is structured for easy extension:

| Phase | Feature                   |
|-------|---------------------------|
| 4     | Intermediate Representation |
| 5     | Optimization              |
| 6     | Execution Engine          |
| 7     | AI Integration            |

These will be added in subsequent milestones.

---

## Requirements

- Python 3.10+ (uses `match` type hints like `X | Y`)
- No external dependencies -- standard library only.
