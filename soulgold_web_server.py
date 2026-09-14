#!/usr/bin/env python3
"""
Pokémon SoulGold Web Save Editor - Local HTTP Backend Server
Serves the web application and handles save parsing, editing, and backup management via REST API.
"""

import os
import sys
import json
import webbrowser
import threading
import urllib.parse
import uuid
from typing import Dict, Any
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

# Add current directory to path
MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(MODULE_DIR)

from soulgold_constants import (
    SPECIES, SPECIES_BY_NAME,
    MOVES, MOVES_BY_NAME,
    ITEMS, ITEMS_BY_NAME,
    ABILITIES, ABILITIES_BY_NAME,
    NATURES, NATURE_STATS,
    TERA_TYPES, POKEBALLS,
    BAG_POCKET_INFO,
    get_available_saves,
    DEFAULT_GBA_DIR
)
from soulgold_save import SoulGoldSave, Pokemon

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True

# Global state & multi-user session storage for cloud hosting
CURRENT_SAVE: SoulGoldSave = None
SESSIONS: Dict[str, SoulGoldSave] = {}

def get_or_load_default_save() -> SoulGoldSave:
    global CURRENT_SAVE
    if CURRENT_SAVE is not None:
        return CURRENT_SAVE
    
    saves = get_available_saves()
    target_path = None
    if saves:
        # Check if v1.1.3 exists and not blank
        v113 = next((s for s in saves if "1.1.3" in s["name"]), None)
        v11 = next((s for s in saves if "Pokemon Soulgold.sav" in s["name"]), None)
        if v113 and not SoulGoldSave(v113["path"]).is_blank_flash:
            target_path = v113["path"]
        elif v11:
            target_path = v11["path"]
        elif v113:
            target_path = v113["path"]
        else:
            target_path = saves[0]["path"]

    if target_path and os.path.exists(target_path):
        CURRENT_SAVE = SoulGoldSave(target_path)
    else:
        CURRENT_SAVE = SoulGoldSave()
    return CURRENT_SAVE

def serialize_mon(mon: Pokemon) -> Dict[str, Any]:
    return {
        "species_id": mon.species_id,
        "species_name": mon.species_name,
        "nickname": mon.nickname,
        "level": mon.level,
        "experience": mon.experience,
        "hp": mon.hp,
        "max_hp": mon.max_hp,
        "attack": mon.attack,
        "defense": mon.defense,
        "speed": mon.speed,
        "sp_attack": mon.sp_attack,
        "sp_defense": mon.sp_defense,
        "is_shiny": mon.is_shiny,
        "nature": mon.nature,
        "held_item_id": mon.held_item,
        "held_item_name": ITEMS.get(mon.held_item, "None"),
        "pokeball_id": mon.pokeball,
        "pokeball_name": POKEBALLS.get(mon.pokeball, "Poke Ball"),
        "tera_type": TERA_TYPES[mon.tera_type] if 0 <= mon.tera_type < len(TERA_TYPES) else "None",
        "tera_type_id": mon.tera_type,
        "personality": mon.personality,
        "moves": [
            {"id": mid, "name": MOVES.get(mid, "None"), "pp": pp}
            for mid, pp in zip(mon.moves, mon.pps)
        ],
        "ivs": {
            "hp": mon.iv_hp, "attack": mon.iv_attack, "defense": mon.iv_defense,
            "speed": mon.iv_speed, "sp_attack": mon.iv_sp_attack, "sp_defense": mon.iv_sp_defense
        },
        "evs": {
            "hp": mon.ev_hp, "attack": mon.ev_attack, "defense": mon.ev_defense,
            "speed": mon.ev_speed, "sp_attack": mon.ev_sp_attack, "sp_defense": mon.ev_sp_defense
        }
    }

def apply_mon_updates(mon: Pokemon, mon_data: dict):
    """Apply updated attributes to a Pokemon instance safely."""
    if "species_name" in mon_data and mon_data["species_name"].lower() in SPECIES_BY_NAME:
        mon.set_species(SPECIES_BY_NAME[mon_data["species_name"].lower()])
    elif "species_id" in mon_data:
        mon.set_species(int(mon_data["species_id"]))

    if "nickname" in mon_data:
        mon.nickname = str(mon_data["nickname"])[:10]
    if "level" in mon_data:
        mon.set_level(int(mon_data["level"]))
    if "is_shiny" in mon_data:
        mon.set_shiny(bool(mon_data["is_shiny"]))
    if "nature" in mon_data and mon_data["nature"] in NATURES:
        mon.set_nature(mon_data["nature"])

    if "tera_type" in mon_data:
        t = mon_data["tera_type"]
        if isinstance(t, int):
            mon.tera_type = max(0, min(31, t))
        elif isinstance(t, str):
            if t in TERA_TYPES:
                mon.tera_type = TERA_TYPES.index(t)
            elif t.isdigit():
                mon.tera_type = max(0, min(31, int(t)))

    if "held_item_name" in mon_data:
        hname = str(mon_data["held_item_name"]).strip().lower()
        if hname in ITEMS_BY_NAME:
            mon.held_item = ITEMS_BY_NAME[hname]
        elif hname in ("", "none", "(none)"):
            mon.held_item = 0
    elif "held_item_id" in mon_data:
        mon.held_item = int(mon_data["held_item_id"])

    if "pokeball_name" in mon_data:
        pname = str(mon_data["pokeball_name"]).strip().lower()
        for pid, pname_val in POKEBALLS.items():
            if pname_val.lower() == pname:
                mon.pokeball = pid
                break
    elif "pokeball_id" in mon_data:
        mon.pokeball = int(mon_data["pokeball_id"])

    if "moves" in mon_data:
        for i, mv in enumerate(mon_data["moves"][:4]):
            if isinstance(mv, dict):
                m_name = mv.get("name", "").strip().lower()
                if m_name in MOVES_BY_NAME:
                    mon.moves[i] = MOVES_BY_NAME[m_name]
                elif m_name in ("", "none", "(none)"):
                    mon.moves[i] = 0
                elif "id" in mv:
                    mon.moves[i] = int(mv["id"])
                if "pp" in mv:
                    mon.pps[i] = max(0, min(99, int(mv["pp"])))

    if "ivs" in mon_data:
        ivs = mon_data["ivs"]
        mon.iv_hp = max(0, min(31, int(ivs.get("hp", mon.iv_hp))))
        mon.iv_attack = max(0, min(31, int(ivs.get("attack", mon.iv_attack))))
        mon.iv_defense = max(0, min(31, int(ivs.get("defense", mon.iv_defense))))
        mon.iv_speed = max(0, min(31, int(ivs.get("speed", mon.iv_speed))))
        mon.iv_sp_attack = max(0, min(31, int(ivs.get("sp_attack", mon.iv_sp_attack))))
        mon.iv_sp_defense = max(0, min(31, int(ivs.get("sp_defense", mon.iv_sp_defense))))

    if "evs" in mon_data:
        evs = mon_data["evs"]
        mon.ev_hp = max(0, min(252, int(evs.get("hp", mon.ev_hp))))
        mon.ev_attack = max(0, min(252, int(evs.get("attack", mon.ev_attack))))
        mon.ev_defense = max(0, min(252, int(evs.get("defense", mon.ev_defense))))
        mon.ev_speed = max(0, min(252, int(evs.get("speed", mon.ev_speed))))
        mon.ev_sp_attack = max(0, min(252, int(evs.get("sp_attack", mon.ev_sp_attack))))
        mon.ev_sp_defense = max(0, min(252, int(evs.get("sp_defense", mon.ev_sp_defense))))

class SoulGoldRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Concise logging
        pass

    def get_session_id(self) -> str:
        cookie_header = self.headers.get("Cookie", "")
        if "soulgold_session=" in cookie_header:
            for part in cookie_header.split(";"):
                part = part.strip()
                if part.startswith("soulgold_session="):
                    return part.split("=", 1)[1].strip()
        custom_header = self.headers.get("X-Session-ID")
        if custom_header:
            return custom_header.strip()
        new_id = uuid.uuid4().hex[:16]
        self._new_session_id = new_id
        return new_id

    def get_current_save(self) -> SoulGoldSave:
        # For localhost with no explicit session header/cookie, share the local active save
        if self.client_address[0] in ("127.0.0.1", "::1") and not self.headers.get("X-Session-ID") and "soulgold_session=" not in self.headers.get("Cookie", ""):
            return get_or_load_default_save()

        sess_id = self.get_session_id()
        if sess_id in SESSIONS:
            return SESSIONS[sess_id]

        default_save = get_or_load_default_save()
        user_save = SoulGoldSave()
        user_save.clone_from(default_save)
        user_save.filepath = default_save.filepath
        SESSIONS[sess_id] = user_save
        return user_save

    def set_current_save(self, save: SoulGoldSave):
        sess_id = self.get_session_id()
        SESSIONS[sess_id] = save
        if self.client_address[0] in ("127.0.0.1", "::1"):
            global CURRENT_SAVE
            CURRENT_SAVE = save

    def send_json(self, data: Any, status: int = 200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        if hasattr(self, "_new_session_id"):
            self.send_header("Set-Cookie", f"soulgold_session={self._new_session_id}; Path=/; SameSite=Lax")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Session-ID")
        self.end_headers()

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query = urllib.parse.parse_qs(parsed_url.query)

        if path == "/" or path == "/index.html":
            html_path = os.path.join(MODULE_DIR, "web", "index.html")
            if os.path.exists(html_path):
                with open(html_path, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                if hasattr(self, "_new_session_id"):
                    self.send_header("Set-Cookie", f"soulgold_session={self._new_session_id}; Path=/; SameSite=Lax")
                self.end_headers()
                self.wfile.write(content)
            else:
                self.send_error(404, "index.html not found")
            return

        if path == "/api/status":
            save = self.get_current_save()
            saves = get_available_saves()
            self.send_json({
                "current_save": {
                    "path": save.filepath,
                    "filename": os.path.basename(save.filepath) if save.filepath else "Untitled",
                    "version": save.detect_version(),
                    "is_blank_flash": save.is_blank_flash,
                },
                "available_saves": saves
            })
            return

        if path == "/api/data":
            save = self.get_current_save()
            h, m, s = save.get_play_time()
            tid, sid = save.get_trainer_id()

            bag_data = {}
            for pocket in BAG_POCKET_INFO.keys():
                raw_items = save.get_bag_pocket(pocket)
                bag_data[pocket] = [
                    {"id": iid, "name": ITEMS.get(iid, f"Item #{iid}"), "qty": qty}
                    for iid, qty in raw_items
                ]

            party_data = [serialize_mon(m) for m in save.get_party()]

            self.send_json({
                "trainer": {
                    "name": save.get_trainer_name(),
                    "gender": save.get_gender(),
                    "tid": tid,
                    "sid": sid,
                    "hours": h,
                    "minutes": m,
                    "seconds": s,
                    "money": save.get_money(),
                    "coins": save.get_coins(),
                },
                "party": party_data,
                "storage": {
                    "current_box": save.get_current_box(),
                    "total_boxes": 14,
                    "box_capacity": 30,
                    "box_names": save.get_box_names(),
                    "box_wallpapers": save.get_box_wallpapers()
                },
                "bag": bag_data,
                "metadata": {
                    "natures": NATURES,
                    "nature_stats": NATURE_STATS,
                    "tera_types": TERA_TYPES,
                    "pokeballs": [{"id": k, "name": v} for k, v in POKEBALLS.items()],
                    "pockets": list(BAG_POCKET_INFO.keys()),
                    "species": [{"id": k, "name": v} for k, v in sorted(SPECIES.items()) if k > 0],
                    "moves": [{"id": k, "name": v} for k, v in sorted(MOVES.items()) if k > 0],
                    "items": [{"id": k, "name": v} for k, v in sorted(ITEMS.items()) if k > 0],
                },
                "version": save.detect_version(),
                "filepath": save.filepath,
                "is_blank_flash": save.is_blank_flash
            })
            return

        if path == "/api/box":
            save = self.get_current_save()
            box_idx = 0
            try:
                box_idx = int(query.get("idx", [0])[0])
            except (ValueError, IndexError):
                box_idx = 0
            box_idx = max(0, min(13, box_idx))
            mons = [serialize_mon(m) for m in save.get_box(box_idx)]
            names = save.get_box_names()
            wallpapers = save.get_box_wallpapers()
            self.send_json({
                "box_index": box_idx,
                "name": names[box_idx] if box_idx < len(names) else f"Box {box_idx+1}",
                "wallpaper": wallpapers[box_idx] if box_idx < len(wallpapers) else 0,
                "pokemon": mons
            })
            return

        if path == "/api/download":
            save = self.get_current_save()
            raw = save.to_bytes()
            filename = os.path.basename(save.filepath) if save.filepath else "Pokemon_SoulGold.sav"

            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.send_header("Content-Length", str(len(raw)))
            if hasattr(self, "_new_session_id"):
                self.send_header("Set-Cookie", f"soulgold_session={self._new_session_id}; Path=/; SameSite=Lax")
            self.end_headers()
            self.wfile.write(raw)
            return

        self.send_error(404, "Endpoint not found")

    def do_POST(self):
        global CURRENT_SAVE
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query = urllib.parse.parse_qs(parsed_url.query)
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else b""

        payload = {}
        if body and self.headers.get("Content-Type", "").startswith("application/json"):
            try:
                payload = json.loads(body.decode("utf-8"))
            except Exception:
                pass

        if path in ("/api/load", "/api/import") and payload.get("path"):
            target_path = payload.get("path")
            if not target_path or not os.path.exists(target_path):
                self.send_json({"error": f"File not found: {target_path}"}, status=400)
                return
            try:
                CURRENT_SAVE = SoulGoldSave(target_path)
                self.send_json({
                    "success": True,
                    "filename": os.path.basename(target_path),
                    "filepath": target_path,
                    "version": CURRENT_SAVE.detect_version(),
                    "is_blank_flash": CURRENT_SAVE.is_blank_flash,
                    "source": "disk"
                })
            except Exception as e:
                self.send_json({"error": str(e)}, status=500)
            return

        if path in ("/api/upload", "/api/import"):
            if not body or len(body) < 131072:
                self.send_json({"error": "Invalid save file size (must be at least 128KB)"}, status=400)
                return

            raw_name = query.get("name", [self.headers.get("X-File-Name", "Imported_Save.sav")])[0]
            orig_name = os.path.basename(raw_name)
            potential_local = os.path.join(DEFAULT_GBA_DIR, orig_name)

            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".sav", delete=False) as f:
                f.write(body)
                tmp_path = f.name
            try:
                CURRENT_SAVE = SoulGoldSave(tmp_path)
                # Keep original filename / default GBA path so user can save back to disk
                CURRENT_SAVE.filepath = potential_local if os.path.exists(DEFAULT_GBA_DIR) else orig_name
                self.send_json({
                    "success": True,
                    "filename": orig_name,
                    "filepath": CURRENT_SAVE.filepath,
                    "version": CURRENT_SAVE.detect_version(),
                    "is_blank_flash": CURRENT_SAVE.is_blank_flash,
                    "source": "upload"
                })
            except Exception as e:
                self.send_json({"error": str(e)}, status=500)
            return

        save = get_or_load_default_save()

        if path == "/api/heal":
            save.heal_party()
            self.send_json({"success": True, "message": "Party fully restored!"})
            return

        if path == "/api/max-ivs":
            save.max_party_ivs()
            self.send_json({"success": True, "message": "All party IVs set to 31!"})
            return

        if path == "/api/max-money":
            save.set_money(999999)
            self.send_json({"success": True, "message": "Money set to ₽999,999!"})
            return

        if path == "/api/max-coins":
            save.set_coins(9999)
            self.send_json({"success": True, "message": "Game Corner coins set to 9,999!"})
            return

        if path == "/api/update-trainer":
            if "name" in payload:
                save.set_trainer_name(payload["name"])
            if "gender" in payload:
                save.set_gender(payload["gender"])
            if "tid" in payload and "sid" in payload:
                save.set_trainer_id(int(payload["tid"]), int(payload["sid"]))
            if "money" in payload:
                save.set_money(int(payload["money"]))
            if "coins" in payload:
                save.set_coins(int(payload["coins"]))
            if "hours" in payload:
                h = int(payload.get("hours", 0))
                m = int(payload.get("minutes", 0))
                s = int(payload.get("seconds", 0))
                save.set_play_time(h, m, s)
            self.send_json({"success": True, "message": "Trainer data updated!"})
            return

        if path == "/api/update-mon":
            slot_idx = int(payload.get("slot", -1))
            save = self.get_current_save()
            party = save.get_party()
            if 0 <= slot_idx < len(party):
                mon = party[slot_idx]
                apply_mon_updates(mon, payload.get("mon", {}))
                save.set_party_mon(slot_idx, mon)

                # Persist to disk if associated with a valid local file
                saved_to_disk = False
                if save.filepath and os.path.isabs(save.filepath) and os.path.exists(save.filepath):
                    try:
                        save.save(save.filepath, make_backup=True, max_backups=2)
                        saved_to_disk = True
                    except Exception as e:
                        print(f"Auto-save warning: {e}")

                self.send_json({
                    "success": True,
                    "message": f"Updated slot {slot_idx+1}: {mon.species_name}" + (" (Saved to disk)" if saved_to_disk else ""),
                    "saved_to_disk": saved_to_disk,
                    "mon": serialize_mon(mon)
                })
            else:
                self.send_json({"error": "Invalid party slot index"}, status=400)
            return

        if path == "/api/update-box-mon":
            box_idx = int(payload.get("box", 0))
            slot_idx = int(payload.get("slot", -1))
            save = self.get_current_save()
            if 0 <= box_idx < 14 and 0 <= slot_idx < 30:
                mon = save.get_box_mon(box_idx, slot_idx)
                apply_mon_updates(mon, payload.get("mon", {}))
                save.set_box_mon(box_idx, slot_idx, mon)

                saved_to_disk = False
                if save.filepath and os.path.isabs(save.filepath) and os.path.exists(save.filepath):
                    try:
                        save.save(save.filepath, make_backup=True, max_backups=2)
                        saved_to_disk = True
                    except Exception as e:
                        print(f"Auto-save warning: {e}")

                self.send_json({
                    "success": True,
                    "message": f"Updated Box {box_idx+1} Slot #{slot_idx+1}: {mon.nickname or mon.species_name}" + (" (Saved to disk)" if saved_to_disk else ""),
                    "saved_to_disk": saved_to_disk,
                    "mon": serialize_mon(mon)
                })
            else:
                self.send_json({"error": "Invalid box or slot index"}, status=400)
            return

        if path == "/api/set-box-name":
            box_idx = int(payload.get("box", 0))
            name = str(payload.get("name", "")).strip()
            save = self.get_current_save()
            if 0 <= box_idx < 14:
                save.set_box_name(box_idx, name)
                if save.filepath and os.path.isabs(save.filepath) and os.path.exists(save.filepath):
                    try:
                        save.save(save.filepath, make_backup=True, max_backups=2)
                    except Exception:
                        pass
                self.send_json({"success": True, "name": save.get_box_names()[box_idx]})
            else:
                self.send_json({"error": "Invalid box index"}, status=400)
            return

        if path == "/api/swap-box-slots":
            b1 = int(payload.get("box1", 0))
            s1 = int(payload.get("slot1", 0))
            b2 = int(payload.get("box2", 0))
            s2 = int(payload.get("slot2", 0))
            save = self.get_current_save()
            if 0 <= b1 < 14 and 0 <= s1 < 30 and 0 <= b2 < 14 and 0 <= s2 < 30:
                save.swap_box_slots(b1, s1, b2, s2)
                if save.filepath and os.path.isabs(save.filepath) and os.path.exists(save.filepath):
                    try:
                        save.save(save.filepath, make_backup=True, max_backups=2)
                    except Exception:
                        pass
                self.send_json({"success": True, "message": "Slots swapped successfully"})
            else:
                self.send_json({"error": "Invalid slot or box indices"}, status=400)
            return

        if path == "/api/update-bag":
            pocket = payload.get("pocket")
            items = payload.get("items", [])
            if pocket in BAG_POCKET_INFO:
                formatted_items = []
                for it in items:
                    iid = int(it.get("id", 0))
                    qty = int(it.get("qty", 1))
                    formatted_items.append((iid, qty))
                save.set_bag_pocket(pocket, formatted_items)
                self.send_json({"success": True, "message": f"Updated pocket '{pocket}'"})
            else:
                self.send_json({"error": "Invalid pocket"}, status=400)
            return

        if path == "/api/clone-to-v113":
            v113_path = os.path.join(DEFAULT_GBA_DIR, "Soulgold (v1.1.3).sav")
            dest_sav = SoulGoldSave(v113_path if os.path.exists(v113_path) else None)
            dest_sav.clone_from(save)
            dest_sav.save(v113_path)
            CURRENT_SAVE = dest_sav
            self.send_json({
                "success": True,
                "message": f"Cloned progress into {os.path.basename(v113_path)}!",
                "filename": os.path.basename(v113_path),
                "version": CURRENT_SAVE.detect_version()
            })
            return

        if path == "/api/save":
            dest_path = payload.get("path") or save.filepath
            if not dest_path:
                self.send_json({"error": "No destination path specified"}, status=400)
                return
            try:
                save.save(dest_path, make_backup=True, max_backups=2)
                self.send_json({
                    "success": True,
                    "message": f"Save file updated successfully! Backup created (max 2 retained).",
                    "filename": os.path.basename(dest_path)
                })
            except Exception as e:
                self.send_json({"error": f"Save failed: {str(e)}"}, status=500)
            return

        self.send_error(404, "Endpoint not found")

def start_server(host: str = None, port: int = None, open_browser: bool = True):
    if port is None:
        port = int(os.environ.get("PORT", 8080))
    if host is None:
        host = os.environ.get("HOST", "0.0.0.0" if "PORT" in os.environ else "127.0.0.1")

    httpd = None
    selected_port = port
    # Dynamically scan from port up to port + 50 to find an available port
    for p in range(port, port + 50):
        try:
            server_address = (host, p)
            httpd = ThreadedHTTPServer(server_address, SoulGoldRequestHandler)
            selected_port = p
            break
        except OSError as e:
            if e.errno in (98, 48):  # Address already in use
                continue
            raise

    if httpd is None:
        raise OSError(f"Could not bind to any available port between {port} and {port + 50}")

    display_host = "localhost" if host in ("0.0.0.0", "127.0.0.1") else host
    url = f"http://{display_host}:{selected_port}"
    print(f"\n" + "=" * 60)
    print(f"  Pokémon SoulGold Save Editor - Web Application")
    print(f"  Running at: {url}")
    print(f"  Press Ctrl+C to stop the server")
    print("=" * 60 + "\n")

    if open_browser and host == "127.0.0.1" and "PORT" not in os.environ:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping web server...")
        httpd.server_close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Pokémon SoulGold Web Save Editor Server")
    parser.add_argument("--port", type=int, default=None, help="Port to listen on (default: $PORT or 8080)")
    parser.add_argument("--host", type=str, default=None, help="Host to bind to (default: $HOST, 0.0.0.0 if in cloud, else 127.0.0.1)")
    parser.add_argument("--no-browser", action="store_true", help="Do not open web browser automatically")
    args = parser.parse_args()

    start_server(host=args.host, port=args.port, open_browser=not args.no_browser)

