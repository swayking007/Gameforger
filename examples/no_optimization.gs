# no_optimization.gs — A program where no optimizations apply
# Expected: optimizer reports "No optimizations applicable"

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
