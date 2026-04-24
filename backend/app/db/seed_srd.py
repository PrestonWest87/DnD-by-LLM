import os
import re
import json
from pathlib import Path


def load_srd_from_directory(srd_dir: str) -> list:
    """Load SRD content from markdown files."""
    srd_path = Path(srd_dir)
    rules = []

    if not srd_path.exists():
        print(f"SRD directory not found: {srd_dir}")
        return rules

    category_map = {
        'classes.md': 'class',
        'spells.md': 'spell',
        'monsters.md': 'monster',
        'equipment.md': 'equipment',
        'backgrounds.md': 'background',
        'feats.md': 'feat',
        'character-origins.md': 'species',
    }

    for md_file in srd_path.glob('*.md'):
        category = category_map.get(md_file.name, 'general')

        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()

        sections = re.split(r'^## ', content, flags=re.MULTILINE)

        for section in sections[1:]:
            lines = section.split('\n', 1)
            if not lines:
                continue

            title = lines[0].strip()
            body = lines[1].strip() if len(lines) > 1 else ""

            rules.append({
                'category': category,
                'title': title,
                'content': body[:5000]
            })

    return rules


def generate_rules_prompt() -> list:
    """Generate basic D&D 5e SRD rules from knowledge."""
    rules = [
        {
            'category': 'general',
            'title': 'Ability Scores',
            'content': '''Six ability scores (Strength, Dexterity, Constitution, Intelligence, Wisdom, Charisma) represent a character's basic attributes. The ability modifier is calculated as (score - 10) // 2. Ability checks, saving throws, and attack rolls add this modifier.'''
        },
        {
            'category': 'general',
            'title': 'Rolling Ability Checks',
            'content': '''To make an ability check, roll a d20 and add the relevant ability modifier and any proficiency bonus. Compare the total to the DC (Difficulty Class). If the total equals or exceeds the DC, the check succeeds.'''
        },
        {
            'category': 'general',
            'title': 'Advantage and Disadvantage',
            'content': '''When you have advantage, roll two d20s and use the higher result. With disadvantage, use the lower result. You cannot combine multiple advantages or disadvantages.'''
        },
        {
            'category': 'general',
            'title': 'Attack Rolls',
            'content': '''To make a ranged or melee attack, roll d20 + ability modifier + proficiency bonus (if proficient with the weapon). If the result meets or exceeds the target's AC, the attack hits.'''
        },
        {
            'category': 'general',
            'title': 'Damage Rolls',
            'content': '''When an attack hits, roll the weapon's damage die (or dice) and add the ability modifier. This total is the damage dealt. Critical hits double the number of dice rolled.'''
        },
        {
            'category': 'general',
            'title': 'Hit Points',
            'content': '''Hit points represent a creature's stamina and will to fight. When a creature takes damage, subtract the damage from its current hit points. When hit points reach 0, the creature falls unconscious.'''
        },
        {
            'category': 'general',
            'title': 'Death Saving Throws',
            'content': '''When at 0 HP, you must make death saving throws. Roll d20 with no modifiers. 10+ is a success, 9- is a failure. Three successes stabilize, three failures mean death.'''
        },
        {
            'category': 'general',
            'title': 'Short Rest',
            'content': '''A short rest is at least 1 hour of downtime. During a short rest, characters can spend Hit Dice to recover HP and can possibly recover some abilities.'''
        },
        {
            'category': 'general',
            'title': 'Long Rest',
            'content': '''A long rest is at least 8 hours of sleep with 6 hours of restful activity. At the end, characters recover all HP, half their total Hit Dice, and spell slots.'''
        },
        {
            'category': 'general',
            'title': 'Concentration',
            'content': '''Some spells require concentration. If you lose concentration (such as by taking damage or being incapacitated), the spell ends. You can only concentrate on one spell at a time.'''
        },
        {
            'category': 'general',
            'title': 'Spellcasting',
            'content': '''To cast a spell, you must have a spell slot of the appropriate level. You expend the slot when you cast, and the spell has effect. Some spells can be cast as rituals to take 10 minutes longer without expending a slot.'''
        },
        {
            'category': 'general',
            'title': 'Armor Class',
            'content': '''AC represents how difficult it is to hit a creature. Unarmored AC is 10 + Dex modifier. With armor, use the armor's base AC + Dex modifier (if applicable). Shields add +2.'''
        },
        {
            'category': 'general',
            'title': 'Initiative',
            'content': '''At the start of combat, everyone rolls initiative by making a Dexterity check. The DM rolls once for groups of identical creatures. Turns happen in order from highest to lowest initiative.'''
        },
        {
            'category': 'general',
            'title': 'Movement',
            'content': '''Each creature has a speed in feet. Movement can be divided between walking, climbing, swimming, etc. You can move up to your speed in a turn. You can use the Dash action to double your speed or Disengage to avoid opportunity attacks.'''
        },
        {
            'category': 'general',
            'title': 'Opportunity Attacks',
            'content': '''When a creature moves out of your melee reach, you can use your reaction to make one attack against that creature. Moving through a hostile creature's space provokes opportunity attacks.'''
        },
    ]

    classes_data = [
        {
            'category': 'class',
            'title': 'Fighter',
            'content': '''Fighters are skilled martial combatants. They have d10 Hit Dice, Proficiency with all armor and weapons, and save throws using Strength and Constitution. Fighters get Extra Attack at 5th level and Action Surge at 2nd level.'''
        },
        {
            'category': 'class',
            'title': 'Wizard',
            'content': '''Wizards are arcane spellcasters who memorize spells in spellbooks. They have d6 Hit Dice, proficiency with light armor (for casting), and save throws using Intelligence and Wisdom. Wizards prepare spells from their spellbook each day.'''
        },
        {
            'category': 'class',
            'title': 'Cleric',
            'content': '''Clerics are divine spellcasters with the ability to cast all spells in the cleric spell list. They have d8 Hit Dice and proficiency with all armor and shields. Wisdom is their primary ability.'''
        },
        {
            'category': 'class',
            'title': 'Rogue',
            'content': '''Rogues are stealthy tricksters. They have d8 Hit Dice and proficiency with light armor, simple weapons, hand crossbows, and longswords. Rogues get Sneak Attack and Thieves' Cant.'''
        },
        {
            'category': 'class',
            'title': 'Bard',
            'content': '''Bards are versatile performers with magical abilities. They have d8 Hit Dice and can cast any spell from the bard spell list through their magical secrets. Charisma is their primary ability.'''
        },
    ]

    return rules + classes_data


async def seed_srd_rules(db_session):
    """Seed the database with SRD rules."""
    from app.db.database import SRDRule

    existing = await db_session.execute(select(SRDRule).limit(1))
    if existing.scalar_one_or_none():
        print("SRD rules already seeded")
        return

    rules = generate_rules_prompt()

    for rule_data in rules:
        rule = SRDRule(**rule_data)
        db_session.add(rule)

    await db_session.commit()
    print(f"Seeded {len(rules)} SRD rules")
