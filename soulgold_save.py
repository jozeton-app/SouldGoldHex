import struct
import shutil
import datetime
import os
from typing import List, Dict, Tuple, Optional
from soulgold_constants import (
    SECTOR_SIZE, SECTOR_DATA_SIZE, SECTOR_SIGNATURE,
    SB2_SIZE, SB1_SIZE, PARTY_SIZE, MON_SIZE, BOX_MON_SIZE,
    TOTAL_BOXES, BOX_CAPACITY,
    STORAGE_SECTORS_START, STORAGE_SECTORS_END, STORAGE_TOTAL_SIZE,
    STORAGE_CURRENT_BOX, STORAGE_BOXES_OFFSET,
    STORAGE_BOX_NAMES_OFFSET, STORAGE_BOX_WALLPAPERS_OFFSET,
    SB2_PLAYER_NAME, SB2_PLAYER_GENDER, SB2_TRAINER_ID,
    SB2_PLAY_TIME_HOURS, SB2_PLAY_TIME_MINS, SB2_PLAY_TIME_SECS, SB2_PLAY_TIME_VBLANKS,
    SB2_ENCRYPTION_KEY,
    SB1_PARTY_COUNT, SB1_PARTY, SB1_MONEY, SB1_COINS, SB1_BAG,
    BAG_POCKET_INFO,
    SPECIES, SPECIES_BY_NAME,
    MOVES, MOVES_BY_NAME,
    ITEMS, ITEMS_BY_NAME,
    NATURES, NATURE_STATS, TERA_TYPES, POKEBALLS,
    decode_gba_string, encode_gba_string
)

EXPECTED_SECTOR_SIZES = {0: SB2_SIZE, 1: SECTOR_DATA_SIZE, 2: SECTOR_DATA_SIZE, 3: SECTOR_DATA_SIZE, 4: 3540}
for i in range(5, 14):
    EXPECTED_SECTOR_SIZES[i] = SECTOR_DATA_SIZE

def calc_sector_checksum(data: bytes, size: int) -> int:
    chk = 0
    num_dwords = size // 4
    for i in range(num_dwords):
        val = struct.unpack_from('<I', data, i * 4)[0]
        chk = (chk + val) & 0xFFFFFFFF
    return ((chk >> 16) + chk) & 0xFFFF

def get_shiny_value(ot_id: int, personality: int) -> int:
    return (ot_id & 0xFFFF) ^ (ot_id >> 16) ^ (personality & 0xFFFF) ^ (personality >> 16)

class Pokemon:
    def __init__(self, raw: bytes = None):
        if raw is not None and len(raw) >= MON_SIZE:
            self.unpack(raw[:MON_SIZE])
        else:
            self.init_empty()

    def init_empty(self):
        self.personality = 0
        self.ot_id = 0
        self.nickname = ""
        self.ot_name = ""
        self.language = 2 # English
        self.hidden_nature_modifier = 0
        self.is_bad_egg = False
        self.has_species = False
        self.is_egg = False
        self.block_box_rs = False
        self.days_since_form_change = 0
        self.markings = 0
        self.compressed_status = 0
        self.hp_lost = 0
        self.shiny_modifier = 0
        self.modern_fateful_encounter = 0

        # Secure Data
        self.species = 0
        self.tera_type = 0
        self.held_item = 0
        self.pokeball = 1
        self.experience = 0
        self.held_item2 = 0
        self.met_loc_hi0 = 0
        self.pp_bonuses = 0
        self.friendship = 70
        self.moves = [0, 0, 0, 0]
        self.evos = [0, 0]
        self.met_hi1_5 = 0
        self.met_hi6 = 0
        self.ability_num = 0
        self.ht_hp = 0
        self.ht_atk = 0
        self.pps = [0, 0, 0, 0]
        self.ht_defs = [0, 0, 0, 0]
        self.evs = [0, 0, 0, 0, 0, 0] # HP, Atk, Def, Spe, SpA, SpD
        self.conditions = [0, 0, 0, 0, 0, 0]
        self.pokerus = 0
        self.met_location = 0
        self.met_level = 5
        self.met_game = 0
        self.ot_gender = 0
        self.ivs = [0, 0, 0, 0, 0, 0] # HP, Atk, Def, Spe, SpA, SpD
        self.gigantamax = 0

        # Party Data
        self.status = 0
        self.level = 1
        self.mail = 0
        self.hp = 10
        self.max_hp = 10
        self.attack = 5
        self.defense = 5
        self.speed = 5
        self.sp_attack = 5
        self.sp_defense = 5

    def unpack(self, b: bytes):
        self.personality, self.ot_id = struct.unpack('<II', b[0:8])
        self.nickname = decode_gba_string(b[8:20])
        
        b20 = b[20]
        self.language = b20 & 0x7
        self.hidden_nature_modifier = (b20 >> 3) & 0x1F

        b21 = b[21]
        self.is_bad_egg = bool(b21 & 0x1)
        self.has_species = bool(b21 & 0x2)
        self.is_egg = bool(b21 & 0x4)
        self.block_box_rs = bool(b21 & 0x8)
        self.days_since_form_change = (b21 >> 4) & 0x7

        self.ot_name = decode_gba_string(b[22:29])
        
        b29 = b[29]
        self.markings = b29 & 0xF
        self.compressed_status = (b29 >> 4) & 0xF

        w30 = struct.unpack('<H', b[30:32])[0]
        self.hp_lost = w30 & 0x3FFF
        self.shiny_modifier = (w30 >> 14) & 0x1
        self.modern_fateful_encounter = (w30 >> 15) & 0x1

        # Secure data b[32:76]
        sec = b[32:76]
        w0 = struct.unpack('<H', sec[0:2])[0]
        self.species = w0 & 0x7FF
        self.tera_type = (w0 >> 11) & 0x1F

        w1 = struct.unpack('<H', sec[2:4])[0]
        self.held_item = w1 & 0x3FF
        self.pokeball = (w1 >> 10) & 0x3F

        d4 = struct.unpack('<I', sec[4:8])[0]
        self.experience = d4 & 0xFFFFFF

        w8 = struct.unpack('<H', sec[8:10])[0]
        self.held_item2 = w8 & 0x3FF
        self.met_loc_hi0 = (w8 >> 10) & 0x1

        self.pp_bonuses = sec[10]
        self.friendship = sec[11]

        m0, m1, m2, m3 = struct.unpack('<HHHH', sec[12:20])
        self.moves = [
            m0 & 0x7FF,
            m1 & 0x7FF,
            m2 & 0x7FF,
            m3 & 0x7FF
        ]
        self.evos = [(m0 >> 11) & 0x1F, (m1 >> 11) & 0x1F]
        self.met_hi1_5 = (m2 >> 11) & 0x1F
        self.met_hi6 = (m3 >> 11) & 0x1
        self.ability_num = (m3 >> 12) & 0x3
        self.ht_hp = (m3 >> 14) & 0x1
        self.ht_atk = (m3 >> 15) & 0x1

        self.pps = [
            sec[20] & 0x7F,
            sec[21] & 0x7F,
            sec[22] & 0x7F,
            sec[23] & 0x7F
        ]
        self.ht_defs = [
            (sec[20] >> 7) & 0x1,
            (sec[21] >> 7) & 0x1,
            (sec[22] >> 7) & 0x1,
            (sec[23] >> 7) & 0x1
        ]

        self.evs = list(sec[24:30]) # hp, atk, def, spd, spatk, spdef
        self.conditions = list(sec[30:36])
        self.pokerus = sec[36]
        self.met_location = sec[37]

        w_met = struct.unpack('<H', sec[38:40])[0]
        self.met_level = w_met & 0x7F
        self.met_game = (w_met >> 7) & 0xF
        self.ot_gender = (w_met >> 11) & 0x1

        iv_word = struct.unpack('<I', sec[40:44])[0]
        self.ivs = [
            iv_word & 0x1F,
            (iv_word >> 5) & 0x1F,
            (iv_word >> 10) & 0x1F,
            (iv_word >> 15) & 0x1F,
            (iv_word >> 20) & 0x1F,
            (iv_word >> 25) & 0x1F
        ]
        self.is_egg = bool((iv_word >> 30) & 0x1)
        self.gigantamax = (iv_word >> 31) & 0x1

        # Party stats b[76:96]
        if len(b) >= 96:
            self.status = struct.unpack('<I', b[76:80])[0]
            self.level = b[80]
            self.mail = b[81]
            self.hp, self.max_hp, self.attack, self.defense, self.speed, self.sp_attack, self.sp_defense = struct.unpack(
                '<HHHHHHH', b[82:96]
            )

        # For Box Pokemon or uncalculated level: deduce from experience / met_level
        if self.level == 0 and self.species > 0:
            if self.experience > 0:
                lvl = int(self.experience ** (1.0 / 3.0) + 1e-6)
                self.level = max(1, min(100, max(lvl, self.met_level if self.met_level > 0 else 1)))
            elif self.met_level > 0:
                self.level = max(1, min(100, self.met_level))
            else:
                self.level = 5

    def set_level(self, lvl: int):
        self.level = max(1, min(100, int(lvl)))
        # Keep experience in sync with level so withdrawing into party respects level
        self.experience = self.level ** 3



    def pack(self) -> bytes:
        res = bytearray(MON_SIZE)
        struct.pack_into('<II', res, 0, self.personality, self.ot_id)
        res[8:20] = encode_gba_string(self.nickname, 12)
        
        b20 = (self.language & 0x7) | ((self.hidden_nature_modifier & 0x1F) << 3)
        res[20] = b20

        b21 = (1 if self.is_bad_egg else 0) | \
              ((1 if self.has_species else 0) << 1) | \
              ((1 if self.is_egg else 0) << 2) | \
              ((1 if self.block_box_rs else 0) << 3) | \
              ((self.days_since_form_change & 0x7) << 4)
        res[21] = b21

        res[22:29] = encode_gba_string(self.ot_name, 7)

        b29 = (self.markings & 0xF) | ((self.compressed_status & 0xF) << 4)
        res[29] = b29

        w30 = (self.hp_lost & 0x3FFF) | ((self.shiny_modifier & 0x1) << 14) | ((self.modern_fateful_encounter & 0x1) << 15)
        struct.pack_into('<H', res, 30, w30)

        # Pack secure data into res[32:76]
        w0 = (self.species & 0x7FF) | ((self.tera_type & 0x1F) << 11)
        w1 = (self.held_item & 0x3FF) | ((self.pokeball & 0x3F) << 10)
        struct.pack_into('<HH', res, 32, w0, w1)

        struct.pack_into('<I', res, 36, self.experience & 0xFFFFFF)
        
        w8 = (self.held_item2 & 0x3FF) | ((self.met_loc_hi0 & 0x1) << 10)
        struct.pack_into('<H', res, 40, w8)

        res[42] = self.pp_bonuses
        res[43] = self.friendship

        m0 = (self.moves[0] & 0x7FF) | ((self.evos[0] & 0x1F) << 11)
        m1 = (self.moves[1] & 0x7FF) | ((self.evos[1] & 0x1F) << 11)
        m2 = (self.moves[2] & 0x7FF) | ((self.met_hi1_5 & 0x1F) << 11)
        m3 = (self.moves[3] & 0x7FF) | ((self.met_hi6 & 0x1) << 11) | ((self.ability_num & 0x3) << 12) | \
             ((self.ht_hp & 0x1) << 14) | ((self.ht_atk & 0x1) << 15)
        struct.pack_into('<HHHH', res, 44, m0, m1, m2, m3)

        for i in range(4):
            res[52 + i] = (self.pps[i] & 0x7F) | ((self.ht_defs[i] & 0x1) << 7)

        res[56:62] = bytes(self.evs)
        res[62:68] = bytes(self.conditions)
        res[68] = self.pokerus
        res[69] = self.met_location

        w_met = (self.met_level & 0x7F) | ((self.met_game & 0xF) << 7) | ((self.ot_gender & 0x1) << 11)
        struct.pack_into('<H', res, 70, w_met)

        iv_val = (self.ivs[0] & 0x1F) | \
                 ((self.ivs[1] & 0x1F) << 5) | \
                 ((self.ivs[2] & 0x1F) << 10) | \
                 ((self.ivs[3] & 0x1F) << 15) | \
                 ((self.ivs[4] & 0x1F) << 20) | \
                 ((self.ivs[5] & 0x1F) << 25) | \
                 ((1 if self.is_egg else 0) << 30) | \
                 ((self.gigantamax & 0x1) << 31)
        struct.pack_into('<I', res, 72, iv_val)

        # Party stats
        struct.pack_into('<I', res, 76, self.status)
        res[80] = self.level
        res[81] = self.mail
        struct.pack_into(
            '<HHHHHHH', res, 82,
            self.hp, self.max_hp, self.attack, self.defense, self.speed, self.sp_attack, self.sp_defense
        )

        return bytes(res)

    @property
    def species_name(self) -> str:
        return SPECIES.get(self.species, f"Unknown ({self.species})")

    @property
    def is_shiny(self) -> bool:
        nat_shiny = (get_shiny_value(self.ot_id, self.personality) < 8)
        return bool(nat_shiny ^ (self.shiny_modifier & 1))

    def set_shiny(self, shiny: bool):
        nat_shiny = (get_shiny_value(self.ot_id, self.personality) < 8)
        self.shiny_modifier = 1 if (nat_shiny != shiny) else 0

    @property
    def nature(self) -> str:
        base_nature = (self.personality % 25)
        effective = base_nature ^ self.hidden_nature_modifier
        if 0 <= effective < len(NATURES):
            return NATURES[effective]
        return NATURES[base_nature]

    def set_nature(self, nature_name: str):
        if nature_name not in NATURES:
            return
        target_idx = NATURES.index(nature_name)
        curr_idx = self.personality % 25
        if curr_idx != target_idx:
            # 1. Update personality such that (new_personality % 25) == target_idx
            # Preserving (personality & 0xFF) so gender and low-byte traits never change.
            # 256 mod 25 is 6. The modular inverse of 6 mod 25 is 21 (since 6 * 21 = 126 = 5 * 25 + 1).
            diff = (target_idx - curr_idx) % 25
            k = (21 * diff) % 25
            new_personality = self.personality + k * 256
            if new_personality > 0xFFFFFFFF:
                new_personality = self.personality - (25 - k) * 256
            if new_personality < 0:
                new_personality = self.personality + (k + 25) * 256

            was_shiny = self.is_shiny
            self.personality = new_personality & 0xFFFFFFFF
            self.set_shiny(was_shiny)

            # 2. Adjust party stats for the nature shift
            self._adjust_stats_for_nature(curr_idx, target_idx)

        # 3. Clear hidden_nature_modifier so base nature and mint nature are in sync
        self.hidden_nature_modifier = 0

    def _adjust_stats_for_nature(self, old_idx: int, new_idx: int):
        if old_idx == new_idx:
            return
        old_up, old_down = NATURE_STATS.get(NATURES[old_idx], ("-", "-"))
        new_up, new_down = NATURE_STATS.get(NATURES[new_idx], ("-", "-"))

        stat_map = {
            "Atk": "attack",
            "Def": "defense",
            "Spe": "speed",
            "SpA": "sp_attack",
            "SpD": "sp_defense",
        }

        for stat_code, attr in stat_map.items():
            val = getattr(self, attr, 0)
            if val <= 0:
                continue
            # Reverse old nature modifier
            if f"+{stat_code}" == old_up:
                raw_val = round(val / 1.1)
            elif f"-{stat_code}" == old_down:
                raw_val = round(val / 0.9)
            else:
                raw_val = val

            # Apply new nature modifier
            if f"+{stat_code}" == new_up:
                new_val = int(raw_val * 110 // 100)
            elif f"-{stat_code}" == new_down:
                new_val = int(raw_val * 90 // 100)
            else:
                new_val = raw_val

            setattr(self, attr, max(1, min(65535, new_val)))

    def heal(self):
        self.hp = self.max_hp
        self.status = 0
        self.hp_lost = 0
        for i in range(4):
            if self.moves[i] != 0 and self.pps[i] == 0:
                self.pps[i] = 20

    def max_ivs(self):
        self.ivs = [31, 31, 31, 31, 31, 31]

    @property
    def species_id(self) -> int:
        return self.species

    @species_id.setter
    def species_id(self, val: int):
        self.species = int(val)
        self.has_species = (self.species != 0)

    def set_species(self, val: int):
        self.species = int(val)
        self.has_species = (self.species != 0)

    # IV property helpers
    @property
    def iv_hp(self) -> int: return self.ivs[0]
    @iv_hp.setter
    def iv_hp(self, v: int): self.ivs[0] = max(0, min(31, int(v)))

    @property
    def iv_attack(self) -> int: return self.ivs[1]
    @iv_attack.setter
    def iv_attack(self, v: int): self.ivs[1] = max(0, min(31, int(v)))

    @property
    def iv_defense(self) -> int: return self.ivs[2]
    @iv_defense.setter
    def iv_defense(self, v: int): self.ivs[2] = max(0, min(31, int(v)))

    @property
    def iv_speed(self) -> int: return self.ivs[3]
    @iv_speed.setter
    def iv_speed(self, v: int): self.ivs[3] = max(0, min(31, int(v)))

    @property
    def iv_sp_attack(self) -> int: return self.ivs[4]
    @iv_sp_attack.setter
    def iv_sp_attack(self, v: int): self.ivs[4] = max(0, min(31, int(v)))

    @property
    def iv_sp_defense(self) -> int: return self.ivs[5]
    @iv_sp_defense.setter
    def iv_sp_defense(self, v: int): self.ivs[5] = max(0, min(31, int(v)))

    # EV property helpers
    @property
    def ev_hp(self) -> int: return self.evs[0]
    @ev_hp.setter
    def ev_hp(self, v: int): self.evs[0] = max(0, min(252, int(v)))

    @property
    def ev_attack(self) -> int: return self.evs[1]
    @ev_attack.setter
    def ev_attack(self, v: int): self.evs[1] = max(0, min(252, int(v)))

    @property
    def ev_defense(self) -> int: return self.evs[2]
    @ev_defense.setter
    def ev_defense(self, v: int): self.evs[2] = max(0, min(252, int(v)))

    @property
    def ev_speed(self) -> int: return self.evs[3]
    @ev_speed.setter
    def ev_speed(self, v: int): self.evs[3] = max(0, min(252, int(v)))

    @property
    def ev_sp_attack(self) -> int: return self.evs[4]
    @ev_sp_attack.setter
    def ev_sp_attack(self, v: int): self.evs[4] = max(0, min(252, int(v)))

    @property
    def ev_sp_defense(self) -> int: return self.evs[5]
    @ev_sp_defense.setter
    def ev_sp_defense(self, v: int): self.evs[5] = max(0, min(252, int(v)))

def get_slot_validity(raw: bytes, slot_id: int) -> Tuple[bool, int, str]:
    slot_offset = 14 * slot_id
    save_counter = None
    counters_match = True
    valid_sectors = 0
    sig_valid = False

    for i in range(14):
        sec = raw[(slot_offset + i) * SECTOR_SIZE : (slot_offset + i + 1) * SECTOR_SIZE]
        sec_id, chk, sig, counter = struct.unpack('<HHII', sec[0xFF4:])
        if sig == SECTOR_SIGNATURE:
            sig_valid = True
            if sec_id < 14:
                exp_size = EXPECTED_SECTOR_SIZES[sec_id]
                calc_chk = calc_sector_checksum(sec[:exp_size], exp_size)
                if chk == calc_chk:
                    if save_counter is None:
                        save_counter = counter
                    elif save_counter != counter:
                        counters_match = False
                    valid_sectors |= (1 << sec_id)
    if not sig_valid:
        return False, 0, "EMPTY"
    if valid_sectors != (1 << 14) - 1 or not counters_match:
        return False, save_counter or 0, "SECTOR_CHECKSUM_OR_COUNTER_MISMATCH"

    # Overflow sector (30 for slot 0, 31 for slot 1)
    o_sec_id = 30 + slot_id
    o_sec = raw[o_sec_id * SECTOR_SIZE : (o_sec_id + 1) * SECTOR_SIZE]
    o_id, o_chk, o_sig, o_counter = struct.unpack('<HHII', o_sec[0xFF4:])
    if o_counter != save_counter:
        return False, save_counter, f"OVERFLOW_COUNTER_MISMATCH_{o_counter}_VS_{save_counter}"

    # Aux sector (28 for slot 0, 29 for slot 1)
    a_sec_id = 28 + slot_id
    a_sec = raw[a_sec_id * SECTOR_SIZE : (a_sec_id + 1) * SECTOR_SIZE]
    a_id, a_chk, a_sig, a_counter = struct.unpack('<HHII', a_sec[0xFF4:])
    if a_counter != save_counter:
        return False, save_counter, f"AUX_COUNTER_MISMATCH_{a_counter}_VS_{save_counter}"

    if (save_counter % 2) != slot_id:
        return False, save_counter, f"PARITY_MISMATCH_{save_counter}_VS_{slot_id}"

    return True, save_counter, "OK"

class SoulGoldSave:
    def __init__(self, filepath: str = None):
        self.filepath = filepath
        self.raw_data: bytearray = bytearray()
        self.extra_bytes: bytes = b""
        self.active_slot: int = 0
        self.save_counter: int = 0
        self.sb2_data: bytearray = bytearray(SB2_SIZE)
        self.sb1_data: bytearray = bytearray(SB1_SIZE)
        self.storage_data: bytearray = bytearray(STORAGE_TOTAL_SIZE)
        self.sector_map: Dict[int, Tuple[int, bytearray]] = {} # sec_id -> (phys_idx, bytearray)
        self.is_blank_flash: bool = False
        if filepath:
            self.load(filepath)

    def load(self, filepath: str):
        self.filepath = filepath
        with open(filepath, 'rb') as f:
            content = f.read()

        if len(content) >= 131072:
            self.raw_data = bytearray(content[:131072])
            self.extra_bytes = content[131072:]
        else:
            raise ValueError(f"Invalid save file size: {len(content)} bytes (expected at least 131072)")

        # Check if entire save is unformatted flash (all 0xFF)
        if set(self.raw_data[:4096]) == {255} or set(self.raw_data) == {255}:
            self.is_blank_flash = True
        else:
            self.is_blank_flash = False

        # Validate both slots and determine active slot
        s0_ok, c0, msg0 = get_slot_validity(self.raw_data, 0)
        s1_ok, c1, msg1 = get_slot_validity(self.raw_data, 1)

        if s0_ok and s1_ok:
            self.active_slot = 1 if c1 > c0 else 0
            self.save_counter = max(c0, c1)
        elif s1_ok:
            self.active_slot = 1
            self.save_counter = c1
        elif s0_ok:
            self.active_slot = 0
            self.save_counter = c0
        else:
            if msg0 == "EMPTY" and msg1 == "EMPTY":
                self.is_blank_flash = True
            # Fallback by highest counter
            c0_raw = struct.unpack_from('<I', self.raw_data, 0 * SECTOR_SIZE + 0xFFC)[0]
            c1_raw = struct.unpack_from('<I', self.raw_data, 14 * SECTOR_SIZE + 0xFFC)[0]
            self.active_slot = 1 if c1_raw > c0_raw else 0
            self.save_counter = max(c0_raw, c1_raw)

        # Read the 14 sectors belonging to active slot
        slot_offset = 14 * self.active_slot
        self.sector_map = {}
        for i in range(14):
            phys_idx = slot_offset + i
            sec = bytearray(self.raw_data[phys_idx * SECTOR_SIZE : (phys_idx + 1) * SECTOR_SIZE])
            sec_id = struct.unpack_from('<H', sec, 0xFF4)[0]
            self.sector_map[sec_id] = (phys_idx, sec)

        # Extract SaveBlock2 (Sector ID 0)
        if 0 in self.sector_map:
            self.sb2_data = bytearray(self.sector_map[0][1][:SB2_SIZE])

        # Extract SaveBlock1 (Sector IDs 1 to 4)
        sb1_chunks = []
        for sid in range(1, 5):
            if sid in self.sector_map:
                sb1_chunks.append(self.sector_map[sid][1][:SECTOR_DATA_SIZE])
            else:
                sb1_chunks.append(bytearray(SECTOR_DATA_SIZE))
        self.sb1_data = bytearray(b"".join(sb1_chunks)[:SB1_SIZE])

        # Extract PokemonStorage (Sector IDs 5 to 13)
        storage_chunks = []
        for sid in range(STORAGE_SECTORS_START, STORAGE_SECTORS_END + 1):
            if sid in self.sector_map:
                storage_chunks.append(self.sector_map[sid][1][:SECTOR_DATA_SIZE])
            else:
                storage_chunks.append(bytearray(SECTOR_DATA_SIZE))
        self.storage_data = bytearray(b"".join(storage_chunks)[:STORAGE_TOTAL_SIZE])

    def clone_from(self, source: "SoulGoldSave"):
        """Clone all save state, sectors, and metadata from another SoulGoldSave."""
        self.raw_data = bytearray(source.raw_data)
        self.extra_bytes = bytes(source.extra_bytes)
        self.active_slot = source.active_slot
        self.save_counter = source.save_counter
        self.sb2_data = bytearray(source.sb2_data)
        self.sb1_data = bytearray(source.sb1_data)
        self.storage_data = bytearray(source.storage_data)
        self.sector_map = {}
        for sec_id, (phys_idx, sec) in source.sector_map.items():
            self.sector_map[sec_id] = (phys_idx, bytearray(sec))
        self.is_blank_flash = False

    def detect_version(self) -> str:
        """Return inferred ROM / Hack version label."""
        if self.filepath:
            lower = self.filepath.lower()
            if "1.1.3" in lower:
                return "SoulGold v1.1.3"
            elif "soulgold" in lower:
                return "SoulGold v1.1"
        return "SoulGold"

    @property
    def slot_start(self) -> int:
        return 14 * self.active_slot

    @property
    def encryption_key(self) -> int:
        return struct.unpack_from('<I', self.sb2_data, SB2_ENCRYPTION_KEY)[0]

    @encryption_key.setter
    def encryption_key(self, val: int):
        struct.pack_into('<I', self.sb2_data, SB2_ENCRYPTION_KEY, val & 0xFFFFFFFF)

    # --- Trainer Info ---
    def get_trainer_name(self) -> str:
        return decode_gba_string(self.sb2_data[SB2_PLAYER_NAME : SB2_PLAYER_NAME + 8])

    def set_trainer_name(self, name: str):
        self.sb2_data[SB2_PLAYER_NAME : SB2_PLAYER_NAME + 8] = encode_gba_string(name, 8)

    def get_gender(self) -> str:
        return "Girl" if self.sb2_data[SB2_PLAYER_GENDER] == 1 else "Boy"

    def set_gender(self, gender: str):
        self.sb2_data[SB2_PLAYER_GENDER] = 1 if gender.lower().startswith("g") else 0

    def get_trainer_id(self) -> Tuple[int, int]:
        tid, sid = struct.unpack_from('<HH', self.sb2_data, SB2_TRAINER_ID)
        return tid, sid

    def set_trainer_id(self, tid: int, sid: int):
        struct.pack_into('<HH', self.sb2_data, SB2_TRAINER_ID, tid & 0xFFFF, sid & 0xFFFF)

    def get_play_time(self) -> Tuple[int, int, int]:
        h = struct.unpack_from('<H', self.sb2_data, SB2_PLAY_TIME_HOURS)[0]
        m = self.sb2_data[SB2_PLAY_TIME_MINS]
        s = self.sb2_data[SB2_PLAY_TIME_SECS]
        return h, m, s

    def set_play_time(self, h: int, m: int, s: int):
        struct.pack_into('<H', self.sb2_data, SB2_PLAY_TIME_HOURS, h & 0xFFFF)
        self.sb2_data[SB2_PLAY_TIME_MINS] = m % 60
        self.sb2_data[SB2_PLAY_TIME_SECS] = s % 60

    # --- Money & Coins ---
    def get_money(self) -> int:
        raw = struct.unpack_from('<I', self.sb1_data, SB1_MONEY)[0]
        return (raw ^ self.encryption_key) & 0xFFFFFFFF

    def set_money(self, amount: int):
        amount = max(0, min(999999, amount))
        raw = amount ^ self.encryption_key
        struct.pack_into('<I', self.sb1_data, SB1_MONEY, raw & 0xFFFFFFFF)

    def get_coins(self) -> int:
        raw = struct.unpack_from('<H', self.sb1_data, SB1_COINS)[0]
        return (raw ^ (self.encryption_key & 0xFFFF)) & 0xFFFF

    def set_coins(self, amount: int):
        amount = max(0, min(9999, amount))
        raw = amount ^ (self.encryption_key & 0xFFFF)
        struct.pack_into('<H', self.sb1_data, SB1_COINS, raw & 0xFFFF)

    # --- Party Pokemon ---
    def get_party(self) -> List[Pokemon]:
        count = self.sb1_data[SB1_PARTY_COUNT]
        count = min(count, PARTY_SIZE)
        party = []
        for i in range(count):
            start = SB1_PARTY + i * MON_SIZE
            raw = bytes(self.sb1_data[start : start + MON_SIZE])
            mon = Pokemon(raw)
            party.append(mon)
        return party

    def set_party(self, party: List[Pokemon]):
        count = min(len(party), PARTY_SIZE)
        self.sb1_data[SB1_PARTY_COUNT] = count
        for i in range(count):
            start = SB1_PARTY + i * MON_SIZE
            self.sb1_data[start : start + MON_SIZE] = party[i].pack()

    def set_party_mon(self, index: int, mon: Pokemon):
        if 0 <= index < PARTY_SIZE:
            start = SB1_PARTY + index * MON_SIZE
            self.sb1_data[start : start + MON_SIZE] = mon.pack()

    def heal_party(self):
        party = self.get_party()
        for mon in party:
            mon.heal()
        self.set_party(party)

    def max_party_ivs(self):
        party = self.get_party()
        for mon in party:
            mon.max_ivs()
        self.set_party(party)

    # --- Bag & Inventory ---
    def get_bag_pocket(self, pocket_name: str) -> List[Tuple[int, int]]:
        info = BAG_POCKET_INFO.get(pocket_name)
        if not info:
            return []
        base = SB1_BAG + info["offset"]
        count = info["count"]
        items = []
        enc_hword = self.encryption_key & 0xFFFF
        for i in range(count):
            item_id, enc_qty = struct.unpack_from('<HH', self.sb1_data, base + i * 4)
            if item_id != 0:
                qty = (enc_qty ^ enc_hword) & 0xFFFF
                items.append((item_id, qty))
        return items

    def set_bag_pocket(self, pocket_name: str, items: List[Tuple[int, int]]):
        info = BAG_POCKET_INFO.get(pocket_name)
        if not info:
            return
        base = SB1_BAG + info["offset"]
        capacity = info["count"]
        enc_hword = self.encryption_key & 0xFFFF
        for i in range(capacity):
            pos = base + i * 4
            if i < len(items):
                item_id, qty = items[i]
                enc_qty = (qty ^ enc_hword) & 0xFFFF
                struct.pack_into('<HH', self.sb1_data, pos, item_id & 0xFFFF, enc_qty)
            else:
                struct.pack_into('<HH', self.sb1_data, pos, 0, 0)
    # --- PC Storage System ---
    def get_current_box(self) -> int:
        if len(self.storage_data) > STORAGE_CURRENT_BOX:
            return int(self.storage_data[STORAGE_CURRENT_BOX])
        return 0

    def set_current_box(self, box_idx: int):
        if 0 <= box_idx < TOTAL_BOXES:
            self.storage_data[STORAGE_CURRENT_BOX] = int(box_idx)

    def get_box_names(self) -> List[str]:
        names = []
        for b in range(TOTAL_BOXES):
            off = STORAGE_BOX_NAMES_OFFSET + b * 9
            raw = self.storage_data[off : off + 9]
            names.append(decode_gba_string(raw))
        return names

    def set_box_name(self, box_idx: int, name: str):
        if 0 <= box_idx < TOTAL_BOXES:
            off = STORAGE_BOX_NAMES_OFFSET + box_idx * 9
            self.storage_data[off : off + 9] = encode_gba_string(name[:8], 9)

    def get_box_wallpapers(self) -> List[int]:
        wallpapers = []
        for b in range(TOTAL_BOXES):
            off = STORAGE_BOX_WALLPAPERS_OFFSET + b
            wallpapers.append(int(self.storage_data[off]) if off < len(self.storage_data) else 0)
        return wallpapers

    def set_box_wallpaper(self, box_idx: int, wallpaper_idx: int):
        if 0 <= box_idx < TOTAL_BOXES:
            off = STORAGE_BOX_WALLPAPERS_OFFSET + box_idx
            if off < len(self.storage_data):
                self.storage_data[off] = int(wallpaper_idx) & 0xFF

    def _get_box_offset(self, box_idx: int, slot_idx: int) -> int:
        return STORAGE_BOXES_OFFSET + (box_idx * BOX_CAPACITY + slot_idx) * BOX_MON_SIZE

    def get_box_mon(self, box_idx: int, slot_idx: int) -> Pokemon:
        if not (0 <= box_idx < TOTAL_BOXES and 0 <= slot_idx < BOX_CAPACITY):
            raise IndexError(f"Box index {box_idx} or slot {slot_idx} out of range")
        off = self._get_box_offset(box_idx, slot_idx)
        raw_box = self.storage_data[off : off + BOX_MON_SIZE]
        # Pad with 20 zeroes (stats) so Pokemon can unpack safely
        return Pokemon(bytes(raw_box) + b'\x00' * 20)

    def set_box_mon(self, box_idx: int, slot_idx: int, mon: Pokemon):
        if not (0 <= box_idx < TOTAL_BOXES and 0 <= slot_idx < BOX_CAPACITY):
            raise IndexError(f"Box index {box_idx} or slot {slot_idx} out of range")
        off = self._get_box_offset(box_idx, slot_idx)
        if mon.species == 0:
            self.storage_data[off : off + BOX_MON_SIZE] = b'\x00' * BOX_MON_SIZE
        else:
            packed = mon.pack()[:BOX_MON_SIZE]
            self.storage_data[off : off + BOX_MON_SIZE] = packed

    def get_box(self, box_idx: int) -> List[Pokemon]:
        if not (0 <= box_idx < TOTAL_BOXES):
            raise IndexError(f"Box index {box_idx} out of range (0-{TOTAL_BOXES-1})")
        return [self.get_box_mon(box_idx, s) for s in range(BOX_CAPACITY)]

    def swap_box_slots(self, box1: int, slot1: int, box2: int, slot2: int):
        m1 = self.get_box_mon(box1, slot1)
        m2 = self.get_box_mon(box2, slot2)
        self.set_box_mon(box1, slot1, m2)
        self.set_box_mon(box2, slot2, m1)

    # --- Save & Checksum Recalculation ---
    @staticmethod
    def prune_backups(dest_path: str, keep: int = 2):
        """Keep only the `keep` most recent timestamped backup files for dest_path."""
        if keep < 0:
            return
        dir_name = os.path.dirname(os.path.abspath(dest_path))
        base_name = os.path.basename(dest_path)
        pattern_prefix = f"{base_name}.bak_"
        try:
            if not os.path.exists(dir_name):
                return
            backups = []
            for fname in os.listdir(dir_name):
                if fname.startswith(pattern_prefix):
                    full_p = os.path.join(dir_name, fname)
                    if os.path.isfile(full_p):
                        backups.append(full_p)
            # Timestamp format %Y%m%d_%H%M%S sorts lexicographically in chronological order
            backups.sort()
            while len(backups) > keep:
                oldest = backups.pop(0)
                try:
                    os.remove(oldest)
                except OSError:
                    pass
        except OSError:
            pass

    def commit_changes(self):
        """Sync SB2 and SB1 into raw_data sectors and update all sector checksums."""
        # Write SB2 into Sector 0
        if 0 in self.sector_map:
            self.sector_map[0][1][:SB2_SIZE] = self.sb2_data

        # Write SB1 chunks into Sectors 1-4
        for sid in range(1, 5):
            chunk_start = (sid - 1) * SECTOR_DATA_SIZE
            chunk_end = min(chunk_start + SECTOR_DATA_SIZE, len(self.sb1_data))
            chunk = self.sb1_data[chunk_start:chunk_end]
            if sid in self.sector_map:
                self.sector_map[sid][1][:len(chunk)] = chunk

        # Write PokemonStorage chunks into Sectors 5-13
        for sid in range(STORAGE_SECTORS_START, STORAGE_SECTORS_END + 1):
            chunk_start = (sid - STORAGE_SECTORS_START) * SECTOR_DATA_SIZE
            chunk_end = min(chunk_start + SECTOR_DATA_SIZE, len(self.storage_data))
            chunk = self.storage_data[chunk_start:chunk_end]
            if sid in self.sector_map:
                self.sector_map[sid][1][:len(chunk)] = chunk


        # Update and re-checksum all 14 sectors in the active slot
        for sec_id, (phys_idx, sec_data) in self.sector_map.items():
            size = EXPECTED_SECTOR_SIZES.get(sec_id, SECTOR_DATA_SIZE)
            chk = calc_sector_checksum(bytes(sec_data[:size]), size)

            # Footer: sec_id (u16), checksum (u16), signature (u32), counter (u32)
            struct.pack_into('<HHII', sec_data, 0xFF4, sec_id, chk, SECTOR_SIGNATURE, self.save_counter)
            self.raw_data[phys_idx * SECTOR_SIZE : (phys_idx + 1) * SECTOR_SIZE] = sec_data

        # Synchronize auxiliary sector (Box 19 / Hall of Fame) & overflow sector counters
        aux_phys = 28 + self.active_slot
        over_phys = 30 + self.active_slot
        struct.pack_into('<I', self.raw_data, aux_phys * SECTOR_SIZE + 0xFFC, self.save_counter)
        struct.pack_into('<I', self.raw_data, over_phys * SECTOR_SIZE + 0xFFC, self.save_counter)

        # Pre-save validation: Ensure game engine validator accepts the save!
        ok, counter, msg = get_slot_validity(self.raw_data, self.active_slot)
        if not ok:
            raise RuntimeError(f"Internal save validation failed for active slot {self.active_slot}: {msg}")

    def to_bytes(self) -> bytes:
        """Commit all pending memory changes and return the complete valid .sav byte buffer."""
        self.commit_changes()
        return bytes(self.raw_data) + bytes(self.extra_bytes)

    def save(self, filepath: str = None, make_backup: bool = True, max_backups: int = 2):
        dest_path = filepath or self.filepath
        if not dest_path:
            raise ValueError("No destination filepath specified")

        # Create timestamped backup if file exists and requested
        if make_backup and os.path.exists(dest_path):
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            bak_path = f"{dest_path}.bak_{timestamp}"
            shutil.copy2(dest_path, bak_path)
            if max_backups is not None and max_backups > 0:
                self.prune_backups(dest_path, keep=max_backups)

        data = self.to_bytes()

        # Write safely to disk
        with open(dest_path, 'wb') as f:
            f.write(data)
