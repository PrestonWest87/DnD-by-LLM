# D&D 5e Skills - Complete List

SKILLS = {
    # Strength Skills
    "athletics": {
        "name": "Athletics",
        "ability": "str",
        "description": "Climbing, jumping, and swimming.",
        "trained_only": False
    },
    
    # Dexterity Skills
    "acrobatics": {
        "name": "Acrobatics",
        "ability": "dex",
        "description": "Performing acrobatic maneuvers.",
        "trained_only": False
    },
    "sleight_of_hand": {
        "name": "Sleight of Hand",
        "ability": "dex",
        "description": "Pickpocketing and delicate tasks.",
        "trained_only": True
    },
    "stealth": {
        "name": "Stealth",
        "ability": "dex",
        "description": "Hiding and moving silently.",
        "trained_only": False
    },
    
    # Intelligence Skills
    "arcana": {
        "name": "Arcana",
        "ability": "int",
        "description": "Knowledge of magical lore.",
        "trained_only": True
    },
    "history": {
        "name": "History",
        "ability": "int",
        "description": "Knowledge of historical events.",
        "trained_only": True
    },
    "investigation": {
        "name": "Investigation",
        "ability": "int",
        "description": "Finding hidden objects or info.",
        "trained_only": False
    },
    "nature": {
        "name": "Nature",
        "ability": "int",
        "description": "Knowledge of flora, fauna, weather.",
        "trained_only": True
    },
    "religion": {
        "name": "Religion",
        "ability": "int",
        "description": "Knowledge of gods, rites, myths.",
        "trained_only": True
    },
    
    # Wisdom Skills
    "animal_handling": {
        "name": "Animal Handling",
        "ability": "wis",
        "description": "Calming or controlling animals.",
        "trained_only": True
    },
    "insight": {
        "name": "Insight",
        "ability": "wis",
        "description": "Reading intentions and motives.",
        "trained_only": False
    },
    "medicine": {
        "name": "Medicine",
        "ability": "wis",
        "description": "Healing wounds and diseases.",
        "trained_only": True
    },
    "perception": {
        "name": "Perception",
        "ability": "wis",
        "description": "Noticing things using senses.",
        "trained_only": False
    },
    "survival": {
        "name": "Survival",
        "ability": "wis",
        "description": "Tracking, foraging, navigation.",
        "trained_only": True
    },
    
    # Charisma Skills
    "deception": {
        "name": "Deception",
        "ability": "cha",
        "description": "Lying convincingly.",
        "trained_only": False
    },
    "intimidation": {
        "name": "Intimidation",
        "ability": "cha",
        "description": "Influencing through threats.",
        "trained_only": False
    },
    "performance": {
        "name": "Performance",
        "ability": "cha",
        "description": "Entertaining through art.",
        "trained_only": False
    },
    "persuasion": {
        "name": "Persuasion",
        "ability": "cha",
        "description": "Influencing through reason.",
        "trained_only": False
    }
}

# Map skills to their governing abilities
SKILL_ABILITIES = {
    skill_id: skill_data["ability"]
    for skill_id, skill_data in SKILLS.items()
}

# Default skill list for character creation
DEFAULT_SKILLS = [
    "athletics", "acrobatics", "arcana", "history", "investigation",
    "nature", "religion", "animal_handling", "insight", "medicine",
    "perception", "survival", "deception", "intimidation", "performance",
    "persuasion", "sleight_of_hand", "stealth"
]


# Calculate passive perception
def get_passive_check(stat_bonus: int, proficiency_bonus: int = 0, 
                      has_proficiency: bool = False) -> int:
    """Calculate passive ability check."""
    base = 10 + stat_bonus
    if has_proficiency:
        base += proficiency_bonus
    return base