import random
import json
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum


class MapAlgorithm(str, Enum):
    STANDARD = "standard"
    BSP = "bsp"
    CAVERNS = "caverns"
    ROGUELIKE = "roguelike"


class MapGenerator:
    TERRAIN_TYPES = [
        "floor", "wall", "door", "stairs_up", "stairs_down",
        "water", "lava", "pit", "treasure", "trap", "corridor"
    ]

    DUNGEON_THEMES = {
        "standard": {
            "prefixes": ["Dark", "Ancient", "Forgotten", "Hidden", "Lost", "Secret", "Cursed", "Sacred"],
            "nouns": ["Chamber", "Hall", "Vault", "Sanctum", "Tomb", "Crypt", "Library", "Armory", "Laboratory"],
            "features": ["pillar", "statue", "altar", "pool", "runes", "chains", "debris"],
            "enemy_types": ["skeleton", "goblin", "zombie", "orc"],
            "treasure_types": ["gold", "gem", "potion", "weapon"],
            "descriptions": [
                "A dimly lit chamber with stone walls covered in dust.",
                "Torchlight flickers, revealing ancient carvings on the walls.",
                "The air is thick with the smell of age and decay.",
                "Cracks run through the stone floor from an ancient battle.",
                "Faded tapestries hang from the walls, telling lost tales."
            ]
        },
        "cave": {
            "prefixes": ["Crystal", "Echo", "Dripping", "Underground", "Stalactite", "Gloomy", "Fungal", "Damp"],
            "nouns": ["Cavern", "Grotto", "Chasm", "Passage", "Crevice", "Cave", "Grove", "Chamber"],
            "features": ["stalactite", "stalagmite", "bioluminescent", "stream", "pool", "crystal", "mushroom"],
            "enemy_types": ["spider", "cave rat", "deep goblin", "myconid"],
            "treasure_types": ["gem", "ore", "mushroom", "water"],
            "descriptions": [
                "Damp walls glisten with moisture. Strange crystals protrude from the rock.",
                "Bioluminescent fungi provide an eerie glow. Webs cover the corners.",
                "Water drips continuously from stalactites above.",
                "The cave opens into a vast chamber filled with crystals.",
                "Strange fungal growths pulse with an inner light."
            ]
        },
        "crypt": {
            "prefixes": ["Endless", "Silent", "Broken", "Ancestral", "Buried", "Eternal", "Frozen", "Haunted"],
            "nouns": ["Crypt", "Tomb", "Graveyard", "Vault", "Mausoleum", "Catacomb", "Sepulcher"],
            "features": ["coffin", "skeleton", "tombstone", "casket", "bone", "rune", "urn"],
            "enemy_types": ["skeleton", "zombie", "ghost", "wraith"],
            "treasure_types": ["gem", "artifact", "scroll", "key"],
            "descriptions": [
                "Ancient stone sarcophagi line the walls. The air is cold and stale.",
                "Bone fragments scatter the floor. Something disturbes the dead here.",
                "Ghostly whispers echo through the darkness.",
                "Faded family crests mark each burial niche.",
                "An unnatural chill permeates this final resting place."
            ]
        },
        "fortress": {
            "prefixes": ["Upper", "Lower", "Inner", "Outer", "Guard", "War", "Iron", "Stone"],
            "nouns": ["Tower", "Barracks", "Gatehouse", "Keep", "Wall", "Courtyard", "Armory", "Watchtower"],
            "features": ["torch", "peephole", "portcullis", "arrow_slit", "banners", "weapon_rack"],
            "enemy_types": ["guard", "cultist", "bandit", "warrior"],
            "treasure_types": ["weapon", "armor", "gold", "key"],
            "descriptions": [
                "Torches flicker on the walls. Arrow slits provide light.",
                "Weapon racks line the walls, some still stocked.",
                "The smell of old iron and dried blood.",
                "Defensive positions command views of all approaches.",
                "Worn stone shows the passage of many battles."
            ]
        },
        "underdark": {
            "prefixes": ["Fungal", "Myconid", "Drow", "Deep", "Twisted", "Glowing", "Dark", "Veil"],
            "nouns": ["Grove", "Nest", "Web", "Cavern", "Bridge", "Outpost", "Colony", "Reach"],
            "features": ["web", "mushroom", "spider", "crystal", "fungus", "bridge", "prison"],
            "enemy_types": ["drow", "spider", "myconid", "kobold", "beholder"],
            "treasure_types": ["gem", "spell scroll", "artifact", "rare metal"],
            "descriptions": [
                "Bioluminescent fungi provide an eerie glow. Webs cover the corners.",
                "Strange purple light emanates from crystalline growths.",
                "The whisper of the Deep speaks in dreams.",
                "Ancient drow architecture intersects with natural caverns.",
                "Fungal forests grow in impossible darkness."
            ]
        },
        "temple": {
            "prefixes": ["Sacred", "Holy", "Divine", "Temple", "Shrine", "Sanctum", "Temple"],
            "nouns": ["Sanctuary", "Altar", "Shrine", "Hall", " Nave", "Crypt", "Courtyard"],
            "features": ["altar", "statue", "font", "relic", "idol", "symbol", "candle"],
            "enemy_types": ["cultist", "acolyte", "zombie", "construct"],
            "treasure_types": ["relic", "gold", "scroll", "potion"],
            "descriptions": [
                "Holy light streams through stained glass windows.",
                "An ancient altar dominates the center of the chamber.",
                "Faded murals depict the glory of forgotten gods.",
                "Incense smoke mingles with the darkness.",
                "Holy water fills a carved stone font."
            ]
        },
        "mine": {
            "prefixes": [" Iron", "Gold", "Silver", "Coal", "Copper", "Deep", "Old", "Abandoned"],
            "nouns": ["Shaft", "Vein", "Gallery", "Chamber", "Lift", "Track", "Workface"],
            "features": ["track", "cart", "pickaxe", "ore", "support", "water", "ladder"],
            "enemy_types": ["kobold", "cave rat", "construct", "ghost"],
            "treasure_types": ["ore", "gem", "gold", "artifact"],
            "descriptions": [
                "Wooden supports creak under the weight of stone.",
                "Abandoned mining equipment litters the passage.",
                "The echo of pickaxes rings in distant tunnels.",
                "Ore veins sparkle in the walls.",
                "An old mine cart sits on rusted tracks."
            ]
        }
    }

    WILDERNESS_BIOMES = {
        "forest": {
            "terrains": ["grass", "forest", "dense_forest", "path", "river", "clearing"],
            "weights": {"grass": 25, "forest": 40, "dense_forest": 15, "path": 5, "river": 5, "clearing": 5},
            "features": ["stream", "clearing", "tree", "rock", "log", "mushroom"],
            "enemy_types": ["wolf", "bear", "goblin", "bandit"],
            "structures": ["hunter's blind", "druid grove", "old shrine", "campfire"],
            "descriptions": [
                "Towering trees block most sunlight. Birdsong fills the air.",
                "A gentle stream cuts through the forest floor.",
                "Sunlight filters through the dense canopy.",
                "Old-growth trees tower overhead.",
                "A clearing offers a rare view of the sky."
            ]
        },
        "desert": {
            "terrains": ["sand", "rock", "dune", "oasis", "road", "ruins"],
            "weights": {"sand": 50, "rock": 20, "dune": 15, "oasis": 3, "road": 7, "ruins": 5},
            "features": ["ruins", "cactus", "skeleton", "oasis", "rock", "sandstorm"],
            "enemy_types": ["scorpion", "bandit", "mummy", "sandworm"],
            "structures": ["oasis", "caravanserai", "temple", "watchtower"],
            "descriptions": [
                "Endless sand dunes stretch to the horizon.",
                "Heat mirages dance on the distant dunes.",
                "Ancient ruins emerge from the shifting sand.",
                "A palm oasis provides welcome shade.",
                "The hot wind whips sand against your face."
            ]
        },
        "arctic": {
            "terrains": ["snow", "ice", "rock", "frozen_lake", "snowdrift", "cave"],
            "weights": {"snow": 40, "ice": 25, "rock": 20, "frozen_lake": 7, "snowdrift": 5, "cave": 3},
            "features": ["ice_spire", "cairn", "cave", "frozen_rune", "skeleton", "aurora"],
            "enemy_types": ["yeti", "ice mephit", "white dragon", "frost giant"],
            "structures": ["ice cave", "frozen shrine", "hunter's camp", "ancient ruin"],
            "descriptions": [
                "Snow covers everything in pristine white.",
                "Ice crystals glitter in the pale light.",
                "A frozen lake reflects the sky like glass.",
                "The aurora dances in the night sky.",
                "Frozen bones mark a failed expedition."
            ]
        },
        "jungle": {
            "terrains": ["dense_jungle", "canopy", "swamp", "water", "path", "ruins"],
            "weights": {"dense_jungle": 45, "canopy": 20, "swamp": 15, "water": 10, "path": 5, "ruins": 5},
            "features": ["vine", "ruins", "temple", "stream", "waterfall", "flower"],
            "enemy_types": ["snake", "jaguar", "dinosaur", "piranha"],
            "structures": ["ancient temple", "tribal village", "shrine", "pyramid"],
            "descriptions": [
                "Steam rises from the jungle floor.",
                "Ancient stone emerges from the green mass.",
                "Birds of paradise fly through the canopy.",
                "The call of unknown creatures echoes.",
                "A hidden temple waits in the depths."
            ]
        },
        "swamp": {
            "terrains": ["water", "mud", "moss", "dead_tree", "island", "path"],
            "weights": {"water": 30, "mud": 25, "moss": 20, "dead_tree": 15, "island": 5, "path": 5},
            "features": ["mushroom", "frog", "skeleton", "witch_hut", "cattail", "bone"],
            "enemy_types": ["witch", "lizardfolk", "crocodile", "will-o'-wisp"],
            "structures": ["witch's hut", "crocodile nest", "old shrine", "wreckage"],
            "descriptions": [
                "Murky water laps at ancient cypress roots.",
                "Mist hangs low over the still water.",
                "Strange lights dance in the distance.",
                "The smell of decay saturates the air.",
                "Bulbous mushrooms glow with sickly light."
            ]
        },
        "coastal": {
            "terrains": ["sand", "water", "rock", "cliff", "grass", "forest"],
            "weights": {"sand": 35, "water": 30, "rock": 15, "cliff": 10, "grass": 5, "forest": 5},
            "features": ["shipwreck", "shell", "coral", "cave", "lighthouse", "fishing net"],
            "enemy_types": ["sahuagin", "crab", "merfolk", "pirate"],
            "structures": ["lighthouse", "fishing village", "shipwreck", "shrine"],
            "descriptions": [
                "Waves crash against the rocky shore.",
                "Salt spray fills the air.",
                "A lone lighthouse stands on the cliff.",
                "Ship wreckage litters the beach.",
                "Seabirds cry overhead."
            ]
        },
        "mountain": {
            "terrains": ["rock", "snow", "grass", "cliff", "cave", "pass"],
            "weights": {"rock": 40, "snow": 25, "grass": 15, "cliff": 10, "cave": 5, "pass": 5},
            "features": ["cave", "waterfall", "eagle's nest", "cairn", "overlook", "crack"],
            "enemy_types": ["bandit", "ogre", "mantheon", "roc"],
            "structures": ["mountain keep", "watchtower", "shrine", "cave complex"],
            "descriptions": [
                "The path winds up through craggy peaks.",
                "Snowcapped mountains loom overhead.",
                "A sheer cliff blocks the way forward.",
                "Mountain goats watch from narrow ledges.",
                "An eagle circles on the thermal."
            ]
        }
    }

    SETTLEMENT_TYPES = {
        "village": {
            "buildings": ["house", "inn", "smithy", "general store"],
            "features": ["well", "fountain", "market square", "town hall"],
            "population": "50-200"
        },
        "town": {
            "buildings": ["house", "inn", "smithy", "temple", "tannery", "bakery", "guild hall"],
            "features": ["well", "market square", "town hall", "gates", "walls"],
            "population": "200-1000"
        },
        "city": {
            "buildings": ["house", "inn", "smithy", "temple", "palace", "arena", "university"],
            "features": ["walls", "dungeons", "palace", "arena", "harbor", "university"],
            "population": "1000-10000"
        }
    }

    def __init__(self):
        self.dungeon_rooms = []
        self.wilderness_grid = []
        self.algorithm = MapAlgorithm.STANDARD

    def generate(
        self,
        map_type: str = "dungeon",
        width: int = 50,
        height: int = 50,
        difficulty: str = "medium",
        theme: str = "standard",
        seed: Optional[str] = None,
        algorithm: str = "standard"
    ) -> Dict[str, Any]:
        if seed:
            if seed.isdigit():
                random.seed(int(seed))
            else:
                random.seed(hash(seed))
        else:
            random.seed()

        try:
            self.algorithm = MapAlgorithm(algorithm)
        except ValueError:
            self.algorithm = MapAlgorithm.STANDARD

        if map_type == "dungeon":
            return self._generate_dungeon(width, height, difficulty, theme)
        elif map_type == "wilderness":
            return self._generate_wilderness(width, height, theme)
        elif map_type == "settlement":
            return self._generate_settlement(width, height, theme)
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
        if self.algorithm == MapAlgorithm.BSP:
            return self._generate_dungeon_bsp(width, height, difficulty, theme)
        elif self.algorithm == MapAlgorithm.CAVERNS:
            return self._generate_dungeon_cellular(width, height, difficulty, theme)
        elif self.algorithm == MapAlgorithm.ROGUELIKE:
            return self._generate_dungeon_roguelike(width, height, difficulty, theme)
        else:
            return self._generate_dungeon_standard(width, height, difficulty, theme)

    def _generate_dungeon_standard(
        self,
        width: int,
        height: int,
        difficulty: str,
        theme: str
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
                "description": self._generate_room_description(theme),
                "connected_to": None
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
            rooms[i]["connected_to"] = rooms[i + 1]["name"]

        if rooms:
            grid[rooms[0]["y"] + rooms[0]["height"] // 2][rooms[0]["x"]]["terrain"] = "door"
            grid[rooms[-1]["y"] + rooms[-1]["height"] // 2][rooms[-1]["x"] + rooms[-1]["width"] - 1]["terrain"] = "door"

        self._add_features(grid, rooms, difficulty, theme)
        self.dungeon_rooms = rooms

        return {
            "type": "dungeon",
            "theme": theme,
            "algorithm": self.algorithm.value,
            "width": width,
            "height": height,
            "grid": grid,
            "rooms": rooms,
            "difficulty": difficulty
        }

    def _generate_dungeon_bsp(
        self,
        width: int,
        height: int,
        difficulty: str,
        theme: str
    ) -> Dict[str, Any]:
        grid = [[{"terrain": "wall", "features": [], "entities": []} for _ in range(width)] for _ in range(height)]
        
        def split_rect(x: int, y: int, w: int, h: int, depth: int = 0) -> List[Dict]:
            if depth > 3 or (w < 6 and h < 6):
                room_w = max(4, w - 2)
                room_h = max(4, h - 2)
                room_x = x + random.randint(1, w - room_w - 1)
                room_y = y + random.randint(1, h - room_h - 1)
                return [{
                    "x": room_x, "y": room_y,
                    "width": room_w, "height": room_h,
                    "name": self._generate_room_name(theme),
                    "description": self._generate_room_description(theme),
                    "connected_to": None
                }]
            
            if random.random() > 0.5:
                split = random.randint(3, w - 4)
                return split_rect(x, y, split, h, depth + 1) + split_rect(x + split, y, w - split, h, depth + 1)
            else:
                split = random.randint(3, h - 4)
                return split_rect(x, y, w, split, depth + 1) + split_rect(x, y + split, w, h - split, depth + 1)

        rooms = split_rect(1, 1, width - 2, height - 2)
        
        for room in rooms:
            for ry in range(room["y"], room["y"] + room["height"]):
                for rx in range(room["x"], room["x"] + room["width"]):
                    if 0 <= ry < height and 0 <= rx < width:
                        grid[ry][rx] = {"terrain": "floor", "features": [], "entities": []}

        for i in range(len(rooms) - 1):
            x1 = rooms[i]["x"] + rooms[i]["width"] // 2
            y1 = rooms[i]["y"] + rooms[i]["height"] // 2
            x2 = rooms[i + 1]["x"] + rooms[i + 1]["width"] // 2
            y2 = rooms[i + 1]["y"] + rooms[i + 1]["height"] // 2
            self._carve_corridor(grid, x1, y1, x2, y2, width, height)
            rooms[i]["connected_to"] = rooms[i + 1]["name"]

        self._add_features(grid, rooms, difficulty, theme)
        self.dungeon_rooms = rooms

        return {
            "type": "dungeon",
            "theme": theme,
            "algorithm": "bsp",
            "width": width,
            "height": height,
            "grid": grid,
            "rooms": rooms,
            "difficulty": difficulty
        }

    def _generate_dungeon_cellular(
        self,
        width: int,
        height: int,
        difficulty: str,
        theme: str
    ) -> Dict[str, Any]:
        grid = [[{"terrain": "wall", "features": [], "entities": []} for _ in range(width)] for _ in range(height)]
        
        for y in range(height):
            for x in range(width):
                if random.random() < 0.48:
                    grid[y][x]["terrain"] = "wall"
        
        for _ in range(5):
            temp_grid = [row[:] for row in grid]
            for y in range(1, height - 1):
                for x in range(1, width - 1):
                    walls = 0
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            if grid[y + dy][x + dx]["terrain"] == "wall":
                                walls += 1
                    if walls > 4:
                        temp_grid[y][x]["terrain"] = "wall"
                    elif walls < 4:
                        temp_grid[y][x]["terrain"] = "floor"
            grid = temp_grid
        
        rooms = []
        for y in range(2, height - 2):
            for x in range(2, width - 2):
                if grid[y][x]["terrain"] == "floor":
                    room = {"x": x, "y": y, "width": 1, "height": 1, "name": self._generate_room_name(theme), "description": self._generate_room_description(theme)}
                    rooms.append(room)
        
        self._add_features(grid, rooms[:10] if len(rooms) > 10 else rooms, difficulty, theme)
        self.dungeon_rooms = rooms[:10] if len(rooms) > 10 else rooms

        return {
            "type": "dungeon",
            "theme": theme,
            "algorithm": "caverns",
            "width": width,
            "height": height,
            "grid": grid,
            "rooms": rooms[:10] if len(rooms) > 10 else rooms,
            "difficulty": difficulty
        }

    def _generate_dungeon_roguelike(
        self,
        width: int,
        height: int,
        difficulty: str,
        theme: str
    ) -> Dict[str, Any]:
        grid = [[{"terrain": "wall", "features": [], "entities": []} for _ in range(width)] for _ in range(height)]
        
        num_rooms = {
            "easy": random.randint(6, 10),
            "medium": random.randint(10, 15),
            "hard": random.randint(15, 20)
        }.get(difficulty, 12)

        rooms = []
        attempts = 0
        max_attempts = 1000
        
        while len(rooms) < num_rooms and attempts < max_attempts:
            attempts += 1
            room_width = random.randint(3, 8)
            room_height = random.randint(3, 8)
            x = random.randint(1, width - room_width - 1)
            y = random.randint(1, height - room_height - 1)

            overlaps = False
            for room in rooms:
                min_dist = 2
                if (x < room["x"] + room["width"] + min_dist and
                    x + room_width + min_dist > room["x"] and
                    y < room["y"] + room["height"] + min_dist and
                    y + room_height + min_dist > room["y"]):
                    overlaps = True
                    break

            if not overlaps:
                rooms.append({
                    "x": x, "y": y,
                    "width": room_width, "height": room_height,
                    "name": self._generate_room_name(theme),
                    "description": self._generate_room_description(theme),
                    "connected_to": None
                })
                for ry in range(y, y + room_height):
                    for rx in range(x, x + room_width):
                        grid[ry][rx] = {"terrain": "floor", "features": [], "entities": []}

        connections = 0
        while connections < len(rooms) - 1:
            rooms_to_connect = list(range(len(rooms)))
            for i in range(len(rooms) - 1):
                closest_dist = float('inf')
                closest_idx = -1
                for j in range(i + 1, len(rooms)):
                    dx = abs(rooms[i]["x"] - rooms[j]["x"])
                    dy = abs(rooms[i]["y"] - rooms[j]["y"])
                    dist = dx + dy
                    if dist < closest_dist and j not in [r.get("idx") for r in rooms[i].get("connected", {}).values() if "idx" in r]:
                        closest_dist = dist
                        closest_idx = j
                if closest_idx >= 0:
                    x1 = rooms[i]["x"] + rooms[i]["width"] // 2
                    y1 = rooms[i]["y"] + rooms[i]["height"] // 2
                    x2 = rooms[closest_idx]["x"] + rooms[closest_idx]["width"] // 2
                    y2 = rooms[closest_idx]["y"] + rooms[closest_idx]["height"] // 2
                    self._carve_corridor(grid, x1, y1, x2, y2, width, height)
                    rooms[i]["connected_to"] = rooms[closest_idx]["name"]
                    connections += 1

        self._add_features(grid, rooms, difficulty, theme)
        self.dungeon_rooms = rooms

        return {
            "type": "dungeon",
            "theme": theme,
            "algorithm": "roguelike",
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

    def _generate_settlement(
        self,
        width: int,
        height: int,
        settlement_type: str = "village"
    ) -> Dict[str, Any]:
        grid = [[{"terrain": "wall", "features": [], "entities": []} for _ in range(width)] for _ in range(height)]
        
        data = self.SETTLEMENT_TYPES.get(settlement_type, self.SETTLEMENT_TYPES["village"])
        
        for y in range(1, height - 1):
            for x in range(1, width - 1):
                grid[y][x] = {"terrain": "grass", "features": [], "entities": []}

        buildings = []
        num_buildings = {
            "village": random.randint(3, 6),
            "town": random.randint(6, 12),
            "city": random.randint(12, 20)
        }.get(settlement_type, 4)

        for _ in range(num_buildings):
            bldg_w = random.randint(3, 6)
            bldg_h = random.randint(3, 5)
            bx = random.randint(2, width - bldg_w - 2)
            by = random.randint(2, height - bldg_h - 2)

            overlaps = False
            for b in buildings:
                if (bx < b["x"] + b["width"] + 1 and bx + bldg_w + 1 > b["x"] and
                    by < b["y"] + b["height"] + 1 and by + bldg_h + 1 > b["y"]):
                    overlaps = True
                    break

            if not overlaps:
                buildings.append({
                    "x": bx, "y": by,
                    "width": bldg_w, "height": bldg_h,
                    "type": random.choice(data["buildings"]),
                    "name": f"{random.choice(['Old', 'New', 'The', 'Iron'])} {random.choice(['Inn', 'Smith', 'Shop', 'Hall', 'Temple'])}"
                })
                for y in range(by, by + bldg_h):
                    for x in range(bx, bx + bldg_w):
                        grid[y][x] = {"terrain": "floor", "features": [], "entities": []}

        for f in data["features"]:
            fx = random.randint(2, width - 3)
            fy = random.randint(2, height - 3)
            grid[fy][fx]["features"].append(f)

        return {
            "type": "settlement",
            "subtype": settlement_type,
            "width": width,
            "height": height,
            "grid": grid,
            "buildings": buildings,
            "features": data["features"],
            "population": data["population"]
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