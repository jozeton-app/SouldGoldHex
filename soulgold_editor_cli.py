#!/usr/bin/env python3
import argparse
import sys
import os
import json
from soulgold_constants import SPECIES, ITEMS, MOVES, NATURES
from soulgold_save import SoulGoldSave

def print_summary(sav: SoulGoldSave):
    print("=" * 60)
    print("         POKÉMON SOULGOLD SAVE SUMMARY")
    print("=" * 60)
    print(f"File:         {sav.filepath}")
    print(f"Trainer Name: {sav.get_trainer_name()} ({sav.get_gender()})")
    tid, sid = sav.get_trainer_id()
    print(f"Trainer ID:   TID={tid:05d}, SID={sid:05d}")
    h, m, s = sav.get_play_time()
    print(f"Play Time:    {h}h {m:02d}m {s:02d}s")
    print(f"Money:        ₽{sav.get_money():,}")
    print(f"Coins:        {sav.get_coins():,} Coins")
    print(f"Save Counter: {sav.save_counter} (Active Slot: {'1' if sav.slot_start == 0 else '2'})")
    print("-" * 60)
    print("PARTY POKÉMON:")
    party = sav.get_party()
    for idx, mon in enumerate(party):
        shiny_tag = " ★ [SHINY]" if mon.is_shiny else ""
        held_name = f" @ {ITEMS.get(mon.held_item, 'None')}" if mon.held_item else ""
        print(f"  [{idx + 1}] {mon.species_name}{shiny_tag}{held_name}")
        print(f"      Nick: \"{mon.nickname}\" | Level {mon.level} | Nature: {mon.nature}")
        print(f"      HP: {mon.hp}/{mon.max_hp} | Status: {mon.status}")
        move_strs = []
        for m_id, pp in zip(mon.moves, mon.pps):
            if m_id:
                move_strs.append(f"{MOVES.get(m_id, f'Move {m_id}')} ({pp} PP)")
        print(f"      Moves: {', '.join(move_strs) if move_strs else 'None'}")
        print(f"      IVs: HP={mon.ivs[0]}, Atk={mon.ivs[1]}, Def={mon.ivs[2]}, Spe={mon.ivs[3]}, SpA={mon.ivs[4]}, SpD={mon.ivs[5]}")
        print(f"      EVs: HP={mon.evs[0]}, Atk={mon.evs[1]}, Def={mon.evs[2]}, Spe={mon.evs[3]}, SpA={mon.evs[4]}, SpD={mon.evs[5]}")
    print("-" * 60)
    print("BAG HIGHLIGHTS:")
    for pocket in ["Medicine", "PokeBalls", "KeyItems", "Items"]:
        items = sav.get_bag_pocket(pocket)
        if items:
            item_strs = [f"{ITEMS.get(item_id, item_id)} x{qty}" for item_id, qty in items[:6]]
            etc = f" (+{len(items) - 6} more)" if len(items) > 6 else ""
            print(f"  {pocket:<10}: {', '.join(item_strs)}{etc}")
    print("=" * 60)

def main():
    parser = argparse.ArgumentParser(description="Pokémon SoulGold GBA Save Editor CLI")
    parser.add_argument("save_file", nargs="?", default="/home/josecachy/Downloads/GBA/Pokemon Soulgold.sav",
                        help="Path to Pokemon Soulgold .sav file")
    parser.add_argument("--summary", "-s", action="store_true", help="Print save file summary")
    parser.add_argument("--money", "-m", type=int, help="Set money amount (0 - 999999)")
    parser.add_argument("--coins", "-c", type=int, help="Set game corner coins (0 - 9999)")
    parser.add_argument("--heal", action="store_true", help="Fully heal party HP, restore PP, and clear status")
    parser.add_argument("--max-ivs", action="store_true", help="Set all IVs to 31 for entire party")
    parser.add_argument("--shiny", type=int, choices=range(1, 7), metavar="SLOT", help="Toggle shiny for party mon slot (1-6)")
    parser.add_argument("--output", "-o", help="Output save file path (defaults to overwriting input with backup)")
    parser.add_argument("--no-backup", action="store_true", help="Do not create a timestamped .bak backup")
    parser.add_argument("--clone-to-v113", action="store_true", help="Clone active save data into Soulgold (v1.1.3).sav")

    args = parser.parse_args()

    if not os.path.exists(args.save_file):
        print(f"Error: Save file '{args.save_file}' not found!", file=sys.stderr)
        sys.exit(1)

    sav = SoulGoldSave(args.save_file)
    modified = False

    if args.money is not None:
        sav.set_money(args.money)
        print(f"Money updated to ₽{sav.get_money():,}")
        modified = True

    if args.coins is not None:
        sav.set_coins(args.coins)
        print(f"Coins updated to {sav.get_coins():,}")
        modified = True

    if args.heal:
        sav.heal_party()
        print("Party fully healed!")
        modified = True

    if args.max_ivs:
        sav.max_party_ivs()
        print("All party Pokémon IVs set to 31!")
        modified = True

    if args.shiny is not None:
        party = sav.get_party()
        slot_idx = args.shiny - 1
        if slot_idx < len(party):
            mon = party[slot_idx]
            new_shiny = not mon.is_shiny
            mon.set_shiny(new_shiny)
            sav.set_party_mon(slot_idx, mon)
            status_str = "SHINY" if new_shiny else "NORMAL"
            print(f"Slot {args.shiny} ({mon.species_name}) is now {status_str}!")
            modified = True
        else:
            print(f"Warning: Party slot {args.shiny} is empty!", file=sys.stderr)

    if args.clone_to_v113:
        v113_path = "/home/josecachy/Downloads/GBA/Soulgold (v1.1.3).sav"
        v113_sav = SoulGoldSave(v113_path if os.path.exists(v113_path) else None)
        v113_sav.clone_from(sav)
        v113_sav.save(v113_path, make_backup=not args.no_backup, max_backups=2)
        print(f"Successfully cloned progress into: {v113_path}")
        print_summary(v113_sav)
        return

    if modified:
        out_path = args.output or args.save_file
        sav.save(out_path, make_backup=not args.no_backup)
        print(f"Successfully saved to '{out_path}'")

    if args.summary or not modified:
        print_summary(sav)

if __name__ == "__main__":
    main()
