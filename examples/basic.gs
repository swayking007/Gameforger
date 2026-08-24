# basic.gs — A valid GameScript program
# This is the canonical test case for the GameForge compiler.

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
