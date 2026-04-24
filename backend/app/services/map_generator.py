import random
import json
from typing import Dict, List, Any, Optional, Tuple


class MapGenerator:
    TERRAIN_TYPES = [
        "floor", "wall", "door", "stairs_up", "stairs_down",
        "water", "lava", "pit", "treasure", "trap", "corridor"
    ]

    DUNGEON_THEMES = {
        "standard": {
            "prefixes": ["Dark", "Ancient", "Forgotten", "Hidden", "Lost", "Secret", "Cursed", "Sacred"],
            "nouns": ["Chamber", "Hall", "Vault", "Sanctum", "Tomb", "Crypt", "Library", "Armory", "Laboratory"],
            "features": ["pilar", "statue", "altar", "pool"]
        },
        "cave": {
            "prefixes": ["Crystal", "Echo", "Dripping", "Underground", "Stalactite", "Gloomy"],
            "nouns": ["Cavern", "Grotto", "Chasm", "Passage", "Crevice", "Cave"],
            "features": ["stalactite", "stalagmite", "bioluminescent", "stream"]
        },
        "crypt": {
            "prefixes": ["Endless", "Silent", "Broken", "Ancestral", "Buried", "Eternal"],
            "nouns": ["Crypt", "Tomb", "Graveyard", "Vault", "Mausoleum", "Catacomb"],
            "features": ["coffin", "skeleton", "tombstone", "casket"]
        },
        "fortress": {
            "prefixes": ["Upper", "Lower", "Inner", "Outer", "Guard", "War"],
            "nouns": ["Tower", "Barracks", "Gatehouse", "Keep", "Wall", "Courtyard"],
            "features": ["torch", "peephole", "portcullis", "arrow_slit"]
        },
        "underdark": {
            "prefixes": ["Fungal", "Myconid", "Drow", "Deep", "Glowing", "Twisted"],
            "nouns": ["Grove", "Nest", "Web", "Cavern", "Bridge", "Outpost"],
            "features": ["web", "mushroom", "spider", "crystal", " fungi"]
        }
    }

    WILDERNESS_BIOMES = {
        "forest": {
            "terrains": ["grass", "forest", "dense_forest", "path"],
            "weights": {"grass": 30, "forest": 50, "dense_forest": 15, "path": 5},
            "features": ["stream", "clearing", "tree"]
        },
        "desert": {
            "terrains": ["sand", "rock", "dune", "oasis"],
            "weights": {"sand": 60, "rock": 25, "dune": 10, "oasis": 5},
            "features": ["ruins", "cactus", "skeleton", "oasis"]
        },
        "arctic": {
            "terrains": ["snow", "ice", "rock", "frozen_lake"],
            "weights": {"snow": 50, "ice": 30, "rock": 15, "frozen_lake": 5},
            "features": ["ice_spire", "cairn", "cave", "frozen_rune"]
        },
        "jungle": {
            "terrains": ["dense_jungle", "canopy", "swamp", "water"],
            "weights": {"dense_jungle": 55, "canopy": 25, "swamp": 15, "water": 5},
            "features": ["vine", "ruins", "temple", "stream"]
        },
        "swamp": {
            "terrains": ["water", "mud", "moss", "dead_tree"],
            "weights": {"water": 35, "mud": 30, "moss": 20, "dead_tree": 15},
            "features": ["mushroom", "frog", "skeleton", "witch_hut"]
        }
    }

    def __init__(self):
        self.dungeon_rooms = []
        self.wilderness_grid = []

    def generate(
        self,
        map_type: str = "dungeon",
        width: int = 50,
        height: int = 50,
        difficulty: str = "medium",
        theme: str = "standard",
        seed: Optional[str] = None
    ) -> Dict[str, Any]:
        if seed:
            random.seed(int(seed) if seed.isdigit() else hash(seed))
        else:
            random.seed()

        if map_type == "dungeon":
            return self._generate_dungeon(width, height, difficulty, theme)
        elif map_type == "wilderness":
            return self._generate_wilderness(width, height, theme)
        elif map_type == "tavern":
            return self._generate_tavern_or_town(width, height, "tavern")
        elif map_type == "town":
            return self._generate_tavern_or_town(width, height, "town")
        else:
            return self._generate_dungeon(width, height, difficulty)

    def _generate_dungeon(
        self,
        width: int,
        height: int,
        difficulty: str,
        theme: str = "standard"
    ) -> Dict[str, Any]:
        grid = [[{"terrain": "wall", "features": [], "entities": []} for _ in range(width)] for _ in range(height)]

        num_rooms = {
            "easy": random.randint(5, 8),
            "medium": random.randint(8, 12),
            "hard": random.randint(12, 16)
        }.get(difficulty, 10)

        rooms = []
        for _ in range(num_rooms):
            room_width = random.randint(4, 10)
            room_height = random.randint(4, 10)
            x = random.randint(1, width - room_width - 1)
            y = random.randint(1, height - room_height - 1)

            new_room = {
                "x": x, "y": y,
                "width": room_width, "height": room_height,
                "name": self._generate_room_name(theme),
                "description": self._generate_room_description(theme)
            }

            overlaps = False
            for room in rooms:
                if (x < room["x"] + room["width"] + 1 and
                    x + room_width + 1 > room["x"] and
                    y < room["y"] + room["height"] + 1 and
                    y + room_height + 1 > room["y"]):
                    overlaps = True
                    break

            if not overlaps:
                rooms.append(new_room)
                for ry in range(y, y + room_height):
                    for rx in range(x, x + room_width):
                        grid[ry][rx] = {"terrain": "floor", "features": [], "entities": []}

        for i in range(len(rooms) - 1):
            x1 = rooms[i]["x"] + rooms[i]["width"] // 2
            y1 = rooms[i]["y"] + rooms[i]["height"] // 2
            x2 = rooms[i + 1]["x"] + rooms[i + 1]["width"] // 2
            y2 = rooms[i + 1]["y"] + rooms[i + 1]["height"] // 2

            self._carve_corridor(grid, x1, y1, x2, y2, width, height)

        if rooms:
            grid[rooms[0]["y"] + rooms[0]["height"] // 2][rooms[0]["x"]]["terrain"] = "door"
            grid[rooms[-1]["y"] + rooms[-1]["height"] // 2][rooms[-1]["x"] + rooms[-1]["width"] - 1]["terrain"] = "door"

        self._add_features(grid, rooms, difficulty, theme)

        self.dungeon_rooms = rooms

        return {
            "type": "dungeon",
            "theme": theme,
            "width": width,
            "height": height,
            "grid": grid,
            "rooms": rooms,
            "difficulty": difficulty
        }

    def _generate_wilderness(
        self,
        width: int,
        height: int,
        biome: str = "forest"
    ) -> Dict[str, Any]:
        biome_data = self.WILDERNESS_BIOMES.get(biome, self.WILDERNESS_BIOMES["forest"])
        weights = biome_data["weights"]
        
        grid = [[{"terrain": "grass", "features": [], "entities": []} for _ in range(width)] for _ in range(height)]

        for y in range(height):
            for x in range(width):
                terrain = random.choices(
                    list(weights.keys()),
                    weights=list(weights.values())
                )[0]
                grid[y][x]["terrain"] = terrain
                if random.random() < 0.1:
                    grid[y][x]["features"].append(random.choice(biome_data["features"]))

        locations_count = random.randint(2, 5)
        locations = []
        for _ in range(locations_count):
            locations.append({
                "name": self._generate_location_name(biome),
                "x": random.randint(2, width - 3),
                "y": random.randint(2, height - 3),
                "type": random.choice(["village", "ruin", "shrine", "cave"])
            })

        return {
            "type": "wilderness",
            "biome": biome,
            "width": width,
            "height": height,
            "grid": grid,
            "locations": locations
        }

    def _generate_tavern_or_town(
        self,
        width: int,
        height: int,
        building_type: str = "tavern"
    ) -> Dict[str, Any]:
        grid = [[{"terrain": "wall", "features": [], "entities": []} for _ in range(width)] for _ in range(height)]

        for y in range(1, height - 1):
            for x in range(1, width - 1):
                grid[y][x] = {"terrain": "floor", "features": [], "entities": []}

        grid[height // 2][0] = {"terrain": "door", "features": [], "entities": []}
        grid[height // 2][width - 1] = {"terrain": "door", "features": [], "entities": []}

        features = []
        if building_type == "tavern":
            bar_pos = (width // 4, height // 2)
            for y in range(bar_pos[1] - 1, bar_pos[1] + 2):
                grid[y][bar_pos[0]] = {"terrain": "counter", "features": ["bar"], "entities": []}
            features = ["bar", "tables", "fireplace", "upstairs"]
        else:
            for x in range(2, width - 2, 5):
                for y in range(2, height - 2, 5):
                    if random.random() < 0.5:
                        grid[y][x] = {"terrain": "floor", "features": [random.choice(["shop", "house", "temple"])], "entities": []}
            features = ["market", "guild", "temple", "inn"]

        return {
            "type": building_type,
            "width": width,
            "height": height,
            "grid": grid,
            "features": features
        }

    def _carve_corridor(
        self,
        grid: List[List[Dict]],
        x1: int, y1: int,
        x2: int, y2: int,
        width: int, height: int
    ):
        x, y = x1, y1

        while x != x2:
            if 0 < x < width - 1 and 0 < y < height - 1:
                if grid[y][x]["terrain"] == "wall":
                    grid[y][x] = {"terrain": "corridor", "features": [], "entities": []}
            x += 1 if x2 > x1 else -1

        while y != y2:
            if 0 < x < width - 1 and 0 < y < height - 1:
                if grid[y][x]["terrain"] == "wall":
                    grid[y][x] = {"terrain": "corridor", "features": [], "entities": []}
            y += 1 if y2 > y1 else -1

    def _add_features(
        self,
        grid: List[List[Dict]],
        rooms: List[Dict],
        difficulty: str,
        theme: str
    ):
        theme_data = self.DUNGEON_THEMES.get(theme, self.DUNGEON_THEMES["standard"])
        feature_pool = theme_data.get("features", ["pilar", "altar"])

        treasure_rooms = random.sample(rooms, min(len(rooms) // 3, 3))
        for room in treasure_rooms:
            cx = room["x"] + room["width"] // 2
            cy = room["y"] + room["height"] // 2
            if grid[cy][cx]["terrain"] == "floor":
                grid[cy][cx]["features"].append("treasure")

        trap_chance = {"easy": 0.1, "medium": 0.2, "hard": 0.35}.get(difficulty, 0.2)
        for room in rooms:
            if random.random() < trap_chance:
                rx = room["x"] + random.randint(1, room["width"] - 2)
                ry = room["y"] + random.randint(1, room["height"] - 2)
                if grid[ry][rx]["terrain"] == "floor":
                    grid[ry][rx]["terrain"] = "trap"

    def _generate_room_name(self, theme: str = "standard") -> str:
        theme_data = self.DUNGEON_THEMES.get(theme, self.DUNGEON_THEMES["standard"])
        prefixes = theme_data["prefixes"]
        nouns = theme_data["nouns"]
        return f"{random.choice(prefixes)} {random.choice(nouns)}"

    def _generate_room_description(self, theme: str = "standard") -> str:
        descriptions = {
            "standard": "A dimly lit chamber with stone walls covered in dust.",
            "cave": "Damp walls glisten with moisture. Strange crystals protrude from the rock.",
            "crypt": "Ancient stone sarcophagi line the walls. The air is cold and stale.",
            "fortress": "Torches flicker on the walls. Arrow slits provide light.",
            "underdark": "Bioluminescent fungi provide an eerie glow. Webs cover the corners."
        }
        return descriptions.get(theme, descriptions["standard"])

    def _generate_location_name(self, biome: str) -> str:
        names = {
            "forest": ["Elven Outpost", "Druid Grove", "Hunter's Camp"],
            "desert": ["Desert Oasis", "Ancient Ruins", "Nomad Camp"],
            "arctic": ["Ice Cave", "Frozen Shrine", "Yeti Den"],
            "jungle": ["Ancient Temple", "Tribal Village", "Snake Pit"],
            "swamp": ["Witch's Hut", "Bog-standard", "Frog Temple"]
        }
        return random.choice(names.get(biome, ["Location"]))

    def describe_for_ai(
        self,
        map_data: Dict,
        entities: List[Tuple] = None
    ) -> str:
        map_type = map_data.get("type", "dungeon")
        theme = map_data.get("theme", "standard")
        rooms = map_data.get("rooms", [])
        locations = map_data.get("locations", [])

        theme_descriptions = {
            "standard": "An ancient dungeon complex",
            "cave": "A natural cave system with crystalline formations",
            "crypt": "An underground burial complex",
            "fortress": "A fortified stronghold",
            "underdark": "A cavern in the depths below"
        }

        description = f"{theme_descriptions.get(theme, theme_descriptions['standard'])}.\n"

        if rooms:
            description += "\nNotable locations:\n"
            for room in rooms:
                desc = room.get("description", "")
                description += f"- {room.get('name', 'Unnamed room')} at ({room['x']}, {room['y']}), size {room['width']}x{room['height']}: {desc}\n"

        if locations:
            description += "\nPoints of interest:\n"
            for loc in locations:
                description += f"- {loc.get('name', 'Location')} ({loc.get('type')}) at ({loc['x']}, {loc['y']})\n"

        if entities:
            description += "\nEntities present:\n"
            for entity, character in entities:
                if character:
                    description += f"- {character.name} ({entity.entity_type}) at ({entity.x}, {entity.y})\n"
                else:
                    description += f"- {entity.name} ({entity.entity_type}) at ({entity.x}, {entity.y})\n"

        description += "\nThe map is represented as a grid. Players can move to adjacent cells."

        return description