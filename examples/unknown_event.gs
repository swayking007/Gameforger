# unknown_event.gs — Uses a misspelled event name
# Expected: Semantic Error — Unknown event 'enemy_attak'

PLAYER health = 100

WHEN enemy_attak
    health -= 20
