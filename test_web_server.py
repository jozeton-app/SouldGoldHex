#!/usr/bin/env python3
import os
import sys
import unittest
import threading
import urllib.request
import json
import time

MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(MODULE_DIR)

import soulgold_web_server
from soulgold_save import SoulGoldSave

TEST_PORT = 8089

class TestSoulGoldWebServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Start server in daemon thread
        cls.server_thread = threading.Thread(
            target=soulgold_web_server.start_server,
            kwargs={"port": TEST_PORT, "open_browser": False},
            daemon=True
        )
        cls.server_thread.start()
        time.sleep(0.5)

    def test_01_index_html(self):
        url = f"http://127.0.0.1:{TEST_PORT}/"
        req = urllib.request.urlopen(url)
        self.assertEqual(req.status, 200)
        content = req.read().decode("utf-8")
        self.assertIn("Pokémon SoulGold Save Editor", content)

    def test_02_api_status(self):
        url = f"http://127.0.0.1:{TEST_PORT}/api/status"
        req = urllib.request.urlopen(url)
        self.assertEqual(req.status, 200)
        data = json.loads(req.read().decode("utf-8"))
        self.assertIn("current_save", data)
        self.assertIn("available_saves", data)

    def test_03_api_data(self):
        url = f"http://127.0.0.1:{TEST_PORT}/api/data"
        req = urllib.request.urlopen(url)
        self.assertEqual(req.status, 200)
        data = json.loads(req.read().decode("utf-8"))
        self.assertIn("trainer", data)
        self.assertIn("party", data)
        self.assertIn("metadata", data)
        self.assertEqual(len(data["party"]), 6)

    def test_04_api_heal(self):
        url = f"http://127.0.0.1:{TEST_PORT}/api/heal"
        req = urllib.request.Request(url, data=b"{}", headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req)
        self.assertEqual(resp.status, 200)
        data = json.loads(resp.read().decode("utf-8"))
        self.assertTrue(data.get("success"))

    def test_05_api_download(self):
        url = f"http://127.0.0.1:{TEST_PORT}/api/download"
        req = urllib.request.urlopen(url)
        self.assertEqual(req.status, 200)
        raw = req.read()
        self.assertGreaterEqual(len(raw), 131072)

    def test_06_api_import_upload(self):
        url = f"http://127.0.0.1:{TEST_PORT}/api/upload?name=CustomTest.sav"
        with open("/home/josecachy/Downloads/GBA/Pokemon Soulgold.sav", "rb") as f:
            file_bytes = f.read()
        req = urllib.request.Request(url, data=file_bytes, headers={"Content-Type": "application/octet-stream"})
        resp = urllib.request.urlopen(req)
        self.assertEqual(resp.status, 200)
        data = json.loads(resp.read().decode("utf-8"))
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("filename"), "CustomTest.sav")

    def test_07_api_import_path(self):
        url = f"http://127.0.0.1:{TEST_PORT}/api/import"
        body = json.dumps({"path": "/home/josecachy/Downloads/GBA/Soulgold (v1.1.3).sav"}).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req)
        self.assertEqual(resp.status, 200)
        data = json.loads(resp.read().decode("utf-8"))
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("filename"), "Soulgold (v1.1.3).sav")

    def test_08_api_update_mon(self):
        url = f"http://127.0.0.1:{TEST_PORT}/api/update-mon"
        mon_payload = {
            "slot": 1,
            "mon": {
                "species_name": "Pidgeotto",
                "nickname": "Birdy",
                "level": 18,
                "is_shiny": True,
                "nature": "Jolly",
                "tera_type": "Flying",
                "held_item_name": "Oran Berry",
                "pokeball_name": "Ultra Ball",
                "moves": [
                    {"name": "Gust", "pp": 35},
                    {"name": "Quick Attack", "pp": 30},
                    {"name": "Wing Attack", "pp": 35},
                    {"name": "(None)", "pp": 0}
                ],
                "ivs": {"hp": 31, "attack": 31, "defense": 31, "speed": 31, "sp_attack": 31, "sp_defense": 31},
                "evs": {"hp": 6, "attack": 252, "defense": 0, "speed": 252, "sp_attack": 0, "sp_defense": 0}
            }
        }
        body = json.dumps(mon_payload).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
        resp = urllib.request.urlopen(req)
        self.assertEqual(resp.status, 200)
        data = json.loads(resp.read().decode("utf-8"))
        self.assertTrue(data.get("success"))
        self.assertIn("Pidgeotto", data.get("message"))

        # Verify via /api/data
        data_url = f"http://127.0.0.1:{TEST_PORT}/api/data"
        data_resp = urllib.request.urlopen(data_url)
        all_data = json.loads(data_resp.read().decode("utf-8"))
        updated_mon = all_data["party"][1]
        self.assertEqual(updated_mon["species_name"], "Pidgeotto")
        self.assertEqual(updated_mon["nickname"], "Birdy")
        self.assertEqual(updated_mon["level"], 18)
        self.assertTrue(updated_mon["is_shiny"])
        self.assertEqual(updated_mon["nature"], "Jolly")
        self.assertEqual(updated_mon["tera_type"], "Flying")
        self.assertEqual(updated_mon["held_item_name"], "Oran Berry")
        self.assertEqual(updated_mon["pokeball_name"], "Ultra Ball")
        self.assertEqual(updated_mon["ivs"]["speed"], 31)
        self.assertEqual(updated_mon["evs"]["attack"], 252)

    def test_09_api_box_storage(self):
        # 1. GET /api/box?idx=0
        url = f"http://127.0.0.1:{TEST_PORT}/api/box?idx=0"
        resp = urllib.request.urlopen(url)
        self.assertEqual(resp.status, 200)
        box_data = json.loads(resp.read().decode("utf-8"))
        self.assertEqual(box_data["box_index"], 0)
        self.assertEqual(len(box_data["pokemon"]), 30)

        # 2. POST /api/update-box-mon
        up_url = f"http://127.0.0.1:{TEST_PORT}/api/update-box-mon"
        payload = {
            "box": 0,
            "slot": 0,
            "mon": {
                "species_name": "Nidoran♂",
                "nickname": "TestBoxMon",
                "level": 30,
                "is_shiny": True,
                "nature": "Adamant"
            }
        }
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(up_url, data=body, headers={"Content-Type": "application/json"}, method="POST")
        up_resp = urllib.request.urlopen(req)
        self.assertEqual(up_resp.status, 200)
        up_res = json.loads(up_resp.read().decode("utf-8"))
        self.assertTrue(up_res.get("success"))

        # 3. Verify box mon updated
        resp2 = urllib.request.urlopen(url)
        box2 = json.loads(resp2.read().decode("utf-8"))
        m0 = box2["pokemon"][0]
        self.assertEqual(m0["nickname"], "TestBoxMon")
        self.assertEqual(m0["level"], 30)
        self.assertTrue(m0["is_shiny"])
        self.assertEqual(m0["nature"], "Adamant")

        # 4. POST /api/set-box-name
        rename_url = f"http://127.0.0.1:{TEST_PORT}/api/set-box-name"
        ren_body = json.dumps({"box": 0, "name": "Favorite"}).encode("utf-8")
        ren_req = urllib.request.Request(rename_url, data=ren_body, headers={"Content-Type": "application/json"}, method="POST")
        ren_resp = urllib.request.urlopen(ren_req)
        self.assertEqual(ren_resp.status, 200)
        ren_res = json.loads(ren_resp.read().decode("utf-8"))
        self.assertEqual(ren_res.get("name"), "Favorite")

        # 5. POST /api/swap-box-slots
        swap_url = f"http://127.0.0.1:{TEST_PORT}/api/swap-box-slots"
        swap_body = json.dumps({"box1": 0, "slot1": 0, "box2": 0, "slot2": 1}).encode("utf-8")
        swap_req = urllib.request.Request(swap_url, data=swap_body, headers={"Content-Type": "application/json"}, method="POST")
        swap_resp = urllib.request.urlopen(swap_req)
        self.assertEqual(swap_resp.status, 200)
        swap_res = json.loads(swap_resp.read().decode("utf-8"))
        self.assertTrue(swap_res.get("success"))

    def test_10_api_reset_save(self):
        # 1. Upload a 128KB dummy save
        dummy_save = bytearray(131072)
        upload_url = f"http://127.0.0.1:{TEST_PORT}/api/upload?name=temporary_imported.sav"
        req = urllib.request.Request(upload_url, data=dummy_save, headers={"Content-Type": "application/octet-stream"}, method="POST")
        resp = urllib.request.urlopen(req)
        self.assertEqual(resp.status, 200)
        upload_data = json.loads(resp.read().decode("utf-8"))
        self.assertEqual(upload_data.get("filename"), "temporary_imported.sav")

        # 2. Reset back to default
        reset_url = f"http://127.0.0.1:{TEST_PORT}/api/reset"
        reset_req = urllib.request.Request(reset_url, data=b"{}", headers={"Content-Type": "application/json"}, method="POST")
        reset_resp = urllib.request.urlopen(reset_req)
        self.assertEqual(reset_resp.status, 200)
        reset_data = json.loads(reset_resp.read().decode("utf-8"))
        self.assertTrue(reset_data.get("success"))
        self.assertIn("Reset to default", reset_data.get("message"))

        # 3. Status should show default save again
        status_url = f"http://127.0.0.1:{TEST_PORT}/api/status"
        status_resp = urllib.request.urlopen(status_url)
        status_data = json.loads(status_resp.read().decode("utf-8"))
        self.assertNotEqual(status_data["current_save"]["filename"], "temporary_imported.sav")

if __name__ == "__main__":
    unittest.main()

