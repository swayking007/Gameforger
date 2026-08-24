# lexical_error.gs — Contains an invalid character '@'
# Expected: Lexical Error on line 4

PLAYER health = 100

WHEN enemy_attack
    health @= 20
