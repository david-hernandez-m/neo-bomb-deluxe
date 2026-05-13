import json
import random
import sys
from collections import deque
from math import sin
from pathlib import Path

import pygame

pygame.init()
pygame.display.set_caption("Neo Bomb Deluxe - Improved")
clock = pygame.time.Clock()

# =========================
# CONFIG
# =========================
TILE = 64
COLS = 13
ROWS = 11
HUD_H = 78
WIDTH = COLS * TILE
HEIGHT = ROWS * TILE + HUD_H
FPS = 60
ROUND_TIME = 180

BASE_DIR = Path(__file__).parent
ASSET_DIR = BASE_DIR / "assets"
SAVE_FILE = BASE_DIR / "neo_bomb_save.json"

DIFFICULTY_EASY = "easy"
DIFFICULTY_NORMAL = "normal"
DIFFICULTY_HARD = "hard"

STATE_MENU = "menu"
STATE_PLAYING = "playing"
STATE_PAUSED = "paused"
STATE_GAME_OVER = "game_over"
STATE_LEVEL_CLEAR = "level_clear"

POWER_BOMB = "bomb"
POWER_RANGE = "range"
POWER_SPEED = "speed"
POWER_SHIELD = "shield"
POWER_REMOTE = "remote"
POWER_KICK = "kick"

PERFORMANCE_MODE = True

LEVEL_CLEAR_DELAY = 1.2
SPAWN_PROTECTION_TIME = 1.0

if PERFORMANCE_MODE:
    MAX_PARTICLES_EXPLOSION = 8
    MAX_PARTICLES_BREAK = 5
    USE_GLOW = True
    USE_SMOOTH_SCALE = False
    ENEMY_PATH_INTERVAL_NORMAL = 32
    ENEMY_PATH_INTERVAL_FAST = 26
    ENEMY_PATH_INTERVAL_GHOST = 24
else:
    MAX_PARTICLES_EXPLOSION = 16
    MAX_PARTICLES_BREAK = 10
    USE_GLOW = True
    USE_SMOOTH_SCALE = True
    ENEMY_PATH_INTERVAL_NORMAL = 20
    ENEMY_PATH_INTERVAL_FAST = 18
    ENEMY_PATH_INTERVAL_GHOST = 16

# =========================
# PANTALLA
# =========================
display_info = pygame.display.Info()
MONITOR_W = display_info.current_w
MONITOR_H = display_info.current_h

WINDOWED_SCALE = 1.15
WINDOW_W = int(WIDTH * WINDOWED_SCALE)
WINDOW_H = int(HEIGHT * WINDOWED_SCALE)

is_fullscreen = False
SCREEN = pygame.display.set_mode((WINDOW_W, WINDOW_H))
GAME_SURFACE = pygame.Surface((WIDTH, HEIGHT))


def recreate_screen() -> None:
    global SCREEN
    if is_fullscreen:
        SCREEN = pygame.display.set_mode((MONITOR_W, MONITOR_H), pygame.FULLSCREEN)
    else:
        SCREEN = pygame.display.set_mode((WINDOW_W, WINDOW_H))


def get_screen_size() -> tuple[int, int]:
    return SCREEN.get_width(), SCREEN.get_height()


# =========================
# COLORES
# =========================
BG = (8, 10, 18)
GRID = (20, 30, 48)

FLOOR_A = (22, 28, 42)
FLOOR_B = (16, 22, 36)

WALL = (70, 180, 255)
WALL_DARK = (20, 70, 130)
WALL_HL = (180, 240, 255)

BLOCK = (255, 160, 60)
BLOCK_DARK = (170, 80, 10)
BLOCK_HL = (255, 220, 150)

PLAYER = (80, 255, 170)
PLAYER_DARK = (10, 120, 80)

ENEMY = (255, 80, 120)
ENEMY_DARK = (130, 18, 55)
GHOST_COLOR = (180, 120, 255)
GHOST_DARK = (90, 40, 140)

BOSS_MAIN = (255, 70, 70)
BOSS_DARK = (120, 20, 20)
BOSS_HL = (255, 160, 160)

BOMB = (24, 24, 28)
BOMB_HL = (255, 255, 255)
BOMB_GLOW = (255, 190, 90)

EXP_CORE = (255, 250, 220)
EXP_MID = (255, 180, 60)
EXP_OUT = (255, 90, 30)

TEXT = (240, 245, 255)
SHADOW = (0, 0, 0)
CYAN = (80, 240, 255)
MAGENTA = (255, 70, 190)
YELLOW = (255, 225, 70)
RED = (255, 70, 70)
GREEN = (110, 255, 130)
WHITE_SAFE = (245, 245, 245)
DOOR_COLOR = (180, 120, 255)
DOOR_GLOW = (220, 180, 255)
SHIELD_COLOR = (120, 220, 255)
REMOTE_COLOR = (255, 120, 220)
KICK_COLOR = (255, 235, 120)

BLUE_UP = (120, 170, 255)
ORANGE_UP = (255, 180, 80)
LIME_UP = (160, 255, 120)

# =========================
# UTILIDADES
# =========================
def pixel_to_cell(px, py):
    return int(px // TILE), int((py - HUD_H) // TILE)


def in_bounds(cx, cy):
    return 0 <= cx < COLS and 0 <= cy < ROWS


def draw_text(surface, txt, size, x, y, color=TEXT, center=False, shadow=True):
    font = pygame.font.SysFont("arial", size, bold=True)
    img = font.render(txt, True, color)
    rect = img.get_rect()

    if center:
        rect.center = (x, y)
    else:
        rect.topleft = (x, y)

    if shadow:
        sh = font.render(txt, True, SHADOW)
        surface.blit(sh, (rect.x + 2, rect.y + 2))

    surface.blit(img, rect)


def trim_transparent_borders(img):
    rect = img.get_bounding_rect()
    if rect.width == 0 or rect.height == 0:
        return img
    return img.subsurface(rect).copy()


def fit_sprite_to_tile(img, size):
    tile_w, tile_h = size
    iw, ih = img.get_size()

    if iw == 0 or ih == 0:
        return pygame.Surface(size, pygame.SRCALPHA)

    scale = min((tile_w * 0.9) / iw, (tile_h * 0.9) / ih)
    new_w = max(1, int(iw * scale))
    new_h = max(1, int(ih * scale))

    scaler = pygame.transform.smoothscale if USE_SMOOTH_SCALE else pygame.transform.scale
    scaled = scaler(img, (new_w, new_h))

    final = pygame.Surface(size, pygame.SRCALPHA)
    x = (tile_w - new_w) // 2
    y = (tile_h - new_h) // 2
    final.blit(scaled, (x, y))
    return final


def load_sprite(filename, size, remove_bg=False):
    path = ASSET_DIR / filename
    if not path.exists():
        return None

    img = pygame.image.load(str(path)).convert_alpha()

    if remove_bg:
        bg = img.get_at((0, 0))
        img.set_colorkey(bg)

    img = trim_transparent_borders(img)
    return fit_sprite_to_tile(img, size)


def load_save_data():
    if SAVE_FILE.exists():
        try:
            with open(SAVE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {
                    "high_score": int(data.get("high_score", 0)),
                    "best_level": int(data.get("best_level", 1)),
                }
        except Exception:
            pass
    return {"high_score": 0, "best_level": 1}


def save_progress(high_score, best_level):
    data = {"high_score": int(high_score), "best_level": int(best_level)}
    try:
        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


def make_level():
    grid = [[0 for _ in range(COLS)] for _ in range(ROWS)]

    for y in range(ROWS):
        for x in range(COLS):
            if x == 0 or y == 0 or x == COLS - 1 or y == ROWS - 1:
                grid[y][x] = 1

    for y in range(2, ROWS - 1, 2):
        for x in range(2, COLS - 1, 2):
            grid[y][x] = 1

    safe = {
        (1, 1), (1, 2), (2, 1),
        (COLS - 2, ROWS - 2), (COLS - 3, ROWS - 2), (COLS - 2, ROWS - 3),
    }

    for y in range(1, ROWS - 1):
        for x in range(1, COLS - 1):
            if grid[y][x] == 0 and (x, y) not in safe:
                if random.random() < 0.45:
                    grid[y][x] = 2

    return grid


def draw_scaled_to_screen(source_surface):
    screen_w, screen_h = get_screen_size()
    scale = min(screen_w / WIDTH, screen_h / HEIGHT)
    scaled_w = int(WIDTH * scale)
    scaled_h = int(HEIGHT * scale)

    scaler = pygame.transform.smoothscale if USE_SMOOTH_SCALE else pygame.transform.scale
    scaled = scaler(source_surface, (scaled_w, scaled_h))

    SCREEN.fill((0, 0, 0))
    offset_x = (screen_w - scaled_w) // 2
    offset_y = (screen_h - scaled_h) // 2
    SCREEN.blit(scaled, (offset_x, offset_y))
    pygame.display.flip()


# =========================
# ASSETS
# =========================
class Assets:
    def __init__(self):
        self.player = load_sprite("player.png", (TILE, TILE), remove_bg=True)
        self.enemy = load_sprite("enemy.png", (TILE, TILE), remove_bg=True)
        self.wall = load_sprite("wall.png", (TILE, TILE), remove_bg=True)
        self.block = load_sprite("block.png", (TILE, TILE), remove_bg=True)
        self.bomb = load_sprite("bomb.png", (TILE, TILE), remove_bg=True)
        self.power_bomb = load_sprite("power_bomb.png", (TILE, TILE), remove_bg=True)
        self.power_range = load_sprite("power_range.png", (TILE, TILE), remove_bg=True)
        self.power_speed = load_sprite("power_speed.png", (TILE, TILE), remove_bg=True)
        self.power_shield = load_sprite("power_shield.png", (TILE, TILE), remove_bg=True)
        self.power_remote = load_sprite("power_remote.png", (TILE, TILE), remove_bg=True)
        self.power_kick = load_sprite("power_kick.png", (TILE, TILE), remove_bg=True)


assets = Assets()

# =========================
# EFECTOS
# =========================
def draw_shadow(surface, x, y, w, h):
    shadow_surf = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow_surf, (0, 0, 0, 70), (0, 0, w, h))
    surface.blit(shadow_surf, (x, y))


def draw_glow_circle(surface, x, y, radius, color):
    if not USE_GLOW:
        return
    glow = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    for r, a in [(radius, 18), (radius - 8, 24)]:
        if r > 0:
            pygame.draw.circle(glow, (*color, a), (radius, radius), r)
    surface.blit(glow, (x - radius, y - radius))


# =========================
# FONDO
# =========================
class Star:
    def __init__(self):
        self.x = random.randint(0, WIDTH)
        self.y = random.randint(0, HEIGHT)
        self.speed = random.uniform(0.2, 1.2)
        self.size = random.randint(1, 2)

    def update(self):
        self.y += self.speed
        if self.y > HEIGHT:
            self.y = -5
            self.x = random.randint(0, WIDTH)

    def draw(self, surface):
        pygame.draw.circle(surface, (70, 120, 180), (int(self.x), int(self.y)), self.size)


stars = [Star() for _ in range(28)]

# =========================
# PARTICULAS Y TEXTO
# =========================
class Particle:
    def __init__(self, x, y, color, vx, vy, life, radius):
        self.x = x
        self.y = y
        self.color = color
        self.vx = vx
        self.vy = vy
        self.life = life
        self.max_life = life
        self.radius = radius

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.05
        self.life -= 1

    def draw(self, surface, ox=0, oy=0):
        if self.life <= 0:
            return
        r = max(1, int(self.radius * (self.life / self.max_life)))
        pygame.draw.circle(surface, self.color, (int(self.x + ox), int(self.y + oy)), r)


class FloatingText:
    def __init__(self, x, y, text, color=YELLOW, life=45):
        self.x = x
        self.y = y
        self.text = text
        self.color = color
        self.life = life

    def update(self):
        self.y -= 0.6
        self.life -= 1

    def draw(self, surface, ox=0, oy=0):
        if self.life <= 0:
            return
        font = pygame.font.SysFont("arial", 18, bold=True)
        shadow = font.render(self.text, True, SHADOW)
        img = font.render(self.text, True, self.color)
        surface.blit(shadow, (self.x + ox + 2, self.y + oy + 2))
        surface.blit(img, (self.x + ox, self.y + oy))


# =========================
# COLISIONES Y PATH
# =========================
def cell_walkable(state, cx, cy, ignore_blocks=False):
    if not in_bounds(cx, cy):
        return False
    if ignore_blocks:
        if state.grid[cy][cx] == 1:
            return False
    else:
        if state.grid[cy][cx] != 0:
            return False
    for bomb in state.bombs:
        if (bomb.cx, bomb.cy) == (cx, cy):
            return False
    return True


def find_path(state, start, goal, max_depth=10, ignore_blocks=False):
    if start == goal:
        return []

    q = deque()
    q.append((start, []))
    visited = {start}

    while q:
        (cx, cy), path = q.popleft()
        if len(path) >= max_depth:
            continue

        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            nx, ny = cx + dx, cy + dy
            nxt = (nx, ny)

            if nxt in visited:
                continue
            if nxt != goal and not cell_walkable(state, nx, ny, ignore_blocks=ignore_blocks):
                continue
            if nxt == goal:
                return path + [nxt]

            visited.add(nxt)
            q.append((nxt, path + [nxt]))

    return []


def get_rect_points(px, py, radius):
    cpx = px + TILE // 2
    cpy = py + TILE // 2
    return [
        (cpx - radius, cpy - radius),
        (cpx + radius, cpy - radius),
        (cpx - radius, cpy + radius),
        (cpx + radius, cpy + radius),
    ]


def collides_world(px, py, radius, state, ignore_player_bomb=False):
    pts = get_rect_points(px, py, radius)

    for sx, sy in pts:
        cx, cy = pixel_to_cell(sx, sy)
        if not in_bounds(cx, cy):
            return True
        if state.grid[cy][cx] in (1, 2):
            return True

    for b in state.bombs:
        if ignore_player_bomb and (b.cx, b.cy) == (state.player.cx, state.player.cy):
            continue
        bomb_rect = pygame.Rect(b.px + 14, b.py + 14, TILE - 28, TILE - 28)
        entity_rect = pygame.Rect(px + 14, py + 14, TILE - 28, TILE - 28)
        if entity_rect.colliderect(bomb_rect):
            return True

    return False


def collides_world_enemy(px, py, radius, state, kind="normal"):
    pts = get_rect_points(px, py, radius)

    for sx, sy in pts:
        cx, cy = pixel_to_cell(sx, sy)
        if not in_bounds(cx, cy):
            return True
        if kind == "ghost":
            if state.grid[cy][cx] == 1:
                return True
        else:
            if state.grid[cy][cx] in (1, 2):
                return True

    for b in state.bombs:
        bomb_rect = pygame.Rect(b.px + 14, b.py + 14, TILE - 28, TILE - 28)
        entity_rect = pygame.Rect(px + 14, py + 14, TILE - 28, TILE - 28)
        if entity_rect.colliderect(bomb_rect):
            return True

    return False


def collides_world_boss(px, py, radius, state):
    pts = get_rect_points(px, py, radius)

    for sx, sy in pts:
        cx, cy = pixel_to_cell(sx, sy)
        if not in_bounds(cx, cy):
            return True
        if state.grid[cy][cx] == 1:
            return True

    for b in state.bombs:
        bomb_rect = pygame.Rect(b.px + 10, b.py + 10, TILE - 20, TILE - 20)
        entity_rect = pygame.Rect(px + 6, py + 6, TILE - 12, TILE - 12)
        if entity_rect.colliderect(bomb_rect):
            return True

    return False


def get_bomb_at_cell(state, cx, cy):
    for bomb in state.bombs:
        if (bomb.cx, bomb.cy) == (cx, cy):
            return bomb
    return None


def can_bomb_enter_cell(state, cx, cy, moving_bomb=None):
    if not in_bounds(cx, cy):
        return False
    if state.grid[cy][cx] != 0:
        return False
    for b in state.bombs:
        if b is moving_bomb:
            continue
        if (b.cx, b.cy) == (cx, cy):
            return False
    return True


# =========================
# ENTIDADES
# =========================
class Player:
    def __init__(self, cx, cy):
        self.cx = cx
        self.cy = cy
        self.px = cx * TILE
        self.py = cy * TILE + HUD_H
        self.speed = 3.8
        self.radius = 18
        self.max_bombs = 2
        self.power = 2
        self.active_bombs = 0
        self.lives = 3
        self.invuln = 0
        self.shield = 0
        self.remote_mode = False
        self.can_kick = False
        self.facing = (0, 1)

    def try_kick_bomb(self, dx, dy, state):
        front_cx = self.cx + dx
        front_cy = self.cy + dy
        bomb = get_bomb_at_cell(state, front_cx, front_cy)
        if not bomb:
            return False
        if bomb.moving_dx != 0 or bomb.moving_dy != 0:
            return False

        next_cx = bomb.cx + dx
        next_cy = bomb.cy + dy
        if can_bomb_enter_cell(state, next_cx, next_cy, moving_bomb=bomb):
            bomb.moving_dx = dx
            bomb.moving_dy = dy
            return True
        return False

    def move(self, dx, dy, state):
        if dx == 0 and dy == 0:
            return

        self.facing = (dx, dy)

        new_px = self.px + dx * self.speed
        new_py = self.py + dy * self.speed

        moved_x = False
        moved_y = False

        if not collides_world(new_px, self.py, self.radius, state, ignore_player_bomb=True):
            self.px = new_px
            moved_x = True
        elif dx != 0 and self.can_kick:
            self.try_kick_bomb(dx, 0, state)

        if not collides_world(self.px, new_py, self.radius, state, ignore_player_bomb=True):
            self.py = new_py
            moved_y = True
        elif dy != 0 and self.can_kick:
            self.try_kick_bomb(0, dy, state)

        self.cx, self.cy = pixel_to_cell(self.px + TILE // 2, self.py + TILE // 2)


class Enemy:
    def __init__(self, cx, cy, kind="normal"):
        self.cx = cx
        self.cy = cy
        self.px = cx * TILE
        self.py = cy * TILE + HUD_H
        self.radius = 18
        self.kind = kind
        self.dir = random.choice([(1, 0), (-1, 0), (0, 1), (0, -1)])
        self.change_timer = random.randint(20, 60)
        self.path_timer = 0
        self.path = []

        if kind == "fast":
            self.speed = 2.8
            self.chase_range = 5
            self.path_interval = ENEMY_PATH_INTERVAL_FAST
        elif kind == "ghost":
            self.speed = 2.35
            self.chase_range = 7
            self.path_interval = ENEMY_PATH_INTERVAL_GHOST
        else:
            self.speed = 2.0
            self.chase_range = 4
            self.path_interval = ENEMY_PATH_INTERVAL_NORMAL

    def update(self, state):
        self.change_timer -= 1
        self.path_timer -= 1

        ex, ey = self.cx, self.cy
        px, py = state.player.cx, state.player.cy
        distance = abs(ex - px) + abs(ey - py)

        ignore_blocks = self.kind == "ghost"

        if distance <= self.chase_range and self.path_timer <= 0:
            self.path = find_path(state, (ex, ey), (px, py), max_depth=12, ignore_blocks=ignore_blocks)
            self.path_timer = self.path_interval

        if self.path:
            next_cell = self.path[0]
            dx = 0
            dy = 0

            if next_cell[0] > ex:
                dx = 1
            elif next_cell[0] < ex:
                dx = -1
            elif next_cell[1] > ey:
                dy = 1
            elif next_cell[1] < ey:
                dy = -1

            new_px = self.px + dx * self.speed
            new_py = self.py + dy * self.speed

            moved = False
            if dx != 0 and not collides_world_enemy(new_px, self.py, self.radius, state, self.kind):
                self.px = new_px
                moved = True
            if dy != 0 and not collides_world_enemy(self.px, new_py, self.radius, state, self.kind):
                self.py = new_py
                moved = True

            self.cx, self.cy = pixel_to_cell(self.px + TILE // 2, self.py + TILE // 2)

            if (self.cx, self.cy) == next_cell:
                self.path.pop(0)

            if not moved:
                self.path = []
        else:
            if self.change_timer <= 0:
                self.dir = random.choice([(1, 0), (-1, 0), (0, 1), (0, -1)])
                self.change_timer = random.randint(18, 45)

            dx, dy = self.dir
            new_px = self.px + dx * self.speed
            new_py = self.py + dy * self.speed

            blocked = False
            if not collides_world_enemy(new_px, self.py, self.radius, state, self.kind):
                self.px = new_px
            else:
                blocked = True

            if not collides_world_enemy(self.px, new_py, self.radius, state, self.kind):
                self.py = new_py
            else:
                blocked = True

            self.cx, self.cy = pixel_to_cell(self.px + TILE // 2, self.py + TILE // 2)

            if blocked:
                self.dir = random.choice([(1, 0), (-1, 0), (0, 1), (0, -1)])


class Boss:
    def __init__(self, cx, cy, level):
        self.cx = cx
        self.cy = cy
        self.px = cx * TILE
        self.py = cy * TILE + HUD_H
        self.radius = 26
        self.base_speed = min(2.2 + level * 0.03, 3.0)
        self.speed = self.base_speed
        self.hp_max = 6 + level // 2
        self.hp = self.hp_max
        self.dir = random.choice([(1, 0), (-1, 0), (0, 1), (0, -1)])
        self.change_timer = 0
        self.attack_timer = 160
        self.invuln = 0
        self.phase = 1
        self.phase_message_timer = 0

    def update(self, state):
        self.change_timer -= 1
        self.attack_timer -= 1

        if self.invuln > 0:
            self.invuln -= 1

        if self.phase == 1 and self.hp <= max(1, self.hp_max // 2):
            self.phase = 2
            self.speed = self.base_speed + 0.8
            self.phase_message_timer = 90
            state.camera_shake = max(state.camera_shake, 10)

        if self.phase_message_timer > 0:
            self.phase_message_timer -= 1

        if self.change_timer <= 0:
            px, py = state.player.cx, state.player.cy
            dx = 0
            dy = 0
            if abs(px - self.cx) > abs(py - self.cy):
                dx = 1 if px > self.cx else -1
            else:
                dy = 1 if py > self.cy else -1

            choices = [(dx, dy), (1, 0), (-1, 0), (0, 1), (0, -1)]
            random.shuffle(choices)
            self.dir = choices[0]
            self.change_timer = 18 if self.phase == 1 else 10

        dx, dy = self.dir
        new_px = self.px + dx * self.speed
        new_py = self.py + dy * self.speed

        moved = False
        if dx != 0 and not collides_world_boss(new_px, self.py, self.radius, state):
            self.px = new_px
            moved = True
        if dy != 0 and not collides_world_boss(self.px, new_py, self.radius, state):
            self.py = new_py
            moved = True

        self.cx, self.cy = pixel_to_cell(self.px + TILE // 2, self.py + TILE // 2)

        if not moved:
            self.dir = random.choice([(1, 0), (-1, 0), (0, 1), (0, -1)])

        if self.attack_timer <= 0:
            self.spawn_attack(state)
            self.attack_timer = 140 if self.phase == 1 else 70

    def spawn_attack(self, state):
        positions = []
        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            bx = self.cx + dx
            by = self.cy + dy
            if in_bounds(bx, by) and state.grid[by][bx] == 0:
                positions.append((bx, by))

        if self.phase == 2:
            for dx, dy in [(1, 1), (-1, 1), (1, -1), (-1, -1)]:
                bx = self.cx + dx
                by = self.cy + dy
                if in_bounds(bx, by) and state.grid[by][bx] == 0:
                    positions.append((bx, by))

        random.shuffle(positions)
        count = 1 if self.phase == 1 else 3

        for bx, by in positions[:count]:
            occupied = any((b.cx, b.cy) == (bx, by) for b in state.bombs)
            if not occupied:
                state.bombs.append(Bomb(bx, by, 2 if self.phase == 1 else 3, owner="boss", remote=False))


class Bomb:
    def __init__(self, cx, cy, power, owner="player", remote=False):
        self.cx = cx
        self.cy = cy
        self.px = cx * TILE
        self.py = cy * TILE + HUD_H
        self.power = power
        self.timer = 999999 if remote else 105
        self.owner = owner
        self.remote = remote
        self.moving_dx = 0
        self.moving_dy = 0
        self.move_speed = 8

    def update_motion(self, state):
        if self.moving_dx == 0 and self.moving_dy == 0:
            return

        new_px = self.px + self.moving_dx * self.move_speed
        new_py = self.py + self.moving_dy * self.move_speed

        target_cx = int((new_px + TILE // 2) // TILE)
        target_cy = int((new_py - HUD_H + TILE // 2) // TILE)

        if not can_bomb_enter_cell(state, target_cx, target_cy, moving_bomb=self):
            self.snap_to_cell()
            self.moving_dx = 0
            self.moving_dy = 0
            return

        self.px = new_px
        self.py = new_py
        self.cx = int((self.px + TILE // 2) // TILE)
        self.cy = int((self.py - HUD_H + TILE // 2) // TILE)

        cell_px = self.cx * TILE
        cell_py = self.cy * TILE + HUD_H
        if abs(self.px - cell_px) < self.move_speed and abs(self.py - cell_py) < self.move_speed:
            self.px = cell_px
            self.py = cell_py

    def snap_to_cell(self):
        self.px = self.cx * TILE
        self.py = self.cy * TILE + HUD_H


class Explosion:
    def __init__(self, tiles):
        self.tiles = tiles
        self.timer = 24
        self.enemy_hits_processed = False


class PowerUp:
    def __init__(self, cx, cy, kind):
        self.cx = cx
        self.cy = cy
        self.kind = kind


class Door:
    def __init__(self, cx, cy):
        self.cx = cx
        self.cy = cy
        self.unlocked = False


# =========================
# GAME STATE
# =========================
class GameState:
    def __init__(self):
        self.menu_frame = 0
        self.save_data = load_save_data()
        self.high_score = self.save_data["high_score"]
        self.best_level = self.save_data["best_level"]
        self.difficulty = DIFFICULTY_NORMAL
        self.level_clear_timer = 0.0
        self.full_reset()

    def full_reset(self):
        self.level = 1
        self.score = 0
        self.player = Player(1, 1)
        self.state = STATE_MENU
        self.level_message_timer = 0
        self.floating_texts = []
        self.level_clear_timer = 0.0
        self.build_level(keep_stats=False)

    def is_boss_level(self):
        return self.level % 5 == 0

    def get_difficulty_config(self):
        if self.difficulty == DIFFICULTY_EASY:
            return {
                "enemy_bonus": 0,
                "time_bonus": 20,
                "fast_enemy_chance": 0.10,
                "ghost_enemy_chance": 0.08,
            }
        elif self.difficulty == DIFFICULTY_HARD:
            return {
                "enemy_bonus": 2,
                "time_bonus": -15,
                "fast_enemy_chance": 0.50,
                "ghost_enemy_chance": 0.28,
            }
        return {
            "enemy_bonus": 1,
            "time_bonus": 0,
            "fast_enemy_chance": 0.30,
            "ghost_enemy_chance": 0.16,
        }

    def build_level(self, keep_stats=True):
        cfg = self.get_difficulty_config()

        lives = self.player.lives if keep_stats else 3
        max_bombs = self.player.max_bombs if keep_stats else 2
        power = self.player.power if keep_stats else 2
        speed = self.player.speed if keep_stats else 3.8
        shield = self.player.shield if keep_stats else 0
        remote_mode = self.player.remote_mode if keep_stats else False
        can_kick = self.player.can_kick if keep_stats else False

        self.grid = make_level()

        self.player = Player(1, 1)
        self.player.lives = lives
        self.player.max_bombs = max_bombs
        self.player.power = power
        self.player.speed = speed
        self.player.shield = shield
        self.player.remote_mode = remote_mode
        self.player.can_kick = can_kick
        self.player.invuln = int(SPAWN_PROTECTION_TIME * FPS)

        self.bombs = []
        self.explosions = []
        self.powerups = []
        self.particles = []
        self.flash = 0
        self.time_left = max(55, ROUND_TIME - (self.level - 1) * 6 + cfg["time_bonus"])
        self.enemies = []
        self.boss = None
        self.camera_shake = 0
        self.door = None
        self.place_door()
        self.level_clear_timer = 0.0

        if self.is_boss_level():
            self.spawn_boss()
        else:
            self.spawn_enemies_for_level()

        self.level_message_timer = 90

    def restart_round(self):
        current_score = self.score
        current_level = self.level
        current_high = self.high_score
        current_best = self.best_level

        self.build_level(keep_stats=False)
        self.score = current_score
        self.level = current_level
        self.high_score = current_high
        self.best_level = current_best
        self.state = STATE_PLAYING

    def next_level(self):
        self.level += 1
        self.best_level = max(self.best_level, self.level)
        self.high_score = max(self.high_score, self.score)
        save_progress(self.high_score, self.best_level)
        self.build_level(keep_stats=True)
        self.state = STATE_PLAYING

    def place_door(self):
        candidates = []
        for y in range(1, ROWS - 1):
            for x in range(1, COLS - 1):
                if self.grid[y][x] == 0 and (x, y) not in [(1, 1), (1, 2), (2, 1)]:
                    candidates.append((x, y))
        if candidates:
            cx, cy = random.choice(candidates)
            self.door = Door(cx, cy)

    def spawn_enemies_for_level(self):
        cfg = self.get_difficulty_config()
        free = []
        for y in range(1, ROWS - 1):
            for x in range(1, COLS - 1):
                if self.grid[y][x] == 0 and (x, y) not in [(1, 1), (1, 2), (2, 1)]:
                    if self.door and (x, y) == (self.door.cx, self.door.cy):
                        continue
                    free.append((x, y))
        random.shuffle(free)

        enemy_count = min(3 + self.level + cfg["enemy_bonus"], 10)
        for i in range(min(enemy_count, len(free))):
            x, y = free[i]

            if self.level >= 4 and random.random() < cfg["ghost_enemy_chance"]:
                kind = "ghost"
            elif self.level >= 3 and random.random() < cfg["fast_enemy_chance"]:
                kind = "fast"
            else:
                kind = "normal"

            self.enemies.append(Enemy(x, y, kind))

    def spawn_boss(self):
        candidates = []
        for y in range(2, ROWS - 2):
            for x in range(2, COLS - 2):
                if self.grid[y][x] == 0 and self.grid[y][x + 1] == 0 and self.grid[y + 1][x] == 0:
                    candidates.append((x, y))

        if candidates:
            bx, by = random.choice(candidates)
        else:
            bx, by = COLS // 2, ROWS // 2

        self.boss = Boss(bx, by, self.level)


# =========================
# MECANICAS
# =========================
def add_score(state, points, cx=None, cy=None, color=YELLOW):
    state.score += points
    state.high_score = max(state.high_score, state.score)

    if cx is not None and cy is not None:
        px = cx * TILE + TILE // 2 - 10
        py = cy * TILE + HUD_H + TILE // 2 - 12
        state.floating_texts.append(FloatingText(px, py, f"+{points}", color=color))


def spawn_explosion_particles(state, cx, cy):
    base_x = cx * TILE + TILE // 2
    base_y = cy * TILE + HUD_H + TILE // 2
    for _ in range(MAX_PARTICLES_EXPLOSION):
        color = random.choice([EXP_CORE, EXP_MID, EXP_OUT, YELLOW])
        state.particles.append(
            Particle(
                base_x, base_y, color,
                random.uniform(-2.2, 2.2),
                random.uniform(-2.2, 0.5),
                random.randint(10, 18),
                random.randint(2, 4),
            )
        )


def spawn_break_particles(state, cx, cy):
    base_x = cx * TILE + TILE // 2
    base_y = cy * TILE + HUD_H + TILE // 2
    for _ in range(MAX_PARTICLES_BREAK):
        color = random.choice([BLOCK, BLOCK_HL, BLOCK_DARK])
        state.particles.append(
            Particle(
                base_x, base_y, color,
                random.uniform(-1.8, 1.8),
                random.uniform(-2.2, 0.2),
                random.randint(8, 14),
                random.randint(2, 3),
            )
        )


def place_bomb(state):
    p = state.player
    if p.active_bombs >= p.max_bombs:
        return

    cx, cy = p.cx, p.cy
    for b in state.bombs:
        if (b.cx, b.cy) == (cx, cy):
            return

    state.bombs.append(Bomb(cx, cy, p.power, owner="player", remote=p.remote_mode))
    p.active_bombs += 1


def detonate_remote_bombs(state):
    remote_positions = [(b.cx, b.cy) for b in state.bombs if b.remote and b.owner == "player"]
    for bx, by in remote_positions:
        current_index = next((i for i, b in enumerate(state.bombs) if (b.cx, b.cy) == (bx, by)), None)
        if current_index is not None:
            explode_bomb(current_index, state)


def maybe_spawn_powerup(state, cx, cy):
    if random.random() < 0.34:
        kind = random.choice([
            POWER_BOMB,
            POWER_RANGE,
            POWER_SPEED,
            POWER_SHIELD,
            POWER_REMOTE,
            POWER_KICK,
        ])
        state.powerups.append(PowerUp(cx, cy, kind))


def apply_powerup(state, powerup):
    p = state.player
    if powerup.kind == POWER_BOMB:
        p.max_bombs = min(6, p.max_bombs + 1)
    elif powerup.kind == POWER_RANGE:
        p.power = min(6, p.power + 1)
    elif powerup.kind == POWER_SPEED:
        p.speed = min(6, p.speed + 0.35)
    elif powerup.kind == POWER_SHIELD:
        p.shield = min(3, p.shield + 1)
    elif powerup.kind == POWER_REMOTE:
        p.remote_mode = True
    elif powerup.kind == POWER_KICK:
        p.can_kick = True

    add_score(state, 150, powerup.cx, powerup.cy, GREEN)


def damage_boss(state, amount=1):
    if not state.boss or state.boss.invuln > 0:
        return

    state.boss.hp -= amount
    state.boss.invuln = 18
    points = 300 if state.boss.phase == 1 else 500
    add_score(state, points, state.boss.cx, state.boss.cy, RED)
    state.camera_shake = max(state.camera_shake, 8)

    if state.boss.hp <= 0:
        add_score(state, 2000, state.boss.cx, state.boss.cy, CYAN)
        state.boss = None
        if state.door:
            state.door.unlocked = True


def explode_bomb(index, state):
    if index < 0 or index >= len(state.bombs):
        return

    bomb = state.bombs.pop(index)

    if bomb.owner == "player":
        state.player.active_bombs = max(0, state.player.active_bombs - 1)

    tiles = [(bomb.cx, bomb.cy, "center")]
    spawn_explosion_particles(state, bomb.cx, bomb.cy)

    directions = [(1, 0, "right"), (-1, 0, "left"), (0, 1, "down"), (0, -1, "up")]

    for dx, dy, part in directions:
        for step in range(1, bomb.power + 1):
            nx = bomb.cx + dx * step
            ny = bomb.cy + dy * step

            if not in_bounds(nx, ny):
                break

            cell = state.grid[ny][nx]
            if cell == 1:
                break

            tiles.append((nx, ny, part))
            spawn_explosion_particles(state, nx, ny)

            if cell == 2:
                state.grid[ny][nx] = 0
                add_score(state, 25, nx, ny, ORANGE_UP)
                maybe_spawn_powerup(state, nx, ny)
                spawn_break_particles(state, nx, ny)
                break

    state.explosions.append(Explosion(tiles))
    state.camera_shake = max(state.camera_shake, 7)

    if state.boss:
        boss_hit = False
        boss_rect = pygame.Rect(state.boss.px + 6, state.boss.py + 6, TILE - 12, TILE - 12)
        for tx, ty, _ in tiles:
            exp_rect = pygame.Rect(tx * TILE + 10, ty * TILE + HUD_H + 10, TILE - 20, TILE - 20)
            if boss_rect.colliderect(exp_rect):
                boss_hit = True
                break
        if boss_hit:
            damage_boss(state, 1)

    triggered_positions = set()
    for tx, ty, _ in tiles:
        for other in state.bombs:
            if (other.cx, other.cy) == (tx, ty):
                triggered_positions.add((other.cx, other.cy))

    for bx, by in triggered_positions:
        current_index = next((i for i, b in enumerate(state.bombs) if (b.cx, b.cy) == (bx, by)), None)
        if current_index is not None:
            explode_bomb(current_index, state)


def hit_player(state):
    p = state.player
    if p.invuln > 0:
        return

    if p.shield > 0:
        p.shield -= 1
        p.invuln = 70
        state.flash = 6
        state.camera_shake = max(state.camera_shake, 5)
        return

    p.lives -= 1
    p.invuln = 100
    state.flash = 8
    state.camera_shake = max(state.camera_shake, 8)

    if p.lives <= 0:
        state.state = STATE_GAME_OVER
        save_progress(state.high_score, state.best_level)
    else:
        p.px = TILE
        p.py = HUD_H + TILE
        p.cx, p.cy = 1, 1
        p.invuln = int(SPAWN_PROTECTION_TIME * FPS)


def update_moving_bombs(state):
    for bomb in state.bombs:
        bomb.update_motion(state)


def update_game(state, dt):
    if state.state == STATE_LEVEL_CLEAR:
        state.level_clear_timer -= dt
        if state.level_clear_timer <= 0:
            state.next_level()
        return

    if state.state != STATE_PLAYING:
        return

    state.time_left -= dt
    if state.time_left <= 0:
        state.time_left = 0
        state.state = STATE_GAME_OVER
        save_progress(state.high_score, state.best_level)
        return

    keys = pygame.key.get_pressed()
    dx = (1 if keys[pygame.K_RIGHT] or keys[pygame.K_d] else 0) - (1 if keys[pygame.K_LEFT] or keys[pygame.K_a] else 0)
    dy = (1 if keys[pygame.K_DOWN] or keys[pygame.K_s] else 0) - (1 if keys[pygame.K_UP] or keys[pygame.K_w] else 0)

    if dx != 0 and dy != 0:
        dy = 0

    state.player.move(dx, dy, state)
    update_moving_bombs(state)

    for i in range(len(state.bombs) - 1, -1, -1):
        if i >= len(state.bombs):
            continue
        if state.bombs[i].remote:
            continue
        state.bombs[i].timer -= 1
        if i < len(state.bombs) and state.bombs[i].timer <= 0:
            explode_bomb(i, state)

    for i in range(len(state.explosions) - 1, -1, -1):
        exp = state.explosions[i]
        exp.timer -= 1

        for tx, ty, _ in exp.tiles:
            if (state.player.cx, state.player.cy) == (tx, ty):
                hit_player(state)

        if not exp.enemy_hits_processed:
            killed = 0

            for tx, ty, _ in exp.tiles:
                for enemy in state.enemies[:]:
                    if (enemy.cx, enemy.cy) == (tx, ty):
                        state.enemies.remove(enemy)
                        killed += 1

                        if enemy.kind == "normal":
                            add_score(state, 250, tx, ty, MAGENTA)
                        elif enemy.kind == "fast":
                            add_score(state, 400, tx, ty, ORANGE_UP)
                        else:
                            add_score(state, 550, tx, ty, GHOST_COLOR)

                        state.camera_shake = max(state.camera_shake, 5)
                        spawn_explosion_particles(state, tx, ty)

            if killed >= 2:
                combo_bonus = killed * 150
                add_score(state, combo_bonus, state.player.cx, state.player.cy, CYAN)
                px = state.player.cx * TILE + TILE // 2 - 20
                py = state.player.cy * TILE + HUD_H + TILE // 2 - 36
                state.floating_texts.append(FloatingText(px, py, f"COMBO x{killed}", CYAN, life=55))

            exp.enemy_hits_processed = True

        if exp.timer <= 0:
            state.explosions.pop(i)

    for enemy in state.enemies:
        enemy.update(state)
        er = pygame.Rect(enemy.px + 14, enemy.py + 14, TILE - 28, TILE - 28)
        pr = pygame.Rect(state.player.px + 14, state.player.py + 14, TILE - 28, TILE - 28)
        if er.colliderect(pr):
            hit_player(state)

    if state.boss:
        state.boss.update(state)
        br = pygame.Rect(state.boss.px + 6, state.boss.py + 6, TILE - 12, TILE - 12)
        pr = pygame.Rect(state.player.px + 14, state.player.py + 14, TILE - 28, TILE - 28)
        if br.colliderect(pr):
            hit_player(state)

    for powerup in state.powerups[:]:
        if (powerup.cx, powerup.cy) == (state.player.cx, state.player.cy):
            apply_powerup(state, powerup)
            state.powerups.remove(powerup)

    for p in state.particles[:]:
        p.update()
        if p.life <= 0:
            state.particles.remove(p)

    for ft in state.floating_texts[:]:
        ft.update()
        if ft.life <= 0:
            state.floating_texts.remove(ft)

    if state.player.invuln > 0:
        state.player.invuln -= 1
    if state.flash > 0:
        state.flash -= 1
    if state.camera_shake > 0:
        state.camera_shake -= 1
    if state.level_message_timer > 0:
        state.level_message_timer -= 1

    if not state.boss and len(state.enemies) == 0 and state.door:
        state.door.unlocked = True

    if state.door and state.door.unlocked and (state.player.cx, state.player.cy) == (state.door.cx, state.door.cy):
        bonus = int(state.time_left * 5) + 500
        add_score(state, bonus, state.player.cx, state.player.cy, CYAN)
        state.high_score = max(state.high_score, state.score)
        state.best_level = max(state.best_level, state.level)
        save_progress(state.high_score, state.best_level)
        state.state = STATE_LEVEL_CLEAR
        state.level_clear_timer = LEVEL_CLEAR_DELAY


# =========================
# DIBUJO
# =========================
def draw_floor(surface, frame, ox=0, oy=0):
    for y in range(ROWS):
        for x in range(COLS):
            px = x * TILE + ox
            py = y * TILE + HUD_H + oy
            rect = pygame.Rect(px, py, TILE, TILE)

            color = FLOOR_A if (x + y) % 2 == 0 else FLOOR_B
            pygame.draw.rect(surface, color, rect)

            inner = rect.inflate(-8, -8)
            pygame.draw.rect(surface, (color[0] + 4, color[1] + 4, color[2] + 4), inner, 1, border_radius=6)
            pygame.draw.rect(surface, GRID, rect, 1)


def draw_wall(surface, x, y, ox=0, oy=0):
    px = x * TILE + ox
    py = y * TILE + HUD_H + oy
    if assets.wall:
        surface.blit(assets.wall, (px, py))
        return

    r = pygame.Rect(px + 6, py + 6, TILE - 12, TILE - 12)
    pygame.draw.rect(surface, WALL_DARK, r, border_radius=10)
    inner = r.inflate(-8, -8)
    pygame.draw.rect(surface, WALL, inner, border_radius=8)
    pygame.draw.line(surface, WALL_HL, (inner.x + 6, inner.y + 8), (inner.right - 6, inner.y + 8), 2)


def draw_block(surface, x, y, ox=0, oy=0):
    px = x * TILE + ox
    py = y * TILE + HUD_H + oy
    if assets.block:
        surface.blit(assets.block, (px, py))
        return

    r = pygame.Rect(px + 8, py + 8, TILE - 16, TILE - 16)
    pygame.draw.rect(surface, BLOCK_DARK, r, border_radius=8)
    inner = r.inflate(-6, -6)
    pygame.draw.rect(surface, BLOCK, inner, border_radius=7)
    pygame.draw.line(surface, BLOCK_HL, (inner.x + 6, inner.y + 8), (inner.right - 6, inner.y + 8), 2)


def draw_door(surface, door, frame, ox=0, oy=0):
    px = door.cx * TILE + ox
    py = door.cy * TILE + HUD_H + oy

    if door.unlocked:
        draw_glow_circle(surface, px + TILE // 2, py + TILE // 2, 22, DOOR_GLOW)

    r = pygame.Rect(px + 16, py + 10, TILE - 32, TILE - 20)
    color = DOOR_GLOW if door.unlocked else DOOR_COLOR
    pygame.draw.rect(surface, color, r, border_radius=10)
    pygame.draw.rect(surface, SHADOW, r, 2, border_radius=10)


def draw_player(surface, player, frame, ox=0, oy=0):
    x = int(player.px + ox)
    y = int(player.py + oy)

    if player.shield > 0:
        draw_glow_circle(surface, x + TILE // 2, y + TILE // 2, 28, SHIELD_COLOR)

    if assets.player:
        draw_shadow(surface, x + 16, y + TILE - 16, TILE - 32, 12)
        surface.blit(assets.player, (x, y))
    else:
        bob = int(1 * sin(frame * 0.18))
        draw_shadow(surface, x + 16, y + TILE - 16, TILE - 32, 12)
        body = pygame.Rect(x + 14, y + 10 + bob, TILE - 28, TILE - 22)
        pygame.draw.ellipse(surface, PLAYER_DARK, body)
        inner = body.inflate(-10, -10)
        pygame.draw.ellipse(surface, PLAYER, inner)
        visor = pygame.Rect(inner.centerx - 14, inner.y + 8, 28, 12)
        pygame.draw.rect(surface, CYAN, visor, border_radius=5)

    if player.can_kick:
        pygame.draw.circle(surface, KICK_COLOR, (x + TILE // 2 + 12, y + 18), 5)

    fx, fy = player.facing
    arrow_x = x + TILE // 2
    arrow_y = y + TILE // 2
    if fx == 1:
        pts = [(arrow_x + 16, arrow_y), (arrow_x + 4, arrow_y - 6), (arrow_x + 4, arrow_y + 6)]
    elif fx == -1:
        pts = [(arrow_x - 16, arrow_y), (arrow_x - 4, arrow_y - 6), (arrow_x - 4, arrow_y + 6)]
    elif fy == -1:
        pts = [(arrow_x, arrow_y - 16), (arrow_x - 6, arrow_y - 4), (arrow_x + 6, arrow_y - 4)]
    else:
        pts = [(arrow_x, arrow_y + 16), (arrow_x - 6, arrow_y + 4), (arrow_x + 6, arrow_y + 4)]
    pygame.draw.polygon(surface, WHITE_SAFE, pts)


def draw_enemy(surface, enemy, frame, ox=0, oy=0):
    x = int(enemy.px + ox)
    y = int(enemy.py + oy)

    if assets.enemy and enemy.kind != "ghost":
        draw_shadow(surface, x + 16, y + TILE - 16, TILE - 32, 12)
        surface.blit(assets.enemy, (x, y))
        return

    draw_shadow(surface, x + 16, y + TILE - 16, TILE - 32, 12)
    body = pygame.Rect(x + 14, y + 14, TILE - 28, TILE - 26)

    if enemy.kind == "normal":
        base_color = ENEMY
        dark_color = ENEMY_DARK
    elif enemy.kind == "fast":
        base_color = (255, 140, 80)
        dark_color = (140, 60, 20)
    else:
        base_color = GHOST_COLOR
        dark_color = GHOST_DARK
        draw_glow_circle(surface, x + TILE // 2, y + TILE // 2, 20, GHOST_COLOR)

    pygame.draw.rect(surface, dark_color, body, border_radius=14)
    inner = body.inflate(-8, -8)
    pygame.draw.rect(surface, base_color, inner, border_radius=12)

    if enemy.kind == "ghost":
        pygame.draw.circle(surface, WHITE_SAFE, (inner.centerx - 8, inner.y + 14), 4)
        pygame.draw.circle(surface, WHITE_SAFE, (inner.centerx + 8, inner.y + 14), 4)
        pygame.draw.circle(surface, SHADOW, (inner.centerx - 8, inner.y + 14), 1)
        pygame.draw.circle(surface, SHADOW, (inner.centerx + 8, inner.y + 14), 1)


def draw_boss(surface, boss, frame, ox=0, oy=0):
    x = int(boss.px + ox)
    y = int(boss.py + oy)

    glow_color = BOSS_MAIN if boss.phase == 1 else MAGENTA
    draw_glow_circle(surface, x + TILE // 2, y + TILE // 2, 34, glow_color)
    draw_shadow(surface, x + 10, y + TILE - 12, TILE - 20, 14)

    body = pygame.Rect(x + 4, y + 4, TILE - 8, TILE - 8)
    pygame.draw.rect(surface, BOSS_DARK, body, border_radius=18)

    inner = body.inflate(-8, -8)
    color = BOSS_MAIN if boss.phase == 1 else MAGENTA
    if boss.invuln > 0:
        color = WHITE_SAFE

    pygame.draw.rect(surface, color, inner, border_radius=15)
    pygame.draw.rect(surface, BOSS_HL, (inner.x + 8, inner.y + 8, inner.w - 18, 10), border_radius=4)

    pygame.draw.circle(surface, WHITE_SAFE, (inner.centerx - 10, inner.centery - 2), 6)
    pygame.draw.circle(surface, WHITE_SAFE, (inner.centerx + 10, inner.centery - 2), 6)
    pygame.draw.circle(surface, SHADOW, (inner.centerx - 10, inner.centery - 2), 2)
    pygame.draw.circle(surface, SHADOW, (inner.centerx + 10, inner.centery - 2), 2)


def draw_bomb(surface, bomb, frame, ox=0, oy=0):
    x = int(bomb.px + ox)
    y = int(bomb.py + oy)
    cx = x + TILE // 2
    cy = y + TILE // 2

    draw_shadow(surface, x + 18, y + TILE - 14, TILE - 36, 10)
    glow_color = REMOTE_COLOR if bomb.remote else BOMB_GLOW
    draw_glow_circle(surface, cx, cy, 20, glow_color)

    if assets.bomb:
        surface.blit(assets.bomb, (x, y))
        if bomb.remote:
            draw_text(surface, "R", 16, cx, cy, REMOTE_COLOR, center=True, shadow=False)
        return

    pulse = 1.0 + 0.06 * sin(frame * 0.35 + bomb.cx + bomb.cy)
    radius = int(16 * pulse)
    pygame.draw.circle(surface, BOMB, (cx, cy), radius)
    pygame.draw.circle(surface, BOMB_HL, (cx - 7, cy - 7), 4)

    if bomb.moving_dx != 0 or bomb.moving_dy != 0:
        pygame.draw.circle(surface, CYAN, (cx, cy), radius + 4, 2)


def draw_explosion(surface, exp, frame, ox=0, oy=0):
    for cx, cy, part in exp.tiles:
        px = cx * TILE + ox
        py = cy * TILE + HUD_H + oy
        center = (px + TILE // 2, py + TILE // 2)

        if part == "center":
            pygame.draw.circle(surface, EXP_OUT, center, 20)
            pygame.draw.circle(surface, EXP_MID, center, 14)
            pygame.draw.circle(surface, EXP_CORE, center, 7)
        else:
            if part in ("left", "right"):
                pygame.draw.rect(surface, EXP_OUT, (px + 6, py + 22, TILE - 12, 20), border_radius=10)
                pygame.draw.rect(surface, EXP_MID, (px + 14, py + 25, TILE - 28, 14), border_radius=8)
            else:
                pygame.draw.rect(surface, EXP_OUT, (px + 22, py + 6, 20, TILE - 12), border_radius=10)
                pygame.draw.rect(surface, EXP_MID, (px + 25, py + 14, 14, TILE - 28), border_radius=8)
            pygame.draw.circle(surface, EXP_CORE, center, 6)


def draw_powerup(surface, powerup, frame, ox=0, oy=0):
    px = powerup.cx * TILE + ox
    py = powerup.cy * TILE + HUD_H + oy
    floaty = int(1 * sin(frame * 0.18 + powerup.cx))

    draw_shadow(surface, px + 20, py + TILE - 16, TILE - 40, 10)

    if powerup.kind == POWER_BOMB and assets.power_bomb:
        surface.blit(assets.power_bomb, (px, py + floaty))
        return
    if powerup.kind == POWER_RANGE and assets.power_range:
        surface.blit(assets.power_range, (px, py + floaty))
        return
    if powerup.kind == POWER_SPEED and assets.power_speed:
        surface.blit(assets.power_speed, (px, py + floaty))
        return
    if powerup.kind == POWER_SHIELD and assets.power_shield:
        surface.blit(assets.power_shield, (px, py + floaty))
        return
    if powerup.kind == POWER_REMOTE and assets.power_remote:
        surface.blit(assets.power_remote, (px, py + floaty))
        return
    if powerup.kind == POWER_KICK and assets.power_kick:
        surface.blit(assets.power_kick, (px, py + floaty))
        return

    center = (px + TILE // 2, py + TILE // 2 + floaty)
    if powerup.kind == POWER_BOMB:
        color = BLUE_UP
        label = "B"
    elif powerup.kind == POWER_RANGE:
        color = ORANGE_UP
        label = "F"
    elif powerup.kind == POWER_SPEED:
        color = LIME_UP
        label = "S"
    elif powerup.kind == POWER_SHIELD:
        color = SHIELD_COLOR
        label = "H"
    elif powerup.kind == POWER_REMOTE:
        color = REMOTE_COLOR
        label = "R"
    else:
        color = KICK_COLOR
        label = "K"

    pygame.draw.circle(surface, color, center, 12)
    pygame.draw.circle(surface, WHITE_SAFE, center, 12, 2)
    draw_text(surface, label, 16, center[0], center[1] - 1, SHADOW, center=True, shadow=False)


def draw_hud(surface, state):
    pygame.draw.rect(surface, (10, 14, 24), (0, 0, WIDTH, HUD_H))
    pygame.draw.line(surface, MAGENTA, (0, HUD_H - 2), (WIDTH, HUD_H - 2), 3)

    pygame.draw.rect(surface, (20, 26, 42), (8, 8, WIDTH - 16, HUD_H - 18), border_radius=12)
    pygame.draw.rect(surface, (38, 48, 74), (8, 8, WIDTH - 16, HUD_H - 18), 2, border_radius=12)

    diff_label = {
        DIFFICULTY_EASY: "FACIL",
        DIFFICULTY_NORMAL: "NORMAL",
        DIFFICULTY_HARD: "DIFICIL",
    }[state.difficulty]

    draw_text(surface, "NEO BOMB", 28, 18, 18, CYAN)
    draw_text(surface, f"NIVEL {state.level}", 18, 170, 22, CYAN)
    draw_text(surface, f"VIDAS {state.player.lives}", 18, 270, 22, GREEN)
    draw_text(surface, f"PUNTOS {state.score}", 18, 385, 22, YELLOW)
    draw_text(surface, f"RECORD {state.high_score}", 18, 550, 22, MAGENTA)

    mins = int(state.time_left) // 60
    secs = int(state.time_left) % 60
    timer_color = RED if state.time_left <= 30 else TEXT
    draw_text(surface, f"{mins:02d}:{secs:02d}", 22, WIDTH - 95, 20, timer_color)

    kick_text = " K" if state.player.can_kick else ""
    info = f"B {state.player.max_bombs}  F {state.player.power}  S {int(state.player.speed)}  H {state.player.shield}{kick_text}"
    draw_text(surface, info, 15, 18, HEIGHT - 28, TEXT)

    mode_text = "REMOTA ON" if state.player.remote_mode else "REMOTA OFF"
    mode_color = REMOTE_COLOR if state.player.remote_mode else TEXT
    draw_text(surface, mode_text, 15, WIDTH - 120, HEIGHT - 28, mode_color)

    draw_text(surface, diff_label, 15, WIDTH // 2, 18, CYAN, center=True)

    if state.boss:
        draw_text(surface, "BOSS", 15, WIDTH // 2, HEIGHT - 28, RED, center=True)
    elif state.door:
        door_txt = "SALIDA ABIERTA" if state.door.unlocked else "ELIMINA ENEMIGOS"
        door_color = GREEN if state.door.unlocked else DOOR_COLOR
        draw_text(surface, door_txt, 15, WIDTH // 2, HEIGHT - 28, door_color, center=True)


def draw_boss_bar(surface, state):
    if not state.boss:
        return

    bar_w = 360
    bar_h = 18
    x = (WIDTH - bar_w) // 2
    y = HUD_H + 8

    pygame.draw.rect(surface, SHADOW, (x - 2, y - 2, bar_w + 4, bar_h + 4), border_radius=8)
    pygame.draw.rect(surface, (40, 20, 20), (x, y, bar_w, bar_h), border_radius=8)

    ratio = max(0, state.boss.hp / state.boss.hp_max)
    fill_w = int(bar_w * ratio)
    fill_color = BOSS_MAIN if state.boss.phase == 1 else MAGENTA

    pygame.draw.rect(surface, fill_color, (x, y, fill_w, bar_h), border_radius=8)
    pygame.draw.rect(surface, WHITE_SAFE, (x, y, bar_w, bar_h), 2, border_radius=8)

    label = f"BOSS HP {state.boss.hp}/{state.boss.hp_max}"
    if state.boss.phase == 2:
        label += " | FASE 2"
    draw_text(surface, label, 16, WIDTH // 2, y + bar_h // 2, WHITE_SAFE, center=True)


def draw_overlay(surface, title, subtitle, color):
    shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    shade.fill((0, 0, 0, 160))
    surface.blit(shade, (0, 0))
    draw_text(surface, title, 50, WIDTH // 2, HEIGHT // 2 - 20, color, center=True)
    draw_text(surface, subtitle, 22, WIDTH // 2, HEIGHT // 2 + 30, TEXT, center=True)


def draw_menu(frame, state):
    GAME_SURFACE.fill(BG)

    for star in stars:
        star.update()
        star.draw(GAME_SURFACE)

    title_color = (80, 240, 255 - int(30 * abs(sin(frame * 0.04))))
    draw_text(GAME_SURFACE, "NEO BOMB", 66, WIDTH // 2, 130, title_color, center=True)
    draw_text(GAME_SURFACE, "SOLO 1 JUGADOR - IMPROVED", 22, WIDTH // 2, 185, MAGENTA, center=True)

    draw_text(GAME_SURFACE, "ENTER = COMENZAR", 24, WIDTH // 2, 275, YELLOW, center=True)
    draw_text(GAME_SURFACE, "ESPACIO = BOMBA   |   E = DETONAR REMOTAS", 18, WIDTH // 2, 330, TEXT, center=True)
    draw_text(GAME_SURFACE, "WASD / FLECHAS = MOVER", 18, WIDTH // 2, 362, TEXT, center=True)
    draw_text(GAME_SURFACE, "P = PAUSA   R = REINICIAR   F11 = PANTALLA", 18, WIDTH // 2, 394, TEXT, center=True)
    draw_text(GAME_SURFACE, "NUEVO: POWER KICK + ENEMIGO GHOST + COMBOS", 18, WIDTH // 2, 426, KICK_COLOR, center=True)
    draw_text(GAME_SURFACE, "NIVEL SIGUIENTE AUTOMATICO", 18, WIDTH // 2, 458, GREEN, center=True)

    easy_color = GREEN if state.difficulty == DIFFICULTY_EASY else TEXT
    normal_color = CYAN if state.difficulty == DIFFICULTY_NORMAL else TEXT
    hard_color = RED if state.difficulty == DIFFICULTY_HARD else TEXT

    draw_text(GAME_SURFACE, "1 = FACIL", 20, WIDTH // 2 - 160, 510, easy_color, center=True)
    draw_text(GAME_SURFACE, "2 = NORMAL", 20, WIDTH // 2, 510, normal_color, center=True)
    draw_text(GAME_SURFACE, "3 = DIFICIL", 20, WIDTH // 2 + 160, 510, hard_color, center=True)

    draw_text(GAME_SURFACE, f"RECORD: {state.high_score}", 18, WIDTH // 2, 555, YELLOW, center=True)
    draw_text(GAME_SURFACE, f"MEJOR NIVEL: {state.best_level}", 18, WIDTH // 2, 583, GREEN, center=True)

    draw_scaled_to_screen(GAME_SURFACE)


def render_game(state):
    ox = random.randint(-2, 2) if state.camera_shake > 0 else 0
    oy = random.randint(-2, 2) if state.camera_shake > 0 else 0

    GAME_SURFACE.fill(BG)
    draw_floor(GAME_SURFACE, state.menu_frame, ox, oy)

    if state.door:
        draw_door(GAME_SURFACE, state.door, state.menu_frame, ox, oy)

    for y in range(ROWS):
        for x in range(COLS):
            if state.grid[y][x] == 1:
                draw_wall(GAME_SURFACE, x, y, ox, oy)
            elif state.grid[y][x] == 2:
                draw_block(GAME_SURFACE, x, y, ox, oy)

    for powerup in state.powerups:
        draw_powerup(GAME_SURFACE, powerup, state.menu_frame, ox, oy)

    for bomb in state.bombs:
        draw_bomb(GAME_SURFACE, bomb, state.menu_frame, ox, oy)

    for exp in state.explosions:
        draw_explosion(GAME_SURFACE, exp, state.menu_frame, ox, oy)

    for enemy in state.enemies:
        draw_enemy(GAME_SURFACE, enemy, state.menu_frame, ox, oy)

    if state.boss:
        draw_boss(GAME_SURFACE, state.boss, state.menu_frame, ox, oy)
        if state.boss.phase_message_timer > 0:
            draw_text(GAME_SURFACE, "BOSS FASE 2", 34, WIDTH // 2, HEIGHT // 2 + 20, RED, center=True)

    if not (state.player.invuln > 0 and (state.player.invuln // 6) % 2 == 0):
        draw_player(GAME_SURFACE, state.player, state.menu_frame, ox, oy)

    for p in state.particles:
        p.draw(GAME_SURFACE, ox, oy)

    for ft in state.floating_texts:
        ft.draw(GAME_SURFACE, ox, oy)

    draw_hud(GAME_SURFACE, state)
    draw_boss_bar(GAME_SURFACE, state)

    if state.level_message_timer > 0 and state.state == STATE_PLAYING:
        msg = f"BOSS NIVEL {state.level}" if state.is_boss_level() else f"NIVEL {state.level}"
        color = RED if state.is_boss_level() else CYAN
        draw_text(GAME_SURFACE, msg, 36, WIDTH // 2, HEIGHT // 2 - 20, color, center=True)

    if state.flash > 0:
        flash = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        flash.fill((255, 255, 255, 45))
        GAME_SURFACE.blit(flash, (0, 0))

    if state.state == STATE_PAUSED:
        draw_overlay(GAME_SURFACE, "PAUSA", "Presiona P para continuar", YELLOW)
    elif state.state == STATE_GAME_OVER:
        draw_overlay(GAME_SURFACE, "GAME OVER", "R para reiniciar | ENTER para menu", RED)
    elif state.state == STATE_LEVEL_CLEAR:
        draw_overlay(GAME_SURFACE, "LEVEL CLEAR", "Cargando siguiente nivel...", GREEN)

    draw_scaled_to_screen(GAME_SURFACE)


# =========================
# MAIN
# =========================
def main():
    global is_fullscreen
    state = GameState()

    while True:
        dt = clock.tick(FPS) / 1000.0
        state.menu_frame += 1

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                save_progress(state.high_score, state.best_level)
                pygame.quit()
                sys.exit()

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    save_progress(state.high_score, state.best_level)
                    pygame.quit()
                    sys.exit()

                if event.key == pygame.K_F11:
                    is_fullscreen = not is_fullscreen
                    recreate_screen()

                if state.state == STATE_MENU:
                    if event.key == pygame.K_1:
                        state.difficulty = DIFFICULTY_EASY
                    elif event.key == pygame.K_2:
                        state.difficulty = DIFFICULTY_NORMAL
                    elif event.key == pygame.K_3:
                        state.difficulty = DIFFICULTY_HARD
                    elif event.key == pygame.K_RETURN:
                        state.restart_round()

                elif state.state == STATE_PLAYING:
                    if event.key == pygame.K_SPACE:
                        place_bomb(state)
                    elif event.key == pygame.K_e:
                        detonate_remote_bombs(state)
                    elif event.key == pygame.K_p:
                        state.state = STATE_PAUSED
                    elif event.key == pygame.K_r:
                        state.restart_round()

                elif state.state == STATE_PAUSED:
                    if event.key == pygame.K_p:
                        state.state = STATE_PLAYING
                    elif event.key == pygame.K_r:
                        state.restart_round()

                elif state.state == STATE_GAME_OVER:
                    if event.key == pygame.K_r:
                        state.level = 1
                        state.score = 0
                        state.player = Player(1, 1)
                        state.restart_round()
                    elif event.key == pygame.K_RETURN:
                        state.full_reset()

        update_game(state, dt)

        if state.state == STATE_MENU:
            draw_menu(state.menu_frame, state)
        else:
            render_game(state)


if __name__ == "__main__":
    main()