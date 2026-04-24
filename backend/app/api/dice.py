import random
import re
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.auth import get_current_user
from app.db.database import User

router = APIRouter()


class DiceRoll(BaseModel):
    dice: str
    modifier: Optional[int] = 0
    advantage: Optional[bool] = False
    disadvantage: Optional[bool] = False


class DiceResult(BaseModel):
    dice: str
    rolls: List[int]
    modifier: int
    total: int
    natural: Optional[int] = None
    is_critical: bool = False
    is_fumble: bool = False


@router.post("/roll", response_model=List[DiceResult])
async def roll_dice(
    rolls: List[DiceRoll],
    current_user: User = Depends(get_current_user)
):
    results = []

    for roll in rolls:
        dice_match = re.match(r"(\d+)d(\d+)", roll.dice.lower())
        if not dice_match:
            continue

        num_dice = int(dice_match.group(1))
        die_size = int(dice_match.group(2))

        if num_dice > 100 or die_size > 100:
            continue

        roll_values = []
        natural = None

        if roll.advantage or roll.disadvantage:
            roll1 = random.randint(1, die_size)
            roll2 = random.randint(1, die_size)
            natural = roll1 if roll.advantage else roll2
            chosen = max(roll1, roll2) if roll.advantage else min(roll1, roll2)
            roll_values.append(chosen)
        else:
            for _ in range(num_dice):
                roll_values.append(random.randint(1, die_size))
            if num_dice == 1 and die_size == 20:
                natural = roll_values[0]

        total = sum(roll_values) + (roll.modifier or 0)
        is_critical = natural == 20 if natural else False
        is_fumble = natural == 1 if natural else False

        results.append(DiceResult(
            dice=roll.dice,
            rolls=roll_values,
            modifier=roll.modifier or 0,
            total=total,
            natural=natural,
            is_critical=is_critical,
            is_fumble=is_fumble
        ))

    return results


@router.post("/roll/{dice}", response_model=DiceResult)
async def roll_single_dice(
    dice: str,
    modifier: Optional[int] = 0,
    advantage: bool = False,
    disadvantage: bool = False,
    current_user: User = Depends(get_current_user)
):
    return await roll_dice(
        [DiceRoll(dice=dice, modifier=modifier, advantage=advantage, disadvantage=disadvantage)],
        current_user
    )[0]