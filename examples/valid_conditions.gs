# valid_conditions.gs — Tests various relational operators

PLAYER health = 100
PLAYER coins = 0

WHEN enemy_attack
    health -= 20

WHEN collect_coin
    coins += 10

IF health <= 0
    GAME_OVER

IF coins >= 10
    LEVEL_COMPLETE
