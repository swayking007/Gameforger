"""
GameForge -- Platformer Entities
================================
Visual game entities (Player, Coin, Enemy, Platform, Goal, Particle)
designed for clean, reliable rendering via Tkinter Canvas with zero external assets.
"""

import math
from typing import Optional, List, Tuple


class Player:
    """The Mario-inspired platformer hero."""

    def __init__(self, x: float, y: float):
        self.spawn_x = x
        self.spawn_y = y
        self.x = x
        self.y = y
        self.vx = 0.0
        self.vy = 0.0
        self.w = 26.0
        self.h = 36.0

        self.grounded = False
        self.facing_right = True
        self.walk_frame = 0
        self.anim_tick = 0

        self.hurt_timer = 0.0      # Invulnerability timer in seconds
        self.is_dead = False
        self.death_timer = 0.0

    def reset(self):
        self.x = self.spawn_x
        self.y = self.spawn_y
        self.vx = 0.0
        self.vy = 0.0
        self.grounded = False
        self.facing_right = True
        self.walk_frame = 0
        self.anim_tick = 0
        self.hurt_timer = 0.0
        self.is_dead = False
        self.death_timer = 0.0

    def jump(self, jump_speed: float = 12.0):
        if self.grounded and not self.is_dead:
            self.vy = -jump_speed
            self.grounded = False

    def take_hit(self, knockback_x: float = 4.0):
        """Apply damage knockback and activate invulnerability frames."""
        self.hurt_timer = 1.2
        self.vy = -6.0
        self.vx = knockback_x
        self.grounded = False

    def die(self):
        """Trigger death animation."""
        self.is_dead = True
        self.vy = -10.0
        self.grounded = False

    def update(self, dt: float):
        if self.hurt_timer > 0:
            self.hurt_timer = max(0.0, self.hurt_timer - dt)

        if self.is_dead:
            self.death_timer += dt
            return

        # Animate walking
        if abs(self.vx) > 0.5 and self.grounded:
            self.anim_tick += 1
            if self.anim_tick >= 5:
                self.walk_frame = (self.walk_frame + 1) % 4
                self.anim_tick = 0
        else:
            self.walk_frame = 0

    def draw(self, canvas, cam_x: float, cam_y: float):
        # When hurt, flash on alternate frames
        if self.hurt_timer > 0 and (int(self.hurt_timer * 20) % 2 == 0):
            return

        sx = self.x - cam_x
        sy = self.y - cam_y

        tag = "player"

        # Overall shadow beneath player when grounded
        if self.grounded:
            canvas.create_oval(
                sx + 2, sy + self.h - 3, sx + self.w - 2, sy + self.h + 3,
                fill="#0a101d", outline="", tags=tag
            )

        # Direction flip
        flip = 1 if self.facing_right else -1
        cx = sx + self.w / 2

        # In-air jumping pose vs walking pose
        leg_offset = 0
        if not self.grounded:
            leg_offset = -2
        elif self.walk_frame in (1, 3):
            leg_offset = 2

        # 1. Shoes / Boots (Dark Brown)
        boot_color = "#5c2c16"
        canvas.create_rectangle(
            cx - 10, sy + 30 + leg_offset, cx - 2, sy + 36,
            fill=boot_color, outline="#2b1408", tags=tag
        )
        canvas.create_rectangle(
            cx + 2, sy + 30 - leg_offset, cx + 10, sy + 36,
            fill=boot_color, outline="#2b1408", tags=tag
        )

        # 2. Overalls / Pants (Royal Blue)
        overall_color = "#1e50a2"
        canvas.create_rectangle(
            cx - 9, sy + 18, cx + 9, sy + 31,
            fill=overall_color, outline="#0d2b5c", tags=tag
        )
        # Yellow Buttons on overalls
        canvas.create_oval(cx - 6, sy + 20, cx - 3, sy + 23, fill="#fcd116", outline="", tags=tag)
        canvas.create_oval(cx + 3, sy + 20, cx + 6, sy + 23, fill="#fcd116", outline="", tags=tag)

        # 3. Shirt / Torso & Sleeves (Mario Red)
        shirt_color = "#e52521"
        canvas.create_rectangle(
            cx - 11, sy + 15, cx + 11, sy + 22,
            fill=shirt_color, outline="#8a110e", tags=tag
        )
        # White gloves
        glove_color = "#ffffff"
        if not self.grounded and self.vy < 0:
            # Jumping fist up!
            canvas.create_oval(cx + 6 * flip, sy + 6, cx + 14 * flip, sy + 14, fill=glove_color, outline="#999", tags=tag)
            canvas.create_oval(cx - 12 * flip, sy + 20, cx - 6 * flip, sy + 26, fill=glove_color, outline="#999", tags=tag)
        else:
            canvas.create_oval(cx - 12, sy + 21, cx - 7, sy + 26, fill=glove_color, outline="#999", tags=tag)
            canvas.create_oval(cx + 7, sy + 21, cx + 12, sy + 26, fill=glove_color, outline="#999", tags=tag)

        # 4. Head / Face (Peach)
        skin_color = "#fed8b1"
        canvas.create_oval(
            cx - 8, sy + 6, cx + 8, sy + 18,
            fill=skin_color, outline="#d4a373", tags=tag
        )

        # 5. Eye (black with white twinkle)
        eye_x = cx + (2 if self.facing_right else -4)
        canvas.create_rectangle(eye_x, sy + 9, eye_x + 3, sy + 13, fill="#111111", outline="", tags=tag)
        canvas.create_rectangle(eye_x + 1, sy + 9, eye_x + 2, sy + 11, fill="#ffffff", outline="", tags=tag)

        # 6. Mustache (Dark brown/black)
        mustache_x = cx + (0 if self.facing_right else -7)
        canvas.create_oval(
            mustache_x, sy + 12, mustache_x + 7, sy + 16,
            fill="#2b1408", outline="", tags=tag
        )
        # Nose
        nose_x = cx + (4 if self.facing_right else -7)
        canvas.create_oval(nose_x, sy + 10, nose_x + 4, sy + 14, fill=skin_color, outline="#d4a373", tags=tag)

        # 7. Cap (Red with brim pointing in facing direction)
        canvas.create_rectangle(
            cx - 9, sy + 2, cx + 9, sy + 8,
            fill=shirt_color, outline="#8a110e", tags=tag
        )
        brim_x1 = cx - 4 if self.facing_right else cx - 12
        brim_x2 = cx + 12 if self.facing_right else cx + 4
        canvas.create_rectangle(
            brim_x1, sy + 6, brim_x2, sy + 9,
            fill=shirt_color, outline="#8a110e", tags=tag
        )


class Coin:
    """Collectible Gold Coin."""

    def __init__(self, x: float, y: float, value: int = 10):
        self.x = x
        self.y = y
        self.base_y = y
        self.w = 18.0
        self.h = 22.0
        self.value = value
        self.collected = False
        self.anim_phase = (x * 0.05) % (math.pi * 2)

    def reset(self):
        self.collected = False
        self.y = self.base_y

    def update(self, dt: float):
        if not self.collected:
            self.anim_phase += dt * 4.0
            # Gentle bobbing
            self.y = self.base_y + math.sin(self.anim_phase) * 3.0

    def draw(self, canvas, cam_x: float, cam_y: float):
        if self.collected:
            return

        sx = self.x - cam_x
        sy = self.y - cam_y

        tag = "coin"

        # Width modulation for 3D spin effect
        spin_scale = abs(math.cos(self.anim_phase))
        w_eff = max(4.0, self.w * spin_scale)
        cx = sx + self.w / 2
        cy = sy + self.h / 2

        # Outer gold rim
        canvas.create_oval(
            cx - w_eff / 2, cy - self.h / 2,
            cx + w_eff / 2, cy + self.h / 2,
            fill="#ffd700", outline="#b8860b", width=1.5, tags=tag
        )
        # Inner shiny center
        if w_eff > 8:
            canvas.create_oval(
                cx - (w_eff - 6) / 2, cy - (self.h - 6) / 2,
                cx + (w_eff - 6) / 2, cy + (self.h - 6) / 2,
                fill="#fff275", outline="#e6a100", width=1, tags=tag
            )
            # Center star/rectangle sparkle
            canvas.create_rectangle(
                cx - 1, cy - 4, cx + 1, cy + 4,
                fill="#ffffff", outline="", tags=tag
            )


class Enemy:
    """Goomba-style walking enemy."""

    def __init__(self, x: float, y: float, min_x: float, max_x: float, speed: float = 1.2):
        self.spawn_x = x
        self.spawn_y = y
        self.x = x
        self.y = y
        self.min_x = min_x
        self.max_x = max_x
        self.speed = speed
        self.vx = -speed
        self.w = 26.0
        self.h = 24.0

        self.alive = True
        self.squished = False
        self.squish_timer = 0.0
        self.walk_tick = 0
        self.walk_frame = 0

    def reset(self):
        self.x = self.spawn_x
        self.y = self.spawn_y
        self.vx = -self.speed
        self.alive = True
        self.squished = False
        self.squish_timer = 0.0
        self.walk_tick = 0
        self.walk_frame = 0

    def squish(self):
        """When player stomps the enemy."""
        self.squished = True
        self.alive = False
        self.squish_timer = 0.5
        self.vx = 0.0

    def update(self, dt: float):
        if self.squished:
            self.squish_timer = max(0.0, self.squish_timer - dt)
            return

        if not self.alive:
            return

        self.x += self.vx
        if self.x <= self.min_x:
            self.x = self.min_x
            self.vx = self.speed
        elif self.x >= self.max_x:
            self.x = self.max_x
            self.vx = -self.speed

        self.walk_tick += 1
        if self.walk_tick >= 10:
            self.walk_frame = (self.walk_frame + 1) % 2
            self.walk_tick = 0

    def draw(self, canvas, cam_x: float, cam_y: float):
        if not self.alive and not self.squished:
            return
        if self.squished and self.squish_timer <= 0:
            return

        sx = self.x - cam_x
        sy = self.y - cam_y
        cx = sx + self.w / 2
        tag = "enemy"

        if self.squished:
            # Flattened pancake
            canvas.create_oval(
                cx - 14, sy + 16, cx + 14, sy + 24,
                fill="#8b4513", outline="#4a2408", tags=tag
            )
            # Squished eyes (lines)
            canvas.create_line(cx - 7, sy + 19, cx - 2, sy + 19, fill="#ffffff", width=2, tags=tag)
            canvas.create_line(cx + 2, sy + 19, cx + 7, sy + 19, fill="#ffffff", width=2, tags=tag)
            return

        # 1. Dark feet waddling
        foot_color = "#1f1007"
        f_off = 2 if self.walk_frame == 0 else -2
        canvas.create_oval(cx - 11, sy + 18 + f_off, cx - 3, sy + 24, fill=foot_color, outline="", tags=tag)
        canvas.create_oval(cx + 3, sy + 18 - f_off, cx + 11, sy + 24, fill=foot_color, outline="", tags=tag)

        # 2. Tan stem / body
        canvas.create_rectangle(
            cx - 7, sy + 12, cx + 7, sy + 20,
            fill="#d2b48c", outline="#a08260", tags=tag
        )

        # 3. Brown mushroom head
        canvas.create_oval(
            cx - 13, sy + 2, cx + 13, sy + 16,
            fill="#8b4513", outline="#4a2408", width=1.5, tags=tag
        )

        # 4. Angry eyes (tilted black & white)
        # Left eye
        canvas.create_polygon(
            cx - 7, sy + 7, cx - 2, sy + 9, cx - 3, sy + 14, cx - 7, sy + 13,
            fill="#ffffff", outline="#000", tags=tag
        )
        canvas.create_oval(cx - 5, sy + 9, cx - 3, sy + 13, fill="#000000", outline="", tags=tag)
        # Right eye
        canvas.create_polygon(
            cx + 2, sy + 9, cx + 7, sy + 7, cx + 7, sy + 13, cx + 3, sy + 14,
            fill="#ffffff", outline="#000", tags=tag
        )
        canvas.create_oval(cx + 3, sy + 9, cx + 5, sy + 13, fill="#000000", outline="", tags=tag)

        # 5. Little fangs
        canvas.create_polygon(cx - 5, sy + 16, cx - 3, sy + 16, cx - 4, sy + 13, fill="#fff", outline="", tags=tag)
        canvas.create_polygon(cx + 3, sy + 16, cx + 5, sy + 16, cx + 4, sy + 13, fill="#fff", outline="", tags=tag)


class Platform:
    """Solid platform / block / pipe."""

    def __init__(self, x: float, y: float, w: float, h: float, kind: str = "ground"):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.kind = kind  # "ground", "brick", "question", "pipe"

    def draw(self, canvas, cam_x: float, cam_y: float):
        sx = self.x - cam_x
        sy = self.y - cam_y
        tag = "platform"

        if self.kind == "ground":
            # Grassy green top bar (5px)
            canvas.create_rectangle(
                sx, sy, sx + self.w, sy + 6,
                fill="#48bb78", outline="#276749", tags=tag
            )
            # Rich dirt underground
            canvas.create_rectangle(
                sx, sy + 6, sx + self.w, sy + self.h,
                fill="#795548", outline="#4e342e", tags=tag
            )
            # Subtile dirt detail stones
            for step_x in range(int(sx) + 10, int(sx + self.w) - 10, 32):
                canvas.create_rectangle(
                    step_x, sy + 14, step_x + 8, sy + 20,
                    fill="#5d4037", outline="", tags=tag
                )

        elif self.kind == "brick":
            # Terracotta brick block
            canvas.create_rectangle(
                sx, sy, sx + self.w, sy + self.h,
                fill="#b85d32", outline="#5c2409", width=1.5, tags=tag
            )
            # Mortar lines
            mid_y = sy + self.h / 2
            canvas.create_line(sx, mid_y, sx + self.w, mid_y, fill="#421a05", tags=tag)
            canvas.create_line(sx + self.w / 2, sy, sx + self.w / 2, mid_y, fill="#421a05", tags=tag)
            canvas.create_line(sx + self.w / 4, mid_y, sx + self.w / 4, sy + self.h, fill="#421a05", tags=tag)
            canvas.create_line(sx + 3 * self.w / 4, mid_y, sx + 3 * self.w / 4, sy + self.h, fill="#421a05", tags=tag)

        elif self.kind == "question":
            # Golden question block
            canvas.create_rectangle(
                sx, sy, sx + self.w, sy + self.h,
                fill="#f59e0b", outline="#b45309", width=2, tags=tag
            )
            # 4 corner screws
            for cx, cy in [(sx + 3, sy + 3), (sx + self.w - 3, sy + 3),
                           (sx + 3, sy + self.h - 3), (sx + self.w - 3, sy + self.h - 3)]:
                canvas.create_oval(cx - 1.5, cy - 1.5, cx + 1.5, cy + 1.5, fill="#78350f", outline="", tags=tag)
            # Question mark '?'
            canvas.create_text(
                sx + self.w / 2, sy + self.h / 2,
                text="?", fill="#ffffff", font=("Segoe UI", 13, "bold"), tags=tag
            )

        elif self.kind == "pipe":
            # Warp pipe body (green)
            canvas.create_rectangle(
                sx + 3, sy + 10, sx + self.w - 3, sy + self.h,
                fill="#22c55e", outline="#15803d", width=1.5, tags=tag
            )
            # Warp pipe top lip
            canvas.create_rectangle(
                sx, sy, sx + self.w, sy + 12,
                fill="#22c55e", outline="#15803d", width=2, tags=tag
            )
            # Pipe highlight streak
            canvas.create_line(
                sx + 6, sy + 2, sx + 6, sy + self.h - 2,
                fill="#86efac", width=2, tags=tag
            )


class Goal:
    """Flagpole and victory castle marking the level end."""

    def __init__(self, x: float, y: float, height: float = 180.0):
        self.x = x
        self.y = y
        self.h = height
        self.flag_y = y - height + 10
        self.flag_dropped = False

    def reset(self):
        self.flag_dropped = False
        self.flag_y = self.y - self.h + 10

    def trigger_win(self):
        self.flag_dropped = True

    def update(self, dt: float):
        if self.flag_dropped:
            target_y = self.y - 25
            if self.flag_y < target_y:
                self.flag_y = min(target_y, self.flag_y + 160.0 * dt)

    def draw(self, canvas, cam_x: float, cam_y: float):
        sx = self.x - cam_x
        sy = self.y - cam_y
        tag = "goal"

        # 1. Stone pedestal
        canvas.create_rectangle(
            sx - 14, sy - 14, sx + 14, sy,
            fill="#64748b", outline="#334155", width=1.5, tags=tag
        )

        # 2. Flagpole (metallic pole)
        pole_top_y = sy - self.h
        canvas.create_rectangle(
            sx - 2, pole_top_y, sx + 2, sy - 14,
            fill="#cbd5e1", outline="#94a3b8", tags=tag
        )

        # 3. Golden finial ball at top
        canvas.create_oval(
            sx - 6, pole_top_y - 6, sx + 6, pole_top_y + 6,
            fill="#facc15", outline="#ca8a04", tags=tag
        )

        # 4. Triangle Flag
        fy = self.flag_y - cam_y
        canvas.create_polygon(
            sx + 2, fy, sx + 24, fy + 10, sx + 2, fy + 20,
            fill="#22c55e", outline="#15803d", tags=tag
        )

        # 5. Mini castle behind the pole
        cx = sx + 70
        canvas.create_rectangle(
            cx - 30, sy - 60, cx + 30, sy,
            fill="#94a3b8", outline="#475569", width=2, tags=tag
        )
        # Castle battlements
        for bx in range(int(cx - 28), int(cx + 25), 14):
            canvas.create_rectangle(
                bx, sy - 72, bx + 10, sy - 60,
                fill="#94a3b8", outline="#475569", tags=tag
            )
        # Castle arched doorway
        canvas.create_oval(
            cx - 10, sy - 34, cx + 10, sy - 14,
            fill="#0f172a", outline="", tags=tag
        )
        canvas.create_rectangle(
            cx - 10, sy - 24, cx + 10, sy,
            fill="#0f172a", outline="", tags=tag
        )


class Particle:
    """Floating notification or sparkle particle."""

    def __init__(self, x: float, y: float, text: str, color: str = "#ffd700", lifetime: float = 1.0):
        self.x = x
        self.y = y
        self.text = text
        self.color = color
        self.lifetime = lifetime
        self.age = 0.0

    @property
    def is_alive(self) -> bool:
        return self.age < self.lifetime

    def update(self, dt: float):
        self.age += dt
        self.y -= 25.0 * dt  # float upwards

    def draw(self, canvas, cam_x: float, cam_y: float):
        if not self.is_alive:
            return
        sx = self.x - cam_x
        sy = self.y - cam_y
        canvas.create_text(
            sx, sy, text=self.text, fill=self.color,
            font=("Segoe UI", 10, "bold"), tags="particle"
        )
