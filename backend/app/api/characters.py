import json
import random
import secrets
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from fastapi import Depends, HTTPException
from fastapi import Body
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.db.database import Character, CharacterItem, Campaign, CampaignMember, User, get_db

router = APIRouter()

STANDARD_ARRAY = [15, 14, 13, 12, 10, 8]
MAX_STAT_ROLLS = 3

DND5E_DATA = {
    "races": {
        "human": {"speed": 30, "size": "medium", "ability_bonuses": {"str": 1, "dex": 1, "con": 1, "int": 1, "wis": 1, "cha": 1}},
        "elf": {"speed": 30, "size": "medium", "ability_bonuses": {"dex": 2, "int": 1}},
        "dwarf": {"speed": 25, "size": "medium", "ability_bonuses": {"con": 2, "wis": 1}},
        "halfling": {"speed": 25, "size": "small", "ability_bonuses": {"dex": 2, "cha": 1}},
        "gnome": {"speed": 25, "size": "small", "ability_bonuses": {"int": 2, "dex": 1}},
        "dragonborn": {"speed": 30, "size": "medium", "ability_bonuses": {"str": 2, "cha": 1}},
        "half-orc": {"speed": 30, "size": "medium", "ability_bonuses": {"str": 2, "con": 1}},
        "tiefling": {"speed": 30, "size": "medium", "ability_bonuses": {"cha": 2, "int": 1}},
    },
    "classes": {
        "fighter": {"hit_die": "d10", "hit_die_count": 1, "primary_ability": ["str", "dex"], "saving_throws": ["str", "con"], "armor": ["light", "medium", "heavy"], "weapons": ["simple", "martial"], "skills": {"choose": 2, "from": ["acrobatics", "athletics", "history", "insight", "intimidation", "perception"]}},
        "rogue": {"hit_die": "d8", "hit_die_count": 1, "primary_ability": ["dex"], "saving_throws": ["dex", "int"], "armor": ["light"], "weapons": ["simple", "hand_crossbow", "longsword"], "skills": {"choose": 4, "from": ["acrobatics", "athletics", "deception", "insight", "intimidation", "investigation", "perception", "performance", "persuasion", "sleight_of_hand", "stealth"]}},
        "wizard": {"hit_die": "d6", "hit_die_count": 1, "primary_ability": ["int"], "saving_throws": ["int", "wis"], "armor": [], "weapons": ["dagger", "quarterstaff"], "skills": {"choose": 2, "from": ["arcana", "history", "insight", "investigation", "medicine", "religion"]}},
        "cleric": {"hit_die": "d8", "hit_die_count": 1, "primary_ability": ["wis"], "saving_throws": ["wis", "cha"], "armor": ["light", "medium", "shield"], "weapons": ["simple"], "skills": {"choose": 2, "from": ["history", "insight", "medicine", "persuasion", "religion"]}},
        "paladin": {"hit_die": "d10", "hit_die_count": 1, "primary_ability": ["str", "cha"], "saving_throws": ["wis", "cha"], "armor": ["light", "medium", "heavy", "shield"], "weapons": ["simple", "martial"], "skills": {"choose": 2, "from": ["athletics", "insight", "intimidation", "medicine", "persuasion", "religion"]}},
        "ranger": {"hit_die": "d10", "hit_die_count": 1, "primary_ability": ["dex", "wis"], "saving_throws": ["dex", "wis"], "armor": ["light", "medium", "shield"], "weapons": ["simple", "martial"], "skills": {"choose": 3, "from": ["animal_handling", "athletics", "insight", "investigation", "perception", "stealth", "survival"]}},
        "barbarian": {"hit_die": "d12", "hit_die_count": 1, "primary_ability": ["str"], "saving_throws": ["str", "con"], "armor": ["light", "medium"], "weapons": ["simple", "martial"], "skills": {"choose": 2, "from": ["animal_handling", "athletics", "intimidation", "nature", "perception", "survival"]}},
        "bard": {"hit_die": "d8", "hit_die_count": 1, "primary_ability": ["cha", "dex"], "saving_throws": ["dex", "cha"], "armor": ["light"], "weapons": ["simple", "hand_crossbow", "longsword"], "skills": {"choose": 3, "from": ["acrobatics", "animal_handling", "arcana", "athletics", "deception", "history", "insight", "intimidation", "investigation", "medicine", "nature", "perception", "performance", "persuasion", "religion", "sleight_of_hand", "stealth", "survival"]}},
        "druid": {"hit_die": "d8", "hit_die_count": 1, "primary_ability": ["wis"], "saving_throws": ["int", "wis"], "armor": ["light", "medium", "shield"], "weapons": ["club", "dagger", "quarterstaff", "scimitar", "sling"], "skills": {"choose": 2, "from": ["arcana", "animal_handling", "insight", "medicine", "nature", "perception", "religion", "survival"]}},
        "monk": {"hit_die": "d8", "hit_die_count": 1, "primary_ability": ["dex", "wis"], "saving_throws": ["str", "dex"], "armor": [], "weapons": ["simple", "shortsword"], "skills": {"choose": 2, "from": ["acrobatics", "athletics", "history", "insight", "religion", "stealth"]}},
        "warlock": {"hit_die": "d8", "hit_die_count": 1, "primary_ability": ["cha"], "saving_throws": ["wis", "cha"], "armor": ["light"], "weapons": ["simple"], "skills": {"choose": 2, "from": ["arcana", "deception", "history", "intimidation", "investigation", "nature", "persuasion"]}},
        "sorcerer": {"hit_die": "d6", "hit_die_count": 1, "primary_ability": ["cha"], "saving_throws": ["con", "cha"], "armor": [], "weapons": ["dagger", "quarterstaff"], "skills": {"choose": 2, "from": ["arcana", "deception", "insight", "intimidation", "persuasion", "religion"]}},
    },
    "backgrounds": {
        "acolyte": {"skill_proficiencies": ["insight", "religion"], "equipment": ["holy symbol", "prayer book"], "languages": 2, "gold": 5},
        "folk_hero": {"skill_proficiencies": ["animal_handling", "survival"], "equipment": ["thieves' tools", "pot"], "languages": 0, "gold": 10},
        "criminal": {"skill_proficiencies": ["deception", "stealth"], "equipment": ["thieves' tools", "playing card"], "languages": 0, "gold": 15},
        "sage": {"skill_proficiencies": ["arcana", "history"], "equipment": ["books", "ink"], "languages": 2, "gold": 10},
        "soldier": {"skill_proficiencies": ["athletics", "intimidation"], "equipment": ["military insignia", "trophy"], "languages": 0, "gold": 10},
        "outlander": {"skill_proficiencies": ["athletics", "survival"], "equipment": ["staff", "hunting trap"], "languages": 1, "gold": 10},
        "noble": {"skill_proficiencies": ["history", "persuasion"], "equipment": ["fine clothes", "signet ring"], "languages": 1, "gold": 25},
        "entrant": {"skill_proficiencies": ["performance", "persuasion"], "equipment": ["musical instrument"], "languages": 0, "gold": 10},
    }
}

STARTING_EQUIPMENT = {
    "fighter": {"weapons": ["longsword", "shield", "chainmail"], "gear": ["bedroll", "rations x10"]},
    "rogue": {"weapons": ["shortbow", "arrows x20", "rapier"], "gear": ["thieves' tools", "bedroll"]},
    "wizard": {"weapons": ["quarterstaff"], "gear": ["spellbook", "ink", "bedroll"]},
    "cleric": {"weapons": ["mace", "chainmail", "shield"], "gear": ["holy symbol", "bedroll"]},
    "paladin": {"weapons": ["longsword", "chainmail", "shield"], "gear": ["holy symbol", "bedroll"]},
    "ranger": {"weapons": ["shortbow", "arrows x20"], "gear": ["bedroll"]},
    "barbarian": {"weapons": ["greataxe"], "gear": ["bedroll"]},
    "bard": {"weapons": ["shortbow", "rapier"], "gear": ["musical instrument", "bedroll"]},
    "druid": {"weapons": ["quarterstaff"], "gear": ["component pouch", "bedroll"]},
    "monk": {"weapons": ["quarterstaff"], "gear": ["bedroll"]},
    "warlock": {"weapons": ["quarterstaff"], "gear": ["spellbook", "bedroll"]},
    "sorcerer": {"weapons": ["dagger x2"], "gear": ["component pouch", "bedroll"]},
}


class CharacterCreate(BaseModel):
    campaign_id: int
    name: str
    race: str
    class_name: str
    subclass: Optional[str] = None
    background: Optional[str] = None
    stats: Optional[dict] = None
    personality: Optional[str] = None
    backstory: Optional[str] = None


class CharacterUpdate(BaseModel):
    name: Optional[str] = None
    level: Optional[int] = None
    hp: Optional[int] = None
    max_hp: Optional[int] = None
    ac: Optional[int] = None
    stats: Optional[dict] = None
    equipment: Optional[list] = None
    inventory: Optional[list] = None
    personality: Optional[str] = None
    backstory: Optional[str] = None


class CharacterWithRollsCreate(BaseModel):
    campaign_id: int
    name: str
    race: str
    class_name: str
    subclass: Optional[str] = None
    background: Optional[str] = "acolyte"
    stat_rolls: Optional[List[int]] = None
    use_standard_array: bool = False
    personality: Optional[str] = None
    backstory: Optional[str] = None


class CharacterResponse(BaseModel):
    id: int
    user_id: int
    campaign_id: int
    name: str
    race: str
    class_name: str
    subclass: Optional[str]
    background: Optional[str]
    level: int
    stats: dict
    hp: Optional[int]
    max_hp: Optional[int]
    ac: Optional[int]
    speed: Optional[int]
    proficiency_bonus: int
    equipment: list
    inventory: list
    stat_rolls: list
    stat_roll_count: int

    class Config:
        from_attributes = True


def roll_stats_4d6_drop_lowest():
    rolls = [random.randint(1, 6) for _ in range(4)]
    rolls.remove(min(rolls))
    return sum(rolls)


def calculate_modifier(stat):
    return (stat - 10) // 2


def calculate_ac(stats, armor_bonus=0, has_shield=False):
    dex_mod = calculate_modifier(stats.get("dex", 10))
    ac = 10 + dex_mod + armor_bonus
    if has_shield:
        ac += 2
    return ac


@router.post("/roll-stats", response_model=dict)
async def roll_character_stats(
    use_standard_array: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if use_standard_array:
        return {"rolls": STANDARD_ARRAY, "method": "standard_array"}
    
    rolls = [roll_stats_4d6_drop_lowest() for _ in range(6)]
    return {"rolls": sorted(rolls, reverse=True), "method": "rolled"}


@router.post("/create-with-rolls", response_model=CharacterResponse)
async def create_character_with_rolls(
    character_data: CharacterWithRollsCreate = Body(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    campaign_id = character_data.campaign_id
    name = character_data.name
    race = character_data.race
    class_name = character_data.class_name
    subclass = character_data.subclass
    background = character_data.background
    stat_rolls = character_data.stat_rolls
    use_standard_array = character_data.use_standard_array
    personality = character_data.personality
    backstory = character_data.backstory
    
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    member = await db.execute(
        select(CampaignMember).where(
            CampaignMember.campaign_id == campaign_id,
            CampaignMember.user_id == current_user.id
)
    )
    if not member.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not a campaign member")
    
    if race not in DND5E_DATA["races"]:
        raise HTTPException(status_code=400, detail="Invalid race. Choose: " + ", ".join(DND5E_DATA["races"].keys()))
    if class_name not in DND5E_DATA["classes"]:
        raise HTTPException(status_code=400, detail="Invalid class. Choose: " + ", ".join(DND5E_DATA["classes"].keys()))
    if background not in DND5E_DATA["backgrounds"]:
        background = "acolyte"
    
    race_data = DND5E_DATA["races"][race]
    class_data = DND5E_DATA["classes"][class_name]
    bg_data = DND5E_DATA["backgrounds"][background]
    
    if stat_rolls:
        if len(stat_rolls) != 6:
            raise HTTPException(status_code=400, detail="Need exactly 6 stat values")
        stats = {"str": stat_rolls[0], "dex": stat_rolls[1], "con": stat_rolls[2], 
                "int": stat_rolls[3], "wis": stat_rolls[4], "cha": stat_rolls[5]}
    elif use_standard_array:
        stats = {"str": STANDARD_ARRAY[0], "dex": STANDARD_ARRAY[1], "con": STANDARD_ARRAY[2],
                "int": STANDARD_ARRAY[3], "wis": STANDARD_ARRAY[4], "cha": STANDARD_ARRAY[5]}
    else:
        rolls = [roll_stats_4d6_drop_lowest() for _ in range(6)]
        rolls.sort(reverse=True)
        stats = {"str": rolls[0], "dex": rolls[1], "con": rolls[2],
                "int": rolls[3], "wis": rolls[4], "cha": rolls[5]}
    
    for stat, bonus in race_data.get("ability_bonuses", {}).items():
        stats[stat] = stats.get(stat, 10) + bonus
    
    con_mod = calculate_modifier(stats.get("con", 10))
    hit_die = int(class_data["hit_die"][1:])
    max_hp = hit_die + con_mod
    
    armor_bonus = 0
    has_shield = False
    if class_data.get("armor"):
        armor_bonus = 2
        if "medium" in class_data["armor"]:
            armor_bonus = 4
        if "heavy" in class_data["armor"]:
            armor_bonus = 6
    
    base_ac = calculate_ac(stats, armor_bonus, has_shield)
    
    equipment = []
    gear_list = []
    starting = STARTING_EQUIPMENT.get(class_name.lower(), {})
    for w in starting.get("weapons", []):
        equipment.append({"name": w, "type": "weapon", "equipped": True})
    for g in starting.get("gear", []):
        equipment.append({"name": g, "type": "gear", "equipped": False})
    bg_eq = bg_data.get("equipment", [])
    for eq in bg_eq:
        equipment.append({"name": eq, "type": "gear", "equipped": False})
    
    db_character = Character(
        user_id=current_user.id,
        campaign_id=campaign_id,
        name=name,
        race=race,
        class_name=class_name,
        subclass=subclass,
        background=background,
        level=1,
        stats=stats,
        hp=max_hp,
        max_hp=max_hp,
        ac=base_ac,
        speed=race_data.get("speed", 30),
        proficiency_bonus=2,
        saving_throws=class_data.get("saving_throws", []),
        skills={"choose": class_data.get("skills", {}).get("choose", 0)},
        equipment=equipment,
        inventory=[],
        stat_rolls=stat_rolls if stat_rolls else [roll_stats_4d6_drop_lowest() for _ in range(6)],
        stat_roll_count=1 if not use_standard_array and not rolled_stats else 0,
        personality=personality,
        backstory=backstory
    )
    db.add(db_character)
    await db.commit()
    await db.refresh(db_character)
    return db_character


@router.post("/", response_model=CharacterResponse)
async def create_character(
    character: CharacterCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Campaign).where(Campaign.id == character.campaign_id))
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    member = await db.execute(
        select(CampaignMember).where(
            CampaignMember.campaign_id == character.campaign_id,
            CampaignMember.user_id == current_user.id
        )
    )
    if not member.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not a campaign member")

    if character.race not in DND5E_DATA["races"]:
        raise HTTPException(status_code=400, detail="Invalid race")
    if character.class_name not in DND5E_DATA["classes"]:
        raise HTTPException(status_code=400, detail="Invalid class")

    race_data = DND5E_DATA["races"][character.race]
    class_data = DND5E_DATA["classes"][character.class_name]

    stats = character.stats if character.stats else {}
    if not stats:
        stats = {stat: STANDARD_ARRAY[i] + race_data.get("ability_bonuses", {}).get(stat, 0) 
                for i, stat in enumerate(["str", "dex", "con", "int", "wis", "cha"])}

    base_hp = int(class_data["hit_die"][1:])
    con_mod = (stats.get("con", 10) - 10) // 2
    max_hp = base_hp + con_mod

    db_character = Character(
        user_id=current_user.id,
        campaign_id=character.campaign_id,
        name=character.name,
        race=character.race,
        class_name=character.class_name,
        subclass=character.subclass,
        background=character.background,
        level=1,
        stats=stats,
        hp=max_hp,
        max_hp=max_hp,
        ac=10 + (stats.get("dex", 10) - 10) // 2,
        speed=race_data.get("speed", 30),
        proficiency_bonus=2,
        equipment=[],
        inventory=[],
        stat_roll_count=0,
        personality=character.personality,
        backstory=character.backstory
    )
    db.add(db_character)
    await db.commit()
    await db.refresh(db_character)
    return db_character


@router.get("/", response_model=List[CharacterResponse])
async def list_characters(
    campaign_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(Character).where(Character.user_id == current_user.id)
    if campaign_id:
        query = query.where(Character.campaign_id == campaign_id)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{character_id}", response_model=CharacterResponse)
async def get_character(
    character_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Character).where(
            Character.id == character_id,
            Character.user_id == current_user.id
        )
    )
    character = result.scalar_one_or_none()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    return character


@router.patch("/{character_id}", response_model=CharacterResponse)
async def update_character(
    character_id: int,
    character_update: CharacterUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Character).where(
            Character.id == character_id,
            Character.user_id == current_user.id
        )
    )
    character = result.scalar_one_or_none()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    for field, value in character_update.model_dump(exclude_unset=True).items():
        setattr(character, field, value)

    await db.commit()
    await db.refresh(character)
    return character


@router.get("/campaign/{campaign_id}", response_model=List[CharacterResponse])
async def list_campaign_characters(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    member = await db.execute(
        select(CampaignMember).where(
            CampaignMember.campaign_id == campaign_id,
            CampaignMember.user_id == current_user.id
        )
    )
    if not member.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not a campaign member")

    result = await db.execute(
        select(Character).where(Character.campaign_id == campaign_id)
    )
    return result.scalars().all()


class ItemCreate(BaseModel):
    name: str
    description: Optional[str] = None
    quantity: int = 1
    weight: float = 0.0
    item_type: str = "misc"
    rarity: str = "common"
    equipped: bool = False
    damage: Optional[str] = None
    armor_class: Optional[int] = None
    damage_type: Optional[str] = None
    range_value: Optional[str] = None
    magical: bool = False
    cost: int = 0


@router.post("/{character_id}/inventory")
async def add_inventory_item(
    character_id: int,
    item: ItemCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Character).where(Character.id == character_id, Character.user_id == current_user.id)
    )
    character = result.scalar_one_or_none()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    
    new_item = CharacterItem(
        character_id=character_id,
        name=item.name,
        description=item.description,
        quantity=item.quantity,
        weight=item.weight,
        item_type=item.item_type,
        rarity=item.rarity,
        equipped=item.equipped,
        damage=item.damage,
        armor_class=item.armor_class,
        damage_type=item.damage_type,
        range_value=item.range_value,
        magical=item.magical,
        cost=item.cost
    )
    db.add(new_item)
    await db.commit()
    await db.refresh(new_item)
    
    character.inventory = character.inventory or []
    character.inventory.append({
        "item_id": new_item.id,
        "name": item.name,
        "quantity": item.quantity,
        "equipped": item.equipped
    })
    await db.commit()
    
    return new_item


@router.get("/{character_id}/inventory")
async def get_inventory(
    character_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Character).where(Character.id == character_id, Character.user_id == current_user.id)
    )
    character = result.scalar_one_or_none()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    
    items = await db.execute(
        select(CharacterItem).where(CharacterItem.character_id == character_id)
    )
    return items.scalars().all()


@router.patch("/{character_id}/inventory/{item_id}")
async def update_inventory_item(
    character_id: int,
    item_id: int,
    quantity: Optional[int] = None,
    equipped: Optional[bool] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    char_result = await db.execute(
        select(Character).where(Character.id == character_id, Character.user_id == current_user.id)
    )
    if not char_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Character not found")
    
    item = await db.execute(
        select(CharacterItem).where(CharacterItem.id == item_id, CharacterItem.character_id == character_id)
    )
    item = item.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    if quantity is not None:
        item.quantity = quantity
    if equipped is not None:
        item.equipped = equipped
        if equipped:
            char = await db.execute(select(Character).where(Character.id == character_id))
            char = char.scalar_one_or_none()
            if item.item_type == "armor" and item.armor_class:
                char.ac = item.armor_class
                await db.commit()
    
    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/{character_id}/inventory/{item_id}")
async def delete_inventory_item(
    character_id: int,
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    char_result = await db.execute(
        select(Character).where(Character.id == character_id, Character.user_id == current_user.id)
    )
    if not char_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Character not found")
    
    item = await db.execute(
        select(CharacterItem).where(CharacterItem.id == item_id, CharacterItem.character_id == character_id)
    )
    item = item.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    await db.delete(item)
    await db.commit()
    return {"message": "Item deleted"}