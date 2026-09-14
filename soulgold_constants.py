import json
import os
from typing import Dict, List, Tuple

MODULE_DIR = os.path.dirname(os.path.abspath(__file__))

def _load_json(filename: str) -> dict:
    path = os.path.join(MODULE_DIR, filename)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

_raw_species = _load_json("species.json")
SPECIES: Dict[int, str] = {int(k): v for k, v in _raw_species.items()}
SPECIES_BY_NAME: Dict[str, int] = {v.lower(): k for k, v in SPECIES.items()}

_raw_moves = _load_json("moves.json")
MOVES: Dict[int, str] = {int(k): v for k, v in _raw_moves.items()}
MOVES_BY_NAME: Dict[str, int] = {v.lower(): k for k, v in MOVES.items()}

_raw_items = _load_json("items.json")
ITEMS: Dict[int, str] = {int(k): v for k, v in _raw_items.items()}
ITEMS_BY_NAME: Dict[str, int] = {v.lower(): k for k, v in ITEMS.items()}

_raw_abilities = _load_json("abilities.json")
ABILITIES: Dict[int, str] = {int(k): v for k, v in _raw_abilities.items()}
ABILITIES_BY_NAME: Dict[str, int] = {v.lower(): k for k, v in ABILITIES.items()}

_raw_charmap = _load_json("charmap.json")
CHARMAP: Dict[int, str] = {int(k): v for k, v in _raw_charmap.items()}
INV_CHARMAP: Dict[str, int] = {v: k for k, v in CHARMAP.items() if v}

CHARMAP[0x00] = " "
CHARMAP[0xFF] = ""
INV_CHARMAP[" "] = 0x00
for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
    INV_CHARMAP[c] = 0xBB + (ord(c) - ord("A"))
for c in "abcdefghijklmnopqrstuvwxyz":
    INV_CHARMAP[c] = 0xD5 + (ord(c) - ord("a"))
for c in "0123456789":
    INV_CHARMAP[c] = 0xA1 + (ord(c) - ord("0"))
INV_CHARMAP["♂"] = 0xB5
INV_CHARMAP["♀"] = 0xB6
INV_CHARMAP["-"] = 0xAE
INV_CHARMAP["!"] = 0xAB
INV_CHARMAP["?"] = 0xAC
INV_CHARMAP["."] = 0xAD
INV_CHARMAP["/"] = 0xBA
INV_CHARMAP[","] = 0xB8

NATURES: List[str] = [
    "Hardy", "Lonely", "Brave", "Adamant", "Naughty",
    "Bold", "Docile", "Relaxed", "Impish", "Lax",
    "Timid", "Hasty", "Serious", "Jolly", "Naive",
    "Modest", "Mild", "Quiet", "Bashful", "Rash",
    "Calm", "Gentle", "Sassy", "Careful", "Quirky"
]

NATURE_STATS: Dict[str, Tuple[str, str]] = {
    "Hardy": ("-", "-"),
    "Lonely": ("+Atk", "-Def"),
    "Brave": ("+Atk", "-Spe"),
    "Adamant": ("+Atk", "-SpA"),
    "Naughty": ("+Atk", "-SpD"),
    "Bold": ("+Def", "-Atk"),
    "Docile": ("-", "-"),
    "Relaxed": ("+Def", "-Spe"),
    "Impish": ("+Def", "-SpA"),
    "Lax": ("+Def", "-SpD"),
    "Timid": ("+Spe", "-Atk"),
    "Hasty": ("+Spe", "-Def"),
    "Serious": ("-", "-"),
    "Jolly": ("+Spe", "-SpA"),
    "Naive": ("+Spe", "-SpD"),
    "Modest": ("+SpA", "-Atk"),
    "Mild": ("+SpA", "-Def"),
    "Quiet": ("+SpA", "-Spe"),
    "Bashful": ("-", "-"),
    "Rash": ("+SpA", "-SpD"),
    "Calm": ("+SpD", "-Atk"),
    "Gentle": ("+SpD", "-Def"),
    "Sassy": ("+SpD", "-Spe"),
    "Careful": ("+SpD", "-SpA"),
    "Quirky": ("-", "-"),
}

TERA_TYPES: List[str] = [
    "None", "Normal", "Fighting", "Flying", "Poison",
    "Ground", "Rock", "Bug", "Ghost", "Steel",
    "Mystery", "Fire", "Water", "Grass", "Electric",
    "Psychic", "Ice", "Dragon", "Dark", "Fairy", "Stellar"
]

POKEBALLS: Dict[int, str] = {
    0: "None",
    1: "Poke Ball",
    2: "Great Ball",
    3: "Ultra Ball",
    4: "Master Ball",
    5: "Premier Ball",
    6: "Heal Ball",
    7: "Net Ball",
    8: "Nest Ball",
    9: "Dive Ball",
    10: "Dusk Ball",
    11: "Timer Ball",
    12: "Quick Ball",
    13: "Repeat Ball",
    14: "Luxury Ball",
    15: "Level Ball",
    16: "Lure Ball",
    17: "Moon Ball",
    18: "Friend Ball",
    19: "Love Ball",
    20: "Fast Ball",
    21: "Heavy Ball",
    22: "Dream Ball",
    23: "Safari Ball",
    24: "Sport Ball",
    25: "Park Ball",
    26: "Beast Ball",
    27: "Cherish Ball"
}

# Sector and Save Block Constants
SECTOR_DATA_SIZE = 3968
SAVE_BLOCK_3_CHUNK_SIZE = 116
SECTOR_FOOTER_SIZE = 12
SECTOR_SIZE = 4096
SECTOR_SIGNATURE = 0x08012025

SB2_SIZE = 2864  # 0xB30
SB1_SIZE = 15444 # 0x3C54

# Offsets inside SaveBlock2
SB2_PLAYER_NAME = 0x00
SB2_PLAYER_GENDER = 0x08
SB2_TRAINER_ID = 0x0A # 2 bytes TID, 2 bytes SID
SB2_PLAY_TIME_HOURS = 0x0E
SB2_PLAY_TIME_MINS = 0x10
SB2_PLAY_TIME_SECS = 0x11
SB2_PLAY_TIME_VBLANKS = 0x12
SB2_ENCRYPTION_KEY = 0xB4 # 4 bytes

# Offsets inside SaveBlock1
SB1_PARTY_COUNT = 0x234
SB1_PARTY = 0x238
SB1_MONEY = 0x478
SB1_COINS = 0x47C
SB1_BAG = 0x548

PARTY_SIZE = 6
MON_SIZE = 96
BOX_MON_SIZE = 76

# PC Storage constants (struct PokemonStorage in Sectors 5-13)
TOTAL_BOXES = 14
BOX_CAPACITY = 30
STORAGE_SECTORS_START = 5
STORAGE_SECTORS_END = 13
STORAGE_TOTAL_SIZE = 35712 # 9 sectors * 3968 bytes
STORAGE_CURRENT_BOX = 0x0000
STORAGE_BOXES_OFFSET = 0x0004 # 14 * 30 * 76 = 31920 bytes
STORAGE_BOX_NAMES_OFFSET = 0x859C # 34204: 14 names * 9 bytes
STORAGE_BOX_WALLPAPERS_OFFSET = 0x8623 # 34339: 14 wallpapers * 1 byte


# Bag pocket offsets relative to SB1_BAG (0x548)
BAG_POCKET_INFO = {
    "Items": {"offset": 0, "count": 150},
    "Medicine": {"offset": 600, "count": 65},
    "KeyItems": {"offset": 860, "count": 50},
    "PokeBalls": {"offset": 1060, "count": 27},
    "TMsHMs": {"offset": 1168, "count": 128},
    "MegaStones": {"offset": 1680, "count": 35},
    "BattleItems": {"offset": 1820, "count": 100},
    "Berries": {"offset": 2220, "count": 70},
}

def decode_gba_string(raw: bytes) -> str:
    res = []
    for b in raw:
        if b == 0xFF:
            break
        res.append(CHARMAP.get(b, f"[{b:02x}]"))
    return "".join(res)

def encode_gba_string(text: str, max_len: int) -> bytes:
    res = bytearray()
    i = 0
    while i < len(text) and len(res) < max_len:
        c = text[i]
        if c == "[" and "]" in text[i:]:
            end = text.find("]", i)
            hex_str = text[i+1:end]
            if len(hex_str) == 2:
                try:
                    res.append(int(hex_str, 16))
                    i = end + 1
                    continue
                except ValueError:
                    pass
        if c in INV_CHARMAP:
            res.append(INV_CHARMAP[c])
        else:
            res.append(0x00)
        i += 1
    if len(res) < max_len:
        res.append(0xFF)
    while len(res) < max_len:
        res.append(0xFF)
    return bytes(res[:max_len])

DEFAULT_GBA_DIR = "/home/josecachy/Downloads/GBA"

KNOWN_SAVE_PATHS = [
    os.path.join(DEFAULT_GBA_DIR, "Soulgold (v1.1.3).sav"),
    os.path.join(DEFAULT_GBA_DIR, "Pokemon Soulgold.sav"),
]

def get_available_saves() -> List[Dict[str, any]]:
    """Scan and return information on save files in the user's GBA directory."""
    results = []
    if not os.path.exists(DEFAULT_GBA_DIR):
        return results
    for fname in sorted(os.listdir(DEFAULT_GBA_DIR)):
        if fname.endswith(".sav"):
            full_p = os.path.join(DEFAULT_GBA_DIR, fname)
            size = os.path.getsize(full_p)
            mtime = os.path.getmtime(full_p)
            label = "SoulGold v1.1.3" if "1.1.3" in fname else ("SoulGold v1.1" if "Soulgold" in fname else "GBA Save")
            results.append({
                "path": full_p,
                "name": fname,
                "size": size,
                "mtime": mtime,
                "label": label
            })
    return results
