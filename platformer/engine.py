"""
GameForge -- Platformer Game Engine
===================================
Playable 2D platformer rendered in Tkinter Canvas, driven directly by the
GameForge compiler and Three-Address Code (TAC) interpreter runtime.
"""

import math
import time
import tkinter as tk
from typing import Optional, Set, List

from .bridge import CompilerGameBridge
from .world import LevelWorld, create_default_world
from .entities import Particle


class PlatformerCanvas(tk.Frame):
    """
    An interactive Mario-inspired 2D platformer widget.
    Integrates with CompilerGameBridge so every coin collection, enemy collision,
    and game status update is authoritatively evaluated by the TAC interpreter.
    """

    def __init__(self, parent, bridge: CompilerGameBridge, **kwargs):
        super().__init__(parent, bg="#0f1117", **kwargs)

        self.bridge = bridge
        self.world: LevelWorld = create_default_world()

        # Input & state
        self.keys_down: Set[str] = set()
        self.running: bool = True
        self.paused: bool = False
        self.last_tick: float = time.time()

        # Camera
        self.cam_x: float = 0.0
        self.cam_y: float = 0.0

        # Visual feedback particles & banners
        self.particles: List[Particle] = []
        self.tac_banner_text: str = ""
        self.tac_banner_timer: float = 0.0

        # UI Layout
        self._build_ui()
        self._bind_keys()

        # Start game loop
        self._game_loop()

    # ------------------------------------------------------------------
    # UI Setup
    # ------------------------------------------------------------------

    def _build_ui(self):
        # 1. Top Mini-Toolbar
        top_bar = tk.Frame(self, bg="#161b22", height=36)
        top_bar.pack(fill="x", side="top")
        top_bar.pack_propagate(False)

        # Title
        tk.Label(
            top_bar, text="🎮 Mario Platformer (TAC-Controlled)",
            bg="#161b22", fg="#58a6ff", font=("Segoe UI", 10, "bold")
        ).pack(side="left", padx=10)

        # Controls in toolbar
        self.btn_restart = tk.Button(
            top_bar, text="↺ Restart Level", command=self.restart_level,
            bg="#21262d", fg="#c9d1d9", activebackground="#30363d",
            activeforeground="#ffffff", relief="flat", bd=0, padx=8, pady=2,
            font=("Segoe UI", 9), cursor="hand2"
        )
        self.btn_restart.pack(side="right", padx=6, pady=4)

        self.btn_pause = tk.Button(
            top_bar, text="⏸ Pause", command=self.toggle_pause,
            bg="#21262d", fg="#c9d1d9", activebackground="#30363d",
            activeforeground="#ffffff", relief="flat", bd=0, padx=8, pady=2,
            font=("Segoe UI", 9), cursor="hand2"
        )
        self.btn_pause.pack(side="right", padx=4, pady=4)

        self.btn_focus = tk.Button(
            top_bar, text="⚡ Click to Focus Controls", command=self.focus_game,
            bg="#238636", fg="#ffffff", activebackground="#2ea043",
            relief="flat", bd=0, padx=8, pady=2,
            font=("Segoe UI", 9, "bold"), cursor="hand2"
        )
        self.btn_focus.pack(side="right", padx=6, pady=4)

        # 2. Main Game Canvas
        self.canvas = tk.Canvas(
            self, bg="#5c94fc", bd=0, highlightthickness=1,
            highlightbackground="#30363d"
        )
        self.canvas.pack(fill="both", expand=True)

        # Focus canvas on click
        self.canvas.bind("<Button-1>", lambda e: self.focus_game())

        # 3. Bottom Controls Bar
        bot_bar = tk.Frame(self, bg="#161b22", height=26)
        bot_bar.pack(fill="x", side="bottom")
        bot_bar.pack_propagate(False)

        hint = "Controls: [A / D / ← / →] Move  |  [Space / W / ↑] Jump  |  [R] Restart Level  |  [P] Pause"
        tk.Label(
            bot_bar, text=hint, bg="#161b22", fg="#8b949e",
            font=("Segoe UI", 8)
        ).pack(side="left", padx=10)

        self.lbl_tac_status = tk.Label(
            bot_bar, text="TAC Runtime: Ready", bg="#161b22", fg="#3fb950",
            font=("Segoe UI", 8, "bold")
        )
        self.lbl_tac_status.pack(side="right", padx=10)

    def focus_game(self):
        """Focus the canvas so arrow and space keys route to the game."""
        self.canvas.focus_set()
        self.btn_focus.config(text="✓ Game Focused", bg="#1f6feb")

    def _bind_keys(self):
        """Bind keyboard controls to the canvas."""
        self.canvas.bind("<KeyPress>", self._on_key_press)
        self.canvas.bind("<KeyRelease>", self._on_key_release)

    def _on_key_press(self, event):
        k = event.keysym.lower()
        self.keys_down.add(k)

        if k == "r":
            self.restart_level()
        elif k == "p":
            self.toggle_pause()

    def _on_key_release(self, event):
        k = event.keysym.lower()
        self.keys_down.discard(k)

    def toggle_pause(self):
        self.paused = not self.paused
        self.btn_pause.config(text="▶ Resume" if self.paused else "⏸ Pause")

    def restart_level(self):
        """Reset world entities and invoke bridge to reset runtime state."""
        self.world.reset()
        self.particles.clear()
        self.tac_banner_text = ""
        self.tac_banner_timer = 0.0

        # Also reset compiler runtime if bridge supports it
        state = self.bridge._get_state()
        if state is not None:
            state.reset()
            # Also re-evaluate initial IFs
            interp = self.bridge._get_interpreter()
            if interp is not None:
                interp.initialize()

        self.canvas.focus_set()

    def notify_tac_event(self, text: str):
        """Show visual banner on canvas when TAC executes."""
        self.tac_banner_text = text
        self.tac_banner_timer = 2.0

    # ------------------------------------------------------------------
    # Game Loop & Physics
    # ------------------------------------------------------------------

    def _game_loop(self):
        now = time.time()
        dt = min(0.05, now - self.last_tick)
        self.last_tick = now

        if not self.paused and self.running:
            self._update(dt)

        self._render()

        # Schedule next tick at ~50 FPS (20ms)
        self.after(20, self._game_loop)

    def _update(self, dt: float):
        player = self.world.player

        # Update visual banner timer
        if self.tac_banner_timer > 0:
            self.tac_banner_timer = max(0.0, self.tac_banner_timer - dt)
            if self.tac_banner_timer <= 0:
                self.tac_banner_text = ""

        # Update floating particles
        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if p.is_alive]

        # Update coins & enemies
        for c in self.world.coins:
            c.update(dt)
        for e in self.world.enemies:
            e.update(dt)
        self.world.goal.update(dt)

        # Check if compiler runtime says GAME_OVER
        status = self.bridge.get_status()
        if status == "GAME_OVER" and not player.is_dead:
            player.die()

        if player.is_dead:
            player.vy += 0.5  # gravity for dead hop
            player.y += player.vy
            player.update(dt)
            return

        if status == "LEVEL_COMPLETE":
            self.world.goal.trigger_win()
            # Player walks towards victory castle
            if player.x < self.world.goal.x + 60:
                player.vx = 1.5
                player.facing_right = True
                player.x += player.vx
            else:
                player.vx = 0.0
            player.update(dt)
            return

        # 1. Player horizontal movement from keys
        move_speed = 3.6
        if any(k in self.keys_down for k in ("left", "a")):
            player.vx = -move_speed
            player.facing_right = False
        elif any(k in self.keys_down for k in ("right", "d")):
            player.vx = move_speed
            player.facing_right = True
        else:
            player.vx = 0.0

        # Jump
        if any(k in self.keys_down for k in ("space", "up", "w")):
            player.jump(jump_speed=11.5)

        # 2. Apply Gravity
        player.vy = min(12.0, player.vy + 0.55)

        # 3. Collision Resolution with Platforms (X axis)
        player.x += player.vx
        # Clamp within level bounds
        player.x = max(0.0, min(self.world.width - player.w, player.x))

        for plat in self.world.platforms:
            if self._check_overlap(player.x, player.y, player.w, player.h,
                                   plat.x, plat.y, plat.w, plat.h):
                if player.vx > 0:
                    player.x = plat.x - player.w
                elif player.vx < 0:
                    player.x = plat.x + plat.w

        # 4. Collision Resolution with Platforms (Y axis)
        player.y += player.vy
        player.grounded = False

        for plat in self.world.platforms:
            if self._check_overlap(player.x, player.y, player.w, player.h,
                                   plat.x, plat.y, plat.w, plat.h):
                if player.vy > 0:
                    # Landing on top of platform
                    player.y = plat.y - player.h
                    player.vy = 0.0
                    player.grounded = True
                elif player.vy < 0:
                    # Bumping head on platform bottom
                    player.y = plat.y + plat.h
                    player.vy = 0.0

        # Pit check
        if player.y > self.world.height + 40:
            # Player fell into pit!
            if not player.is_dead:
                # Trigger enemy_attack / death via bridge
                res = self.bridge.trigger_event("enemy_attack", "Fell into pit")
                player.die()
                self.notify_tac_event("⚡ Pit Hazard -> enemy_attack triggered!")

        player.update(dt)

        # 5. Coin Collection -> Triggers GameScript 'collect_coin' event
        for coin in self.world.coins:
            if not coin.collected and self._check_overlap(
                player.x, player.y, player.w, player.h,
                coin.x, coin.y, coin.w, coin.h
            ):
                coin.collected = True
                self.particles.append(Particle(coin.x, coin.y - 10, "+Coin!", color="#ffd700"))

                # Execute through TAC Interpreter
                res = self.bridge.trigger_event("collect_coin", "Picked up gold coin")
                if res["success"]:
                    # Build short diff string
                    diffs = [f"{v}: {old}->{new}" for v, (old, new) in res["changes"].items()]
                    diff_str = ", ".join(diffs) if diffs else "coins updated"
                    self.notify_tac_event(f"⚡ TAC: collect_coin ({diff_str})")
                else:
                    self.notify_tac_event("⚡ Coin collected (event 'collect_coin' not in script)")

        # 6. Enemy Collision -> Triggers GameScript 'enemy_attack' or Stomp
        for enemy in self.world.enemies:
            if enemy.alive and self._check_overlap(
                player.x, player.y, player.w, player.h,
                enemy.x, enemy.y, enemy.w, enemy.h
            ):
                # Check for stomp from above
                if player.vy > 0 and (player.y + player.h - player.vy) <= (enemy.y + 12):
                    enemy.squish()
                    player.vy = -8.5  # bounce
                    self.particles.append(Particle(enemy.x, enemy.y - 10, "STOMP!", color="#38ef7d"))
                    # If script has player_move event, trigger it as bonus
                    if self.bridge.has_event("player_move"):
                        self.bridge.trigger_event("player_move", "Stomped enemy")
                        self.notify_tac_event("⚡ TAC: player_move (Stomp bonus)")
                elif player.hurt_timer <= 0:
                    # Enemy hits player!
                    knock_dir = -5.0 if player.x < enemy.x else 5.0
                    player.take_hit(knockback_x=knock_dir)
                    self.particles.append(Particle(player.x, player.y - 15, "OUCH!", color="#ff4d4d"))

                    # Execute through TAC Interpreter
                    res = self.bridge.trigger_event("enemy_attack", "Enemy collided with player")
                    if res["success"]:
                        diffs = [f"{v}: {old}->{new}" for v, (old, new) in res["changes"].items()]
                        diff_str = ", ".join(diffs) if diffs else "health reduced"
                        self.notify_tac_event(f"⚡ TAC: enemy_attack ({diff_str})")
                    else:
                        self.notify_tac_event("⚡ Enemy hit player (event 'enemy_attack' not in script)")

        # 7. Goal / Flagpole Collision
        if player.x >= self.world.goal.x - 10 and not self.world.goal.flag_dropped:
            self.world.goal.trigger_win()
            self.particles.append(Particle(self.world.goal.x, self.world.goal.y - 100, "GOAL!!", color="#ffd700", lifetime=2.5))
            # If status isn't already level complete, check if GameState allows
            state = self.bridge._get_state()
            if state is not None and not state.is_terminal():
                state.set_level_complete()
                self.notify_tac_event("★ Goal Reached -> LEVEL_COMPLETE")

        # 8. Smooth Camera Tracking
        cv_w = max(400, self.canvas.winfo_width())
        target_cam_x = player.x - cv_w * 0.35
        max_cam_x = max(0.0, self.world.width - cv_w)
        target_cam_x = max(0.0, min(max_cam_x, target_cam_x))
        self.cam_x += (target_cam_x - self.cam_x) * 0.15

    def _check_overlap(self, x1, y1, w1, h1, x2, y2, w2, h2) -> bool:
        return (x1 < x2 + w2 and x1 + w1 > x2 and
                y1 < y2 + h2 and y1 + h1 > y2)

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def _render(self):
        cv = self.canvas
        cv.delete("all")

        cv_w = max(400, cv.winfo_width())
        cv_h = max(300, cv.winfo_height())
        cx = self.cam_x
        cy = self.cam_y

        # 1. Sky & Background
        cv.create_rectangle(0, 0, cv_w, cv_h, fill="#5c94fc", outline="")

        # 2. Decorative Parallax Clouds
        for cl_x, cl_y, cl_w in [(80, 50, 60), (320, 80, 80), (680, 45, 90),
                                 (1100, 60, 70), (1500, 75, 85), (1900, 40, 95)]:
            sx = cl_x - cx * 0.25
            if -120 <= sx <= cv_w + 120:
                cv.create_oval(sx, cl_y, sx + cl_w * 0.6, cl_y + 24, fill="#ffffff", outline="")
                cv.create_oval(sx + cl_w * 0.3, cl_y - 8, sx + cl_w * 0.8, cl_y + 24, fill="#ffffff", outline="")
                cv.create_oval(sx + cl_w * 0.5, cl_y, sx + cl_w, cl_y + 24, fill="#ffffff", outline="")

        # 3. Decorative Parallax Hills
        for h_x, h_w, h_h in [(140, 160, 80), (540, 220, 100), (1020, 180, 90),
                              (1450, 240, 110), (1880, 190, 85)]:
            sx = h_x - cx * 0.45
            gy = self.world.ground_y - cy
            if -250 <= sx <= cv_w + 250:
                cv.create_polygon(
                    sx, gy, sx + h_w / 2, gy - h_h, sx + h_w, gy,
                    fill="#38a169", outline="#22543d"
                )

        # 4. Platforms & Blocks
        for plat in self.world.platforms:
            if plat.x + plat.w >= cx and plat.x <= cx + cv_w:
                plat.draw(cv, cx, cy)

        # 5. Coins
        for coin in self.world.coins:
            if coin.x + coin.w >= cx and coin.x <= cx + cv_w:
                coin.draw(cv, cx, cy)

        # 6. Enemies
        for enemy in self.world.enemies:
            if enemy.x + enemy.w >= cx and enemy.x <= cx + cv_w:
                enemy.draw(cv, cx, cy)

        # 7. Goal
        self.world.goal.draw(cv, cx, cy)

        # 8. Player
        self.world.player.draw(cv, cx, cy)

        # 9. Particles
        for p in self.particles:
            p.draw(cv, cx, cy)

        # 10. Draw In-Game HUD (Direct from TAC Runtime)
        self._render_hud(cv, cv_w, cv_h)

        # 11. TAC Event Execution Banner
        if self.tac_banner_text:
            cv.create_rectangle(
                cv_w / 2 - 220, 48, cv_w / 2 + 220, 76,
                fill="#161b22", outline="#58a6ff", width=1.5
            )
            cv.create_text(
                cv_w / 2, 62, text=self.tac_banner_text,
                fill="#79c0ff", font=("Segoe UI", 9, "bold")
            )

        # 12. Overlays (Game Over / Level Complete / Need Compile)
        status = self.bridge.get_status()
        if not self.bridge.is_ready():
            self._render_not_compiled_overlay(cv, cv_w, cv_h)
        elif status == "GAME_OVER":
            self._render_game_over_overlay(cv, cv_w, cv_h)
        elif status == "LEVEL_COMPLETE":
            self._render_level_complete_overlay(cv, cv_w, cv_h)

    def _render_hud(self, cv, w: int, h: int):
        """Render HUD reading directly from the authoritative GameState."""
        # Top HUD Bar
        cv.create_rectangle(8, 8, min(w - 8, 560), 42, fill="#0f1117", outline="#30363d", width=1.5)

        # Variables from TAC GameState
        health = self.bridge.get_var("health", default=100)
        coins  = self.bridge.get_var("coins",  default=0)
        score  = self.bridge.get_var("score",  default=0)
        status = self.bridge.get_status()

        # Health display
        hp_color = "#3fb950" if health > 40 else ("#e3b341" if health > 20 else "#f85149")
        cv.create_text(20, 24, text="💖 HP:", fill="#ffffff", font=("Segoe UI", 9, "bold"), anchor="w")
        # Health bar background & fill
        cv.create_rectangle(64, 18, 144, 30, fill="#21262d", outline="#484f58")
        hp_bar_w = max(0, min(78, int((health / 100.0) * 78)))
        if hp_bar_w > 0:
            cv.create_rectangle(65, 19, 65 + hp_bar_w, 29, fill=hp_color, outline="")
        cv.create_text(152, 24, text=f"{health}", fill=hp_color, font=("Consolas", 10, "bold"), anchor="w")

        # Coins display
        cv.create_text(195, 24, text="🪙 COINS:", fill="#ffffff", font=("Segoe UI", 9, "bold"), anchor="w")
        cv.create_text(260, 24, text=f"{coins}", fill="#facc15", font=("Consolas", 10, "bold"), anchor="w")

        # Score display
        cv.create_text(300, 24, text="⭐ SCORE:", fill="#ffffff", font=("Segoe UI", 9, "bold"), anchor="w")
        cv.create_text(368, 24, text=f"{score}", fill="#58a6ff", font=("Consolas", 10, "bold"), anchor="w")

        # Status Badge
        badge_color = "#238636" if status == "RUNNING" else ("#da3633" if status == "GAME_OVER" else "#d29922")
        cv.create_rectangle(420, 16, 545, 34, fill=badge_color, outline="")
        cv.create_text(482, 25, text=f"STATE: {status}", fill="#ffffff", font=("Segoe UI", 8, "bold"))

        # Update bottom bar status
        if self.bridge.is_stale():
            self.lbl_tac_status.config(text="⚠️ Code Modified — Recompile F5", fg="#e3b341")
        elif not self.bridge.is_ready():
            self.lbl_tac_status.config(text="○ Click 'Compile' to Load Program", fg="#8b949e")
        else:
            self.lbl_tac_status.config(text=f"✓ TAC Active ({status})", fg="#3fb950")

    def _render_game_over_overlay(self, cv, w: int, h: int):
        cv.create_rectangle(0, 0, w, h, fill="#0a0c10", stipple="gray50")
        box_w = min(460, w - 40)
        bx1 = (w - box_w) / 2
        bx2 = bx1 + box_w
        by1 = h / 2 - 80
        by2 = h / 2 + 80

        cv.create_rectangle(bx1, by1, bx2, by2, fill="#161b22", outline="#f85149", width=2)
        cv.create_text(w / 2, by1 + 30, text="☠  GAME OVER  ☠", fill="#f85149", font=("Segoe UI", 18, "bold"))

        health = self.bridge.get_var("health", 0)
        cv.create_text(w / 2, by1 + 65, text=f"GameScript condition evaluated: health <= 0 (health = {health})",
                       fill="#c9d1d9", font=("Segoe UI", 9))
        cv.create_text(w / 2, by1 + 90, text="TAC Instruction: COMMAND GAME_OVER executed.",
                       fill="#8b949e", font=("Consolas", 9))
        cv.create_text(w / 2, by1 + 125, text="Press [ R ] or click '↺ Restart Level' to play again",
                       fill="#58a6ff", font=("Segoe UI", 10, "bold"))

    def _render_level_complete_overlay(self, cv, w: int, h: int):
        cv.create_rectangle(0, 0, w, h, fill="#0a0c10", stipple="gray50")
        box_w = min(460, w - 40)
        bx1 = (w - box_w) / 2
        bx2 = bx1 + box_w
        by1 = h / 2 - 80
        by2 = h / 2 + 80

        cv.create_rectangle(bx1, by1, bx2, by2, fill="#161b22", outline="#3fb950", width=2)
        cv.create_text(w / 2, by1 + 30, text="★  LEVEL COMPLETE!  ★", fill="#3fb950", font=("Segoe UI", 18, "bold"))

        coins = self.bridge.get_var("coins", 0)
        score = self.bridge.get_var("score", 0)
        cv.create_text(w / 2, by1 + 65, text=f"Victory conditions met!  Coins: {coins}  |  Score: {score}",
                       fill="#c9d1d9", font=("Segoe UI", 9))
        cv.create_text(w / 2, by1 + 90, text="TAC Instruction: COMMAND LEVEL_COMPLETE executed.",
                       fill="#8b949e", font=("Consolas", 9))
        cv.create_text(w / 2, by1 + 125, text="Press [ R ] or click '↺ Restart Level' to play again",
                       fill="#58a6ff", font=("Segoe UI", 10, "bold"))

    def _render_not_compiled_overlay(self, cv, w: int, h: int):
        box_w = min(420, w - 40)
        bx1 = (w - box_w) / 2
        bx2 = bx1 + box_w
        by1 = h / 2 - 50
        by2 = h / 2 + 50

        cv.create_rectangle(bx1, by1, bx2, by2, fill="#161b22", outline="#58a6ff", width=2)
        cv.create_text(w / 2, by1 + 25, text="⬡ Ready to Play", fill="#58a6ff", font=("Segoe UI", 14, "bold"))
        cv.create_text(w / 2, by1 + 55, text="Click '⚙ Compile' to load GameScript into the platformer",
                       fill="#c9d1d9", font=("Segoe UI", 10))
        cv.create_text(w / 2, by1 + 75, text="(Or select 'Platformer Demo' in the Examples dropdown)",
                       fill="#8b949e", font=("Segoe UI", 8))
