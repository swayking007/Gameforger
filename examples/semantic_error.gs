# semantic_error.gs — Uses an undeclared variable 'gems'
# Expected: Semantic Error — Unknown variable 'gems'

PLAYER health = 100

WHEN enemy_attack
    gems -= 20
