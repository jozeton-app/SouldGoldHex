import os
import sys
import unittest
import shutil
import tempfile

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from soulgold_save import SoulGoldSave, Pokemon, calc_sector_checksum
from soulgold_constants import SECTOR_DATA_SIZE, SB2_SIZE, SB1_SIZE

TEST_SAV = "/home/josecachy/Downloads/GBA/Pokemon Soulgold.sav"
TMP_SAV = "/tmp/test_soulgold_suite.sav"

class TestSoulGoldSaveEditor(unittest.TestCase):
    def setUp(self):
        shutil.copy2(TEST_SAV, TMP_SAV)

    def tearDown(self):
        if os.path.exists(TMP_SAV):
            os.remove(TMP_SAV)

    def test_load_and_trainer_info(self):
        sav = SoulGoldSave(TMP_SAV)
        self.assertEqual(sav.get_trainer_name(), "Joze")
        self.assertEqual(sav.get_gender(), "Boy")
        tid, sid = sav.get_trainer_id()
        self.assertEqual(tid, 15327)
        self.assertEqual(sid, 62250)
        self.assertGreater(sav.get_money(), 0)
        self.assertEqual(sav.get_coins(), 0)

    def test_party_decoding(self):
        sav = SoulGoldSave(TMP_SAV)
        party = sav.get_party()
        self.assertEqual(len(party), 6)
        
        # Check Sprigatito
        sprig = party[2]
        self.assertEqual(sprig.species_name, "Sprigatito")
        self.assertEqual(sprig.nickname, "Gatico")
        self.assertGreaterEqual(sprig.level, 5)
        self.assertEqual(sprig.nature, "Impish")
        # Check first party member
        self.assertFalse(party[0].is_shiny)

    def test_shiny_toggle_and_nature_change(self):
        sav = SoulGoldSave(TMP_SAV)
        party = sav.get_party()
        sprig = party[2]

        orig_pid_low = sprig.personality & 0xFF
        sprig.set_shiny(False)
        self.assertFalse(sprig.is_shiny)
        sprig.set_nature("Jolly")
        self.assertEqual(sprig.nature, "Jolly")
        self.assertEqual(sprig.personality % 25, 13) # Jolly is index 13
        self.assertEqual(sprig.personality & 0xFF, orig_pid_low)
        self.assertEqual(sprig.hidden_nature_modifier, 0)

        sav.set_party_mon(2, sprig)
        sav.save(TMP_SAV, make_backup=False)

        # Reload
        sav2 = SoulGoldSave(TMP_SAV)
        sprig2 = sav2.get_party()[2]
        self.assertFalse(sprig2.is_shiny)
        self.assertEqual(sprig2.nature, "Jolly")
        self.assertEqual(sprig2.personality % 25, 13)
        self.assertEqual(sprig2.personality & 0xFF, orig_pid_low)
        self.assertEqual(sprig2.hidden_nature_modifier, 0)

    def test_nature_personality_and_stat_integrity(self):
        from soulgold_constants import NATURES
        sav = SoulGoldSave(TMP_SAV)
        mon = sav.get_party()[0] # Nidoran
        orig_low_byte = mon.personality & 0xFF

        # Test changing through multiple natures
        for target_nat in ["Adamant", "Timid", "Modest", "Careful", "Hardy"]:
            t_idx = NATURES.index(target_nat)
            mon.set_nature(target_nat)
            self.assertEqual(mon.nature, target_nat)
            self.assertEqual(mon.personality % 25, t_idx)
            self.assertEqual(mon.personality & 0xFF, orig_low_byte)
            self.assertEqual(mon.hidden_nature_modifier, 0)

    def test_backup_pruning(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_sav = os.path.join(tmpdir, "test.sav")
            shutil.copyfile(TEST_SAV, test_sav)
            s = SoulGoldSave(test_sav)
            # Make 4 saves with backups
            for i in range(4):
                # Fake slightly different timestamps
                fake_bak = f"{test_sav}.bak_20260914_00000{i}"
                with open(fake_bak, 'w') as f:
                    f.write("fake")
            SoulGoldSave.prune_backups(test_sav, keep=2)
            remaining = [f for f in os.listdir(tmpdir) if f.startswith("test.sav.bak_")]
            self.assertEqual(len(remaining), 2)
            self.assertIn("test.sav.bak_20260914_000002", remaining)
            self.assertIn("test.sav.bak_20260914_000003", remaining)

    def test_money_and_coins_edit(self):
        sav = SoulGoldSave(TMP_SAV)
        sav.set_money(999999)
        sav.set_coins(9999)
        sav.save(TMP_SAV, make_backup=False)

        sav2 = SoulGoldSave(TMP_SAV)
        self.assertEqual(sav2.get_money(), 999999)
        self.assertEqual(sav2.get_coins(), 9999)

    def test_heal_party(self):
        sav = SoulGoldSave(TMP_SAV)
        party = sav.get_party()
        # Hurt mon
        party[0].hp = 1
        sav.set_party(party)
        sav.heal_party()

        for mon in sav.get_party():
            self.assertEqual(mon.hp, mon.max_hp)

    def test_checksum_validity(self):
        sav = SoulGoldSave(TMP_SAV)
        sav.set_money(500000)
        sav.heal_party()
        sav.save(TMP_SAV, make_backup=False)

        # Verify raw sectors checksum
        with open(TMP_SAV, "rb") as f:
            raw = f.read()

        import struct
        expected_sizes = {0: SB2_SIZE, 1: SECTOR_DATA_SIZE, 2: SECTOR_DATA_SIZE, 3: SECTOR_DATA_SIZE, 4: 3540}
        for i in range(14):
            sec_idx = sav.slot_start + i
            sec = raw[sec_idx * 4096 : (sec_idx + 1) * 4096]
            sec_id, chk, sig, counter = struct.unpack("<HHII", sec[0xFF4:])
            exp_sz = expected_sizes.get(sec_id, SECTOR_DATA_SIZE)
            computed = calc_sector_checksum(sec[:exp_sz], exp_sz)
            self.assertEqual(chk, computed, f"Sector {sec_id} checksum mismatch!")

    def test_pc_storage(self):
        sav = SoulGoldSave(TMP_SAV)
        self.assertEqual(sav.get_current_box(), 0)
        sav.set_current_box(2)
        self.assertEqual(sav.get_current_box(), 2)

        # Names & Wallpapers
        names = sav.get_box_names()
        self.assertEqual(len(names), 14)
        sav.set_box_name(0, "MyBox")
        self.assertEqual(sav.get_box_names()[0], "MyBox")

        wallpapers = sav.get_box_wallpapers()
        self.assertEqual(len(wallpapers), 14)
        sav.set_box_wallpaper(0, 7)
        self.assertEqual(sav.get_box_wallpapers()[0], 7)

        # Box Slots
        box0 = sav.get_box(0)
        self.assertEqual(len(box0), 30)

        # Edit slot 0
        m = sav.get_box_mon(0, 0)
        original_species = m.species_id
        m.nickname = "Hero"
        m.set_level(50)
        m.set_shiny(True)
        m.set_nature("Adamant")
        sav.set_box_mon(0, 0, m)

        m_saved = sav.get_box_mon(0, 0)
        self.assertEqual(m_saved.nickname, "Hero")
        self.assertEqual(m_saved.level, 50)
        self.assertTrue(m_saved.is_shiny)
        self.assertEqual(m_saved.nature, "Adamant")

        # Swap slots
        sav.swap_box_slots(0, 0, 0, 1)
        self.assertEqual(sav.get_box_mon(0, 1).nickname, "Hero")

        # Commit and verify checksums
        sav.commit_changes()
        from soulgold_save import get_slot_validity
        valid, counter, msg = get_slot_validity(sav.raw_data, sav.active_slot)
        self.assertTrue(valid, f"Save invalid after storage commit: {msg}")

if __name__ == "__main__":
    unittest.main()
