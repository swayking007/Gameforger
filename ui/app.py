"""
GameForge -- Compiler Playground UI (Phase 7)
=============================================
A clean, dark-themed Tkinter interface with:

  A. GameScript Editor (with syntax highlighting)
  B. Compiler Pipeline Status Panel
  C. Tokens Viewer
  D. AST Viewer
  E. Symbol Table Viewer
  F. Three-Address Code Viewer
  G. Optimization Comparison Panel
  H. Execution Controls (event selector + trigger button)
  I. Execution Output / Mega Output Box
  J. Error and Status Panel

Launch:
    python ui/app.py
"""

import sys
import os
import tkinter as tk
import tkinter.ttk as ttk
import tkinter.font as tkfont
from tkinter import scrolledtext

# Ensure project root is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from compiler_service import compile_source, STATUS_PASSED, STATUS_FAILED, STATUS_SKIPPED
from runtime import TACInterpreter
from ir.tac_printer import TACPrinter
from parser.ast_nodes import (
    ProgramNode, PlayerDeclarationNode, EventNode, IfNode,
    AssignmentNode, CommandNode, ConditionNode,
    LiteralNode, IdentifierNode,
)
from platformer import PlatformerCanvas, CompilerGameBridge


# ===========================================================================
# Design tokens
# ===========================================================================

BG          = "#0f1117"   # main background
BG2         = "#161b22"   # panel background
BG3         = "#1c2333"   # widget background
BORDER      = "#30363d"   # subtle borders
ACCENT      = "#58a6ff"   # blue accent
ACCENT2     = "#3fb950"   # green
ACCENT3     = "#f78166"   # red / error
ACCENT4     = "#e3b341"   # yellow / warning
FG          = "#c9d1d9"   # primary foreground
FG2         = "#8b949e"   # secondary foreground
FG3         = "#6e7681"   # dim text
MONO        = "Consolas"  # monospace font (falls back gracefully)
SANS        = "Segoe UI"
FONT_MONO   = (MONO, 10)
FONT_MONO_L = (MONO, 11)
FONT_SANS   = (SANS, 10)
FONT_SANS_S = (SANS, 9)
FONT_TITLE  = (SANS, 14, "bold")
FONT_HDR    = (SANS, 10, "bold")

STATUS_COLORS = {
    "Not Run":  FG3,
    "Running":  ACCENT4,
    "Passed":   ACCENT2,
    "Failed":   ACCENT3,
    "Skipped":  FG3,
}
STATUS_ICONS = {
    "Not Run":  "○",
    "Running":  "◌",
    "Passed":   "✓",
    "Failed":   "✗",
    "Skipped":  "—",
}

DEFAULT_SOURCE = """\
# GameScript -- basic example
# Edit me and click Compile!

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

IF coins >= 10
    LEVEL_COMPLETE
"""

EXAMPLES = {
    "Basic Program": DEFAULT_SOURCE,
    "Enemy Attack Only": """\
PLAYER health = 100

WHEN enemy_attack
    health -= 20

IF health <= 0
    GAME_OVER
""",
    "Coin Collection": """\
PLAYER coins = 0

WHEN collect_coin
    coins += 10

IF coins >= 10
    LEVEL_COMPLETE
""",
    "GAME_OVER Condition": """\
PLAYER health = 20

WHEN enemy_attack
    health -= 20

IF health <= 0
    GAME_OVER
""",
    "LEVEL_COMPLETE Condition": """\
PLAYER coins = 0

WHEN collect_coin
    coins += 10

IF coins >= 10
    LEVEL_COMPLETE
""",
    "Undeclared Variable (Error)": """\
WHEN enemy_attack
    gems -= 20
""",
    "Invalid Event (Error)": """\
PLAYER health = 100

WHEN enemy_attak
    health -= 20
""",
    "Syntax Error": """\
PLAYER = 100
""",
    "Lexical Error": """\
PLAYER health @= 100
""",
    "Platformer Demo (Mario)": """\
# GameScript -- Mario Platformer Demo
# Compiler-to-gameplay integration:
#   * Coins increase coins & score
#   * Enemy attacks reduce health
#   * Health <= 0 triggers GAME_OVER
#   * Coins >= 50 triggers LEVEL_COMPLETE

PLAYER health = 100
PLAYER coins = 0
PLAYER score = 0

WHEN collect_coin
    coins += 10
    score += 50

WHEN enemy_attack
    health -= 25

WHEN player_move
    score += 1

IF health <= 0
    GAME_OVER

IF coins >= 50
    LEVEL_COMPLETE
""",
    "No Optimization Applicable": """\
PLAYER health = 100
PLAYER coins = 0

WHEN enemy_attack
    health -= 20

WHEN collect_coin
    coins += 10

IF health <= 0
    GAME_OVER
""",
}


# ===========================================================================
# Main Application Window
# ===========================================================================

class GameForgeApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("GAMEFORGE — GameScript Compiler Playground")
        self.geometry("1360x860")
        self.minsize(1100, 700)
        self.configure(bg=BG)

        # State
        self._result = None
        self._interp = None
        self._state  = None
        self._is_source_stale = False

        # Compiler-Game Bridge
        self._bridge = CompilerGameBridge(
            get_interpreter=lambda: self._interp,
            get_state=lambda: self._state,
            is_stale_fn=lambda: self._is_source_stale,
            on_event_executed=self._on_bridge_event_executed,
        )

        self._setup_styles()
        self._build_layout()
        self._populate_default()

        # Keyboard shortcuts
        self.bind("<F5>", lambda e: self._on_compile())

    # -----------------------------------------------------------------------
    # Styles
    # -----------------------------------------------------------------------

    def _setup_styles(self):
        style = ttk.Style(self)
        style.theme_use("default")

        style.configure("TFrame",       background=BG)
        style.configure("Panel.TFrame", background=BG2)
        style.configure("TLabel",       background=BG,  foreground=FG,  font=FONT_SANS)
        style.configure("Panel.TLabel", background=BG2, foreground=FG,  font=FONT_SANS)
        style.configure("Hdr.TLabel",   background=BG2, foreground=ACCENT, font=FONT_HDR)
        style.configure("Dim.TLabel",   background=BG2, foreground=FG2, font=FONT_SANS_S)
        style.configure("Title.TLabel", background=BG,  foreground=ACCENT, font=FONT_TITLE)
        style.configure("TNotebook",    background=BG2, borderwidth=0)
        style.configure("TNotebook.Tab",
                        background=BG3, foreground=FG2,
                        padding=[10, 4], font=FONT_SANS_S)
        style.map("TNotebook.Tab",
                  background=[("selected", BG2)],
                  foreground=[("selected", ACCENT)])
        style.configure("TCheckbutton",
                        background=BG2, foreground=FG,
                        font=FONT_SANS, indicatorcolor=BG3,
                        selectcolor=ACCENT)
        style.configure("TCombobox",    background=BG3, foreground=FG,
                        fieldbackground=BG3, font=FONT_SANS)
        style.configure("TSeparator",   background=BORDER)

    # -----------------------------------------------------------------------
    # Layout
    # -----------------------------------------------------------------------

    def _build_layout(self):
        # ── Title bar ─────────────────────────────────────────────────
        title_bar = tk.Frame(self, bg=BG2, height=50)
        title_bar.pack(fill="x", side="top")
        title_bar.pack_propagate(False)

        tk.Label(title_bar, text="⬡ GAMEFORGE", bg=BG2,
                 fg=ACCENT, font=(SANS, 15, "bold")).pack(side="left", padx=20, pady=8)
        tk.Label(title_bar, text="GameScript Compiler Playground",
                 bg=BG2, fg=FG2, font=(SANS, 10)).pack(side="left", pady=8)

        sep = tk.Frame(self, bg=BORDER, height=1)
        sep.pack(fill="x")

        # ── Main panes ────────────────────────────────────────────────
        # Left column: Editor + Pipeline + Controls
        # Right column: Tabbed viewers + Output
        main = tk.PanedWindow(self, orient="horizontal",
                              bg=BG, sashwidth=4, sashrelief="flat",
                              sashpad=0)
        main.pack(fill="both", expand=True)

        left = self._build_left_column(main)
        right = self._build_right_column(main)

        main.add(left,  minsize=360, width=440)
        main.add(right, minsize=600)

    # -----------------------------------------------------------------------
    # Left column
    # -----------------------------------------------------------------------

    def _build_left_column(self, parent):
        frame = tk.Frame(parent, bg=BG)

        # Editor panel
        ed_frame = tk.Frame(frame, bg=BG2)
        ed_frame.pack(fill="both", expand=True, padx=6, pady=(6, 3))

        self._build_section_header(ed_frame, "A  GameScript Editor")

        # Toolbar: examples dropdown + buttons
        toolbar = tk.Frame(ed_frame, bg=BG2)
        toolbar.pack(fill="x", padx=6, pady=(2, 4))

        tk.Label(toolbar, text="Load Example:", bg=BG2, fg=FG2,
                 font=FONT_SANS_S).pack(side="left")
        self._example_var = tk.StringVar(value="Basic Program")
        combo = ttk.Combobox(toolbar, textvariable=self._example_var,
                             values=list(EXAMPLES.keys()), state="readonly",
                             width=22, font=FONT_SANS_S)
        combo.pack(side="left", padx=4)
        combo.bind("<<ComboboxSelected>>", self._on_example_selected)

        self._btn_reset = self._make_button(toolbar, "↺ Reset", self._on_reset,
                                            bg="#21262d", fg=FG2)
        self._btn_reset.pack(side="right", padx=(2, 0))
        self._btn_clear = self._make_button(toolbar, "✕ Clear Output",
                                            self._on_clear_output,
                                            bg="#21262d", fg=FG2)
        self._btn_clear.pack(side="right", padx=2)

        # Editor text widget
        self._editor = scrolledtext.ScrolledText(
            ed_frame, bg=BG3, fg=FG, insertbackground=ACCENT,
            font=FONT_MONO_L, relief="flat", bd=0,
            wrap="none", undo=True, selectbackground="#264f78",
        )
        self._editor.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        self._editor.bind("<KeyRelease>", self._on_source_edited)

        # Compile button
        compile_bar = tk.Frame(ed_frame, bg=BG2)
        compile_bar.pack(fill="x", padx=6, pady=(0, 8))

        self._opt_var = tk.BooleanVar(value=False)
        opt_chk = ttk.Checkbutton(compile_bar,
                                  text="  Enable Code Optimization",
                                  variable=self._opt_var)
        opt_chk.pack(side="left")

        self._btn_compile = self._make_button(
            compile_bar, "⚙  Compile", self._on_compile,
            bg=ACCENT, fg="#000000", padx=16, pady=6,
            font=(SANS, 10, "bold"),
        )
        self._btn_compile.pack(side="right")

        # Pipeline status panel
        pipe_frame = tk.Frame(frame, bg=BG2)
        pipe_frame.pack(fill="x", padx=6, pady=(0, 3))

        self._build_section_header(pipe_frame, "B  Compiler Pipeline")
        self._phase_labels = {}
        phases = ["Lexical Analysis", "Syntax Analysis", "Semantic Analysis",
                  "TAC Generation", "Optimization", "Execution"]
        for i, ph in enumerate(phases, start=1):
            row = tk.Frame(pipe_frame, bg=BG2)
            row.pack(fill="x", padx=10, pady=1)
            icon_lbl = tk.Label(row, text="○", bg=BG2, fg=FG3, font=FONT_MONO,
                                width=2, anchor="w")
            icon_lbl.pack(side="left")
            name_lbl = tk.Label(row, text=f"{i}. {ph}", bg=BG2, fg=FG2,
                                font=FONT_SANS_S, anchor="w")
            name_lbl.pack(side="left", padx=4)
            self._phase_labels[ph] = (icon_lbl, name_lbl)

        tk.Frame(pipe_frame, bg=BG2, height=6).pack()

        # Execution controls panel
        exec_frame = tk.Frame(frame, bg=BG2)
        exec_frame.pack(fill="x", padx=6, pady=(0, 6))

        self._build_section_header(exec_frame, "H  Execution Controls")

        ctrl_row = tk.Frame(exec_frame, bg=BG2)
        ctrl_row.pack(fill="x", padx=10, pady=(4, 2))

        tk.Label(ctrl_row, text="Event:", bg=BG2, fg=FG2,
                 font=FONT_SANS_S).pack(side="left")
        self._event_var = tk.StringVar(value="(compile first)")
        self._event_combo = ttk.Combobox(ctrl_row, textvariable=self._event_var,
                                         values=[], state="disabled",
                                         width=18, font=FONT_SANS_S)
        self._event_combo.pack(side="left", padx=6)

        self._btn_trigger = self._make_button(ctrl_row, "▶ Trigger Event",
                                              self._on_trigger_event,
                                              bg=ACCENT2, fg="#000000",
                                              state="disabled")
        self._btn_trigger.pack(side="left", padx=4)

        self._btn_reset_rt = self._make_button(ctrl_row, "⟳ Reset Runtime",
                                               self._on_reset_runtime,
                                               bg="#21262d", fg=FG2,
                                               state="disabled")
        self._btn_reset_rt.pack(side="left", padx=2)

        # Status bar
        self._status_var = tk.StringVar(value="Ready")
        status_bar = tk.Label(frame, textvariable=self._status_var,
                              bg=BG, fg=FG3, font=FONT_SANS_S,
                              anchor="w", padx=8)
        status_bar.pack(fill="x", side="bottom")

        return frame

    # -----------------------------------------------------------------------
    # Right column
    # -----------------------------------------------------------------------

    def _build_right_column(self, parent):
        frame = tk.Frame(parent, bg=BG)

        # Top: tabbed viewers
        notebook = ttk.Notebook(frame)
        notebook.pack(fill="both", expand=True, padx=6, pady=(6, 3))

        self._tab_game    = self._build_game_tab(notebook)
        self._tab_tokens  = self._build_tokens_tab(notebook)
        self._tab_ast     = self._build_ast_tab(notebook)
        self._tab_symtab  = self._build_symtab_tab(notebook)
        self._tab_tac     = self._build_tac_tab(notebook)
        self._tab_opt     = self._build_opt_tab(notebook)

        notebook.add(self._tab_game,   text=" 🎮 Playable Game ")
        notebook.add(self._tab_tokens, text=" C  Tokens ")
        notebook.add(self._tab_ast,    text=" D  AST ")
        notebook.add(self._tab_symtab, text=" E  Symbol Table ")
        notebook.add(self._tab_tac,    text=" F  TAC ")
        notebook.add(self._tab_opt,    text=" G  Optimization ")

        # Bottom: errors + mega output
        bottom = tk.PanedWindow(frame, orient="vertical",
                                bg=BG, sashwidth=4, sashrelief="flat")
        bottom.pack(fill="both", expand=True, padx=6, pady=(0, 6))

        err_frame = self._build_error_panel(bottom)
        out_frame = self._build_output_panel(bottom)

        bottom.add(err_frame, minsize=80, height=90)
        bottom.add(out_frame, minsize=150)

        return frame

    # -----------------------------------------------------------------------
    # Tab builders
    # -----------------------------------------------------------------------

    def _build_game_tab(self, nb):
        f = tk.Frame(nb, bg=BG2)
        self._game_canvas = PlatformerCanvas(f, bridge=self._bridge)
        self._game_canvas.pack(fill="both", expand=True, padx=2, pady=2)
        return f

    def _build_tokens_tab(self, nb):
        f = tk.Frame(nb, bg=BG2)
        cols = ("Index", "Type", "Value", "Line", "Col")
        self._token_tree = self._make_treeview(f, cols)
        self._token_tree.column("Index", width=50,  minwidth=40)
        self._token_tree.column("Type",  width=180, minwidth=140)
        self._token_tree.column("Value", width=130, minwidth=80)
        self._token_tree.column("Line",  width=60,  minwidth=40)
        self._token_tree.column("Col",   width=60,  minwidth=40)
        return f

    def _build_ast_tab(self, nb):
        f = tk.Frame(nb, bg=BG2)
        self._ast_text = self._make_text(f)
        return f

    def _build_symtab_tab(self, nb):
        f = tk.Frame(nb, bg=BG2)
        cols = ("Name", "Type", "Initial Value", "Declared Line")
        self._symtab_tree = self._make_treeview(f, cols)
        self._symtab_tree.column("Name",          width=130, minwidth=80)
        self._symtab_tree.column("Type",          width=100, minwidth=70)
        self._symtab_tree.column("Initial Value", width=100, minwidth=60)
        self._symtab_tree.column("Declared Line", width=100, minwidth=60)
        return f

    def _build_tac_tab(self, nb):
        f = tk.Frame(nb, bg=BG2)
        self._tac_text = self._make_text(f)
        return f

    def _build_opt_tab(self, nb):
        f = tk.Frame(nb, bg=BG2)
        self._opt_text = self._make_text(f)
        return f

    def _build_error_panel(self, parent):
        f = tk.Frame(parent, bg=BG2)
        self._build_section_header(f, "J  Errors & Status")
        self._error_text = self._make_text(f, height=4, fg=ACCENT3)
        return f

    def _build_output_panel(self, parent):
        f = tk.Frame(parent, bg=BG2)
        self._build_section_header(f, "I  Execution Output")
        self._output_text = self._make_text(f, fg=ACCENT2)
        return f

    # -----------------------------------------------------------------------
    # Widget factories
    # -----------------------------------------------------------------------

    def _build_section_header(self, parent, title: str):
        row = tk.Frame(parent, bg=BG2)
        row.pack(fill="x", padx=8, pady=(6, 2))
        tk.Label(row, text=title, bg=BG2, fg=ACCENT,
                 font=FONT_HDR).pack(side="left")
        tk.Frame(row, bg=BORDER, height=1).pack(
            side="left", fill="x", expand=True, padx=(8, 0))

    def _make_text(self, parent, height=None, fg=FG):
        frame = tk.Frame(parent, bg=BORDER, bd=1)
        frame.pack(fill="both", expand=True, padx=8, pady=(2, 6))
        kw = dict(bg=BG3, fg=fg, insertbackground=ACCENT,
                  font=FONT_MONO, relief="flat", bd=0,
                  state="disabled", wrap="none",
                  selectbackground="#264f78",
                  spacing1=2, spacing3=2)
        if height:
            kw["height"] = height
        txt = scrolledtext.ScrolledText(frame, **kw)
        txt.pack(fill="both", expand=True)
        # Configure tags
        txt.tag_configure("keyword", foreground="#ff7b72")
        txt.tag_configure("label",   foreground=ACCENT4)
        txt.tag_configure("num",     foreground="#79c0ff")
        txt.tag_configure("op",      foreground="#d2a8ff")
        txt.tag_configure("comment", foreground=FG3)
        txt.tag_configure("ok",      foreground=ACCENT2)
        txt.tag_configure("err",     foreground=ACCENT3)
        txt.tag_configure("hdr",     foreground=ACCENT)
        txt.tag_configure("dim",     foreground=FG3)
        return txt

    def _make_treeview(self, parent, cols):
        frame = tk.Frame(parent, bg=BG2)
        frame.pack(fill="both", expand=True, padx=8, pady=(2, 6))

        tree = ttk.Treeview(frame, columns=cols, show="headings",
                            style="Mono.Treeview")
        for col in cols:
            tree.heading(col, text=col, anchor="w")
            tree.column(col, anchor="w")

        style = ttk.Style()
        style.configure("Mono.Treeview",
                        background=BG3, foreground=FG, fieldbackground=BG3,
                        font=FONT_MONO, rowheight=22, borderwidth=0)
        style.configure("Mono.Treeview.Heading",
                        background=BG2, foreground=ACCENT,
                        font=(SANS, 9, "bold"), relief="flat")
        style.map("Mono.Treeview",
                  background=[("selected", "#1f6feb")],
                  foreground=[("selected", FG)])

        vsb = ttk.Scrollbar(frame, orient="vertical",   command=tree.yview)
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        hsb.pack(side="bottom", fill="x")
        vsb.pack(side="right",  fill="y")
        tree.pack(fill="both", expand=True)
        return tree

    def _make_button(self, parent, text, cmd, bg=BG3, fg=FG,
                     padx=8, pady=4, state="normal", font=FONT_SANS):
        btn = tk.Button(parent, text=text, command=cmd,
                        bg=bg, fg=fg, activebackground=BORDER,
                        activeforeground=fg, relief="flat", bd=0,
                        padx=padx, pady=pady, cursor="hand2",
                        font=font, state=state)
        btn.bind("<Enter>", lambda e: btn.config(bg=BORDER))
        btn.bind("<Leave>", lambda e: btn.config(bg=bg))
        return btn

    # -----------------------------------------------------------------------
    # Default content
    # -----------------------------------------------------------------------

    def _populate_default(self):
        self._editor.delete("1.0", "end")
        self._editor.insert("1.0", DEFAULT_SOURCE)
        self._on_compile()
        self._set_status("Ready — Edit GameScript, click Compile (F5), or play directly in the Game tab!")

    # -----------------------------------------------------------------------
    # Event handlers
    # -----------------------------------------------------------------------

    def _on_example_selected(self, event=None):
        name = self._example_var.get()
        source = EXAMPLES.get(name, "")
        self._editor.delete("1.0", "end")
        self._editor.insert("1.0", source)
        self._is_source_stale = True
        self._invalidate_state()

    def _on_reset(self):
        self._example_var.set("Basic Program")
        self._editor.delete("1.0", "end")
        self._editor.insert("1.0", DEFAULT_SOURCE)
        self._is_source_stale = True
        self._invalidate_state()

    def _on_clear_output(self):
        self._set_text(self._output_text, "")
        self._set_text(self._error_text, "")

    def _on_source_edited(self, event=None):
        self._is_source_stale = True
        self._invalidate_state()

    def _on_compile(self):
        source   = self._editor.get("1.0", "end-1c")
        optimize = self._opt_var.get()

        self._set_status("Compiling…")
        self._reset_pipeline_display()
        self._clear_all_viewers()

        # Run the compiler service
        result = compile_source(source, optimize=optimize, verbose=False)
        self._result = result

        # Update pipeline status display
        for ph in result.phases:
            self._update_phase(ph.name, ph.status)

        if not result.success:
            self._show_errors(result)
            self._invalidate_execution()
            self._set_status("Compilation failed — see errors panel")
            return

        self._is_source_stale = False

        # Populate viewers
        self._populate_tokens(result)
        self._populate_ast(result)
        self._populate_symtab(result)
        self._populate_tac(result)
        self._populate_opt(result)

        # Set up runtime
        self._interp = TACInterpreter(result.active_tac, verbose=False)
        self._state  = self._interp.initialize()

        # Populate event selector
        events = self._interp.registered_events()
        self._event_combo.config(values=events, state="readonly")
        if events:
            self._event_var.set(events[0])
        else:
            self._event_var.set("(no events)")

        self._btn_trigger.config(state="normal")
        self._btn_reset_rt.config(state="normal")

        # Mark execution phase as ready
        self._update_phase("Execution", "Not Run")

        # Sync Game Canvas
        if hasattr(self, "_game_canvas"):
            self._game_canvas.restart_level()

        # Show initial state in output
        self._append_output("=" * 52 + "\n", "hdr")
        self._append_output(" COMPILATION SUCCESSFUL\n", "ok")
        self._append_output("=" * 52 + "\n\n", "hdr")
        self._show_initial_state()

        self._set_status(
            f"Compiled OK — {len(result.original_tac)} TAC instructions"
            + (f" -> {len(result.optimized_tac)} after optimization"
               if optimize and result.optimized_tac else "")
        )
        self._set_text(self._error_text, "")

    def _on_trigger_event(self):
        if not self._result or not self._result.success:
            return
        event = self._event_var.get()
        if not event or event.startswith("("):
            return

        prev_snap = self._state.snapshot()
        self._interp.trigger_event(event, self._state)
        curr_snap = self._state.snapshot()

        # Build rich output
        self._append_output("-" * 52 + "\n", "dim")
        self._append_output(f" Event Triggered (Manual): {event}\n", "hdr")
        self._append_output("-" * 52 + "\n", "dim")

        # Show changes
        any_change = False
        for var in prev_snap:
            old = prev_snap[var]
            new = curr_snap.get(var, old)
            if old != new:
                self._append_output(f"  {var}: {old} -> {new}\n", "ok")
                any_change = True
        if not any_change:
            self._append_output("  (no variable changes)\n", "dim")

        # Show current state
        self._append_output("\n Current State:\n", "hdr")
        for var, val in curr_snap.items():
            self._append_output(f"  {var} = {val}\n", "num")
        self._append_output(f"  status = {self._state.status}\n", "keyword")
        self._append_output("\n")

        # Notify game canvas
        if hasattr(self, "_game_canvas"):
            self._game_canvas.notify_tac_event(f"⚡ Panel: {event}")
            if self._state.status == "GAME_OVER":
                self._game_canvas.world.player.die()

        if self._state.is_terminal():
            self._update_phase("Execution", "Passed")
            self._append_output(
                f" Status: {self._state.status}\n", "err"
                if self._state.status == "GAME_OVER" else "ok"
            )
            self._btn_trigger.config(state="disabled")
        else:
            self._update_phase("Execution", "Passed")

        self._output_text.yview("end")

    def _on_reset_runtime(self):
        if not self._result or not self._result.success:
            return
        self._state.reset()
        self._interp = TACInterpreter(self._result.active_tac, verbose=False)
        self._state  = self._interp.initialize()
        events = self._interp.registered_events()
        self._btn_trigger.config(state="normal")

        # Sync Game Canvas
        if hasattr(self, "_game_canvas"):
            self._game_canvas.restart_level()

        self._append_output("\n" + "-" * 52 + "\n", "dim")
        self._append_output(" Runtime Reset\n", "hdr")
        self._show_initial_state()
        self._update_phase("Execution", "Not Run")
        self._output_text.yview("end")

    def _on_bridge_event_executed(self, event_name: str, changes: dict, state, logs: list):
        """Called whenever an in-game event (e.g. coin collection or enemy attack) executes TAC."""
        self._append_output("-" * 52 + "\n", "dim")
        self._append_output(f" In-Game TAC Event Dispatched: {event_name}\n", "hdr")
        self._append_output("-" * 52 + "\n", "dim")

        for var, (old, new) in changes.items():
            self._append_output(f"  {var}: {old} -> {new}\n", "ok")
        if not changes:
            self._append_output("  (no variable changes)\n", "dim")

        self._append_output(f"  status = {state.status}\n\n", "keyword")

        if state.is_terminal():
            self._update_phase("Execution", "Passed")
            self._append_output(
                f" Status: {state.status}\n",
                "err" if state.status == "GAME_OVER" else "ok"
            )
            self._btn_trigger.config(state="disabled")
        else:
            self._update_phase("Execution", "Passed")

        self._output_text.yview("end")

    # -----------------------------------------------------------------------
    # Viewer population
    # -----------------------------------------------------------------------

    def _populate_tokens(self, result):
        tree = self._token_tree
        for row in tree.get_children():
            tree.delete(row)
        for tok in result.token_rows():
            tree.insert("", "end", values=(
                tok["index"], tok["type"], tok["value"],
                tok["line"],  tok["column"]
            ))

    def _populate_ast(self, result):
        if result.ast is None:
            return
        lines = []
        self._ast_to_lines(result.ast, lines)
        self._set_text(self._ast_text, "\n".join(lines))

    def _ast_to_lines(self, node, lines, prefix="", is_last=True):
        connector = "╰── " if is_last else "├── "
        child_pref = prefix + ("    " if is_last else "│   ")

        if isinstance(node, ProgramNode):
            lines.append("Program")
            for i, stmt in enumerate(node.statements):
                self._ast_to_lines(stmt, lines, prefix, i == len(node.statements)-1)

        elif isinstance(node, PlayerDeclarationNode):
            lines.append(f"{prefix}{connector}PlayerDeclaration")
            lines.append(f"{child_pref}├── name: {node.name.name}")
            lines.append(f"{child_pref}╰── value: {node.value.value}")

        elif isinstance(node, EventNode):
            lines.append(f"{prefix}{connector}Event: {node.name.name}")
            for i, a in enumerate(node.body):
                self._ast_to_lines(a, lines, child_pref, i == len(node.body)-1)

        elif isinstance(node, IfNode):
            cond = node.condition
            r = cond.right.value if isinstance(cond.right, LiteralNode) else cond.right.name
            lines.append(f"{prefix}{connector}If: {cond.left.name} {cond.operator} {r}")
            for i, a in enumerate(node.body):
                self._ast_to_lines(a, lines, child_pref, i == len(node.body)-1)

        elif isinstance(node, AssignmentNode):
            rhs = (node.value.value if isinstance(node.value, LiteralNode)
                   else node.value.name)
            lines.append(f"{prefix}{connector}Assignment: {node.variable.name} "
                         f"{node.operator} {rhs}")

        elif isinstance(node, CommandNode):
            lines.append(f"{prefix}{connector}Command: {node.name}")

    def _populate_symtab(self, result):
        tree = self._symtab_tree
        for row in tree.get_children():
            tree.delete(row)
        for sym in result.symbol_table_rows():
            tree.insert("", "end", values=(
                sym["name"], sym["type"], sym["value"], sym["line"]
            ))

    def _populate_tac(self, result):
        tac = result.original_tac
        if tac is None:
            self._set_text(self._tac_text, "(TAC not available)")
            return
        txt = self._tac_text
        self._clear_text(txt)
        txt.config(state="normal")
        txt.insert("end", "=" * 52 + "\n", "hdr")
        txt.insert("end", " THREE-ADDRESS CODE\n", "hdr")
        txt.insert("end", "=" * 52 + "\n\n", "hdr")
        for i, instr in enumerate(tac, start=1):
            line = f"{i:04d}  {instr}\n"
            if "DECLARE" in line:
                txt.insert("end", line[:6], "dim")
                txt.insert("end", "DECLARE", "keyword")
                txt.insert("end", line[13:])
            elif "LABEL" in line:
                txt.insert("end", line, "label")
            elif any(op in line for op in ("ADD", "SUB", "MOV")):
                txt.insert("end", line[:6], "dim")
                txt.insert("end", instr.opcode(), "op")
                txt.insert("end", f"      {instr.operands_str()}\n")
            elif "IF_" in line or "GOTO" in line:
                txt.insert("end", line, "keyword")
            elif "COMMAND" in line:
                txt.insert("end", line, "err")
            elif "RETURN" in line:
                txt.insert("end", line, "dim")
            else:
                txt.insert("end", line)
        txt.insert("end", f"\nTotal: {len(tac)} instructions\n", "dim")
        txt.config(state="disabled")

    def _populate_opt(self, result):
        txt = self._opt_text
        self._clear_text(txt)
        txt.config(state="normal")

        if not result.optimize:
            txt.insert("end", "Optimization is disabled.\n", "dim")
            txt.insert("end", "Enable the checkbox and recompile to see optimization comparison.\n", "dim")
            txt.config(state="disabled")
            return

        if result.optimized_tac is None:
            txt.insert("end", "(Optimization was skipped or failed)\n", "err")
            txt.config(state="disabled")
            return

        rep = result.opt_report

        txt.insert("end", "OPTIMIZATION COMPARISON\n", "hdr")
        txt.insert("end", "─" * 52 + "\n\n", "dim")
        txt.insert("end", f"  Instructions before : {rep.original_count}\n", "num")
        txt.insert("end", f"  Instructions after  : {rep.optimized_count}\n", "num")
        txt.insert("end", f"  Instructions removed: {rep.instructions_removed}\n\n",
                   "ok" if rep.instructions_removed > 0 else "num")

        if rep.changes:
            txt.insert("end", "  Changes applied:\n", "keyword")
            for c in rep.changes:
                txt.insert("end", f"    ✓ {c}\n", "ok")
        else:
            txt.insert("end", "  No optimizations applicable. TAC remains unchanged.\n", "dim")

        txt.insert("end", "\n  Note: instruction-count reduction does not guarantee\n", "dim")
        txt.insert("end", "  a measurable speedup in this educational interpreter.\n\n", "dim")

        txt.insert("end", "─" * 52 + "\n", "dim")
        txt.insert("end", "  OPTIMIZED TAC\n", "hdr")
        txt.insert("end", "─" * 52 + "\n", "dim")
        for i, instr in enumerate(result.optimized_tac, start=1):
            txt.insert("end", f"  {i:04d}  {instr}\n")
        txt.config(state="disabled")

    # -----------------------------------------------------------------------
    # Error display
    # -----------------------------------------------------------------------

    def _show_errors(self, result):
        txt = self._error_text
        self._clear_text(txt)
        txt.config(state="normal")
        for err in result.errors:
            txt.insert("end", err + "\n", "err")
        txt.config(state="disabled")

    # -----------------------------------------------------------------------
    # Output helpers
    # -----------------------------------------------------------------------

    def _show_initial_state(self):
        if not self._state:
            return
        self._append_output(" Initial State:\n", "hdr")
        for var in self._state.all_variables():
            val = self._state.get(var)
            self._append_output(f"  {var} = {val}\n", "num")
        self._append_output(f"  status = {self._state.status}\n\n", "keyword")

    def _append_output(self, text, tag=None):
        txt = self._output_text
        txt.config(state="normal")
        if tag:
            txt.insert("end", text, tag)
        else:
            txt.insert("end", text)
        txt.config(state="disabled")

    # -----------------------------------------------------------------------
    # Pipeline display helpers
    # -----------------------------------------------------------------------

    def _update_phase(self, name: str, status: str):
        if name not in self._phase_labels:
            return
        icon_lbl, name_lbl = self._phase_labels[name]
        color = STATUS_COLORS.get(status, FG3)
        icon  = STATUS_ICONS.get(status, "?")
        icon_lbl.config(text=icon, fg=color)
        name_lbl.config(fg=color)

    def _reset_pipeline_display(self):
        for ph in self._phase_labels:
            self._update_phase(ph, "Not Run")

    # -----------------------------------------------------------------------
    # State helpers
    # -----------------------------------------------------------------------

    def _invalidate_state(self):
        """Mark everything as stale when source changes."""
        self._result = None
        self._interp = None
        self._state  = None
        self._reset_pipeline_display()
        self._invalidate_execution()

    def _invalidate_execution(self):
        self._btn_trigger.config(state="disabled")
        self._btn_reset_rt.config(state="disabled")
        self._event_combo.config(values=[], state="disabled")
        self._event_var.set("(compile first)")

    def _clear_all_viewers(self):
        self._set_text(self._ast_text, "")
        self._set_text(self._tac_text, "")
        self._set_text(self._opt_text, "")
        self._set_text(self._output_text, "")
        for row in self._token_tree.get_children():
            self._token_tree.delete(row)
        for row in self._symtab_tree.get_children():
            self._symtab_tree.delete(row)

    # -----------------------------------------------------------------------
    # Text widget helpers
    # -----------------------------------------------------------------------

    def _set_text(self, widget, text, tag=None):
        self._clear_text(widget)
        widget.config(state="normal")
        if tag:
            widget.insert("1.0", text, tag)
        else:
            widget.insert("1.0", text)
        widget.config(state="disabled")

    def _clear_text(self, widget):
        widget.config(state="normal")
        widget.delete("1.0", "end")
        widget.config(state="disabled")

    def _set_status(self, msg: str):
        self._status_var.set(msg)


# ===========================================================================
# Entry point
# ===========================================================================

def main():
    app = GameForgeApp()
    app.mainloop()


if __name__ == "__main__":
    main()
