#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import sys

# Ensure local imports work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from soulgold_constants import (
    SPECIES, SPECIES_BY_NAME,
    MOVES, MOVES_BY_NAME,
    ITEMS, ITEMS_BY_NAME,
    NATURES, NATURE_STATS,
    TERA_TYPES, POKEBALLS,
    BAG_POCKET_INFO,
    get_available_saves
)
from soulgold_save import SoulGoldSave, Pokemon

class AutocompleteCombobox(ttk.Combobox):
    def set_completion_list(self, completion_list):
        self._completion_list = sorted(completion_list, key=lambda s: s.lower())
        self._hits = []
        self._hit_index = 0
        self.position = 0
        self.bind('<KeyRelease>', self.handle_keyrelease)
        self['values'] = self._completion_list

    def autocomplete(self, delta=0):
        if delta:
            self._hit_index = (self._hit_index + delta) % len(self._hits)
        else:
            self.position = len(self.get())
            _hits = []
            for element in self._completion_list:
                if element.lower().startswith(self.get().lower()):
                    _hits.append(element)
            if not _hits:
                for element in self._completion_list:
                    if self.get().lower() in element.lower():
                        _hits.append(element)
            self._hits = _hits
            self._hit_index = 0
        if self._hits:
            self.delete(0, tk.END)
            self.insert(0, self._hits[self._hit_index])
            self.select_range(self.position, tk.END)

    def handle_keyrelease(self, event):
        if event.keysym in ('BackSpace', 'Left', 'Right', 'Up', 'Down', 'Return', 'Escape', 'Tab'):
            return
        self.autocomplete()

class SoulGoldEditorApp(tk.Tk):
    def __init__(self, default_save_path=None):
        super().__init__()
        self.title("Pokémon SoulGold GBA - Save Editor")
        self.geometry("960x720")
        self.minsize(860, 640)

        # Style
        self.style = ttk.Style(self)
        if "clam" in self.style.theme_names():
            self.style.theme_use("clam")

        self.tree_font_size = 11
        self.update_tree_style()

        self.sav: Optional[SoulGoldSave] = None
        self.current_party: list[Pokemon] = []
        self.selected_mon_idx: int = 0

        self.create_menu()
        self.create_widgets()

        # Keyboard shortcuts for zoom
        self.bind("<Control-plus>", self.zoom_in_tree)
        self.bind("<Control-equal>", self.zoom_in_tree)
        self.bind("<Control-minus>", self.zoom_out_tree)
        self.bind("<Control-0>", self.zoom_reset_tree)

        # Save detection
        self.available_saves = get_available_saves()
        target_save = default_save_path
        if not target_save and self.available_saves:
            # Prefer v1.1.3 if present and not blank, otherwise v1.1
            v113 = next((s for s in self.available_saves if "1.1.3" in s["name"]), None)
            v11 = next((s for s in self.available_saves if "Pokemon Soulgold.sav" in s["name"]), None)
            if v113 and not SoulGoldSave(v113["path"]).is_blank_flash:
                target_save = v113["path"]
            elif v11:
                target_save = v11["path"]
            elif v113:
                target_save = v113["path"]
            else:
                target_save = self.available_saves[0]["path"]

        if target_save and os.path.exists(target_save):
            self.load_save_file(target_save)

    def create_menu(self):
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=False)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Import / Open Save...", command=self.on_open_file, accelerator="Ctrl+O")
        file_menu.add_command(label="Save", command=self.on_save_file, accelerator="Ctrl+S")
        file_menu.add_command(label="Save As...", command=self.on_save_as)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit)

        tools_menu = tk.Menu(menubar, tearoff=False)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Full Heal Party", command=self.on_heal_party)
        tools_menu.add_command(label="Max Party IVs (All 31s)", command=self.on_max_party_ivs)
        tools_menu.add_command(label="Max Money (₽999,999)", command=lambda: self.set_money_val(999999))
        tools_menu.add_command(label="Max Coins (9,999)", command=lambda: self.set_coins_val(9999))
        tools_menu.add_separator()
        tools_menu.add_command(label="Clone / Migrate Save to v1.1.3", command=self.on_clone_to_v113)

        help_menu = tk.Menu(menubar, tearoff=False)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.on_about)

        self.bind("<Control-o>", lambda e: self.on_open_file())
        self.bind("<Control-s>", lambda e: self.on_save_file())

    def create_widgets(self):
        # Top banner with file path & quick switcher
        top_frame = ttk.Frame(self, padding=8)
        top_frame.pack(fill=tk.X)

        ttk.Label(top_frame, text="Active Save:").pack(side=tk.LEFT, padx=(0, 5))
        self.file_label = ttk.Label(top_frame, text="No save file loaded", font=("Sans", 9, "bold"))
        self.file_label.pack(side=tk.LEFT, padx=(0, 10))

        self.version_badge = ttk.Label(top_frame, text="", font=("Sans", 8, "italic"))
        self.version_badge.pack(side=tk.LEFT, padx=(0, 15))

        # Quick Switch dropdown
        saves = get_available_saves()
        if saves:
            ttk.Label(top_frame, text="Switch:").pack(side=tk.LEFT, padx=(0, 4))
            self.save_switch_cb = ttk.Combobox(top_frame, state="readonly", width=26)
            self.save_switch_cb['values'] = [f"{s['label']}: {s['name']}" for s in saves]
            self.save_switch_cb.pack(side=tk.LEFT, padx=(0, 10))
            self.save_switch_cb.bind("<<ComboboxSelected>>", self.on_switch_save)

        ttk.Button(top_frame, text="Import Save...", command=self.on_open_file).pack(side=tk.RIGHT, padx=4)
        ttk.Button(top_frame, text="Save Changes", command=self.on_save_file).pack(side=tk.RIGHT, padx=4)

        # Main notebook tabs
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        # Tab 1: Trainer
        self.trainer_tab = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(self.trainer_tab, text=" Trainer ")
        self.build_trainer_tab()

        # Tab 2: Party
        self.party_tab = ttk.Frame(self.notebook, padding=8)
        self.notebook.add(self.party_tab, text=" Party Pokémon ")
        self.build_party_tab()

        # Tab 3: Bag
        self.bag_tab = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(self.bag_tab, text=" Bag & Inventory ")
        self.build_bag_tab()

        # Status Bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(self, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W, padding=4)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)

    # ------------------ TRAINER TAB ------------------
    def build_trainer_tab(self):
        container = ttk.Frame(self.trainer_tab)
        container.pack(fill=tk.BOTH, expand=True)

        # Info Box
        info_lf = ttk.LabelFrame(container, text=" Trainer Information ", padding=12)
        info_lf.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        ttk.Label(info_lf, text="Trainer Name:").grid(row=0, column=0, sticky=tk.W, pady=4)
        self.trainer_name_var = tk.StringVar()
        ttk.Entry(info_lf, textvariable=self.trainer_name_var, width=15).grid(row=0, column=1, sticky=tk.W, pady=4)

        ttk.Label(info_lf, text="Gender:").grid(row=1, column=0, sticky=tk.W, pady=4)
        self.gender_var = tk.StringVar(value="Boy")
        gender_f = ttk.Frame(info_lf)
        gender_f.grid(row=1, column=1, sticky=tk.W, pady=4)
        ttk.Radiobutton(gender_f, text="Boy", variable=self.gender_var, value="Boy").pack(side=tk.LEFT, padx=(0, 8))
        ttk.Radiobutton(gender_f, text="Girl", variable=self.gender_var, value="Girl").pack(side=tk.LEFT)

        ttk.Label(info_lf, text="Trainer ID (TID):").grid(row=2, column=0, sticky=tk.W, pady=4)
        self.tid_var = tk.IntVar()
        ttk.Spinbox(info_lf, from_=0, to=65535, textvariable=self.tid_var, width=10).grid(row=2, column=1, sticky=tk.W, pady=4)

        ttk.Label(info_lf, text="Secret ID (SID):").grid(row=3, column=0, sticky=tk.W, pady=4)
        self.sid_var = tk.IntVar()
        ttk.Spinbox(info_lf, from_=0, to=65535, textvariable=self.sid_var, width=10).grid(row=3, column=1, sticky=tk.W, pady=4)

        ttk.Label(info_lf, text="Play Time (H:M:S):").grid(row=4, column=0, sticky=tk.W, pady=4)
        time_f = ttk.Frame(info_lf)
        time_f.grid(row=4, column=1, sticky=tk.W, pady=4)
        self.hours_var = tk.IntVar()
        self.mins_var = tk.IntVar()
        self.secs_var = tk.IntVar()
        ttk.Spinbox(time_f, from_=0, to=999, textvariable=self.hours_var, width=5).pack(side=tk.LEFT)
        ttk.Label(time_f, text="h ").pack(side=tk.LEFT)
        ttk.Spinbox(time_f, from_=0, to=59, textvariable=self.mins_var, width=3).pack(side=tk.LEFT)
        ttk.Label(time_f, text="m ").pack(side=tk.LEFT)
        ttk.Spinbox(time_f, from_=0, to=59, textvariable=self.secs_var, width=3).pack(side=tk.LEFT)
        ttk.Label(time_f, text="s").pack(side=tk.LEFT)

        # Money & Currency
        curr_lf = ttk.LabelFrame(container, text=" Finances & Coins ", padding=12)
        curr_lf.grid(row=0, column=1, sticky="nsew", padx=8, pady=8)

        ttk.Label(curr_lf, text="Money (₽):").grid(row=0, column=0, sticky=tk.W, pady=6)
        self.money_var = tk.IntVar()
        money_e = ttk.Entry(curr_lf, textvariable=self.money_var, width=12)
        money_e.grid(row=0, column=1, sticky=tk.W, pady=6, padx=(0, 6))

        money_btn_f = ttk.Frame(curr_lf)
        money_btn_f.grid(row=0, column=2, sticky=tk.W)
        ttk.Button(money_btn_f, text="+₽50,000", command=lambda: self.add_money(50000)).pack(side=tk.LEFT, padx=2)
        ttk.Button(money_btn_f, text="Max (₽999,999)", command=lambda: self.set_money_val(999999)).pack(side=tk.LEFT, padx=2)

        ttk.Label(curr_lf, text="Game Corner Coins:").grid(row=1, column=0, sticky=tk.W, pady=6)
        self.coins_var = tk.IntVar()
        coins_e = ttk.Entry(curr_lf, textvariable=self.coins_var, width=12)
        coins_e.grid(row=1, column=1, sticky=tk.W, pady=6, padx=(0, 6))

        coins_btn_f = ttk.Frame(curr_lf)
        coins_btn_f.grid(row=1, column=2, sticky=tk.W)
        ttk.Button(coins_btn_f, text="+1,000", command=lambda: self.add_coins(1000)).pack(side=tk.LEFT, padx=2)
        ttk.Button(coins_btn_f, text="Max (9,999)", command=lambda: self.set_coins_val(9999)).pack(side=tk.LEFT, padx=2)

        # Quick Actions
        actions_lf = ttk.LabelFrame(container, text=" Quick One-Click Actions ", padding=12)
        actions_lf.grid(row=1, column=0, columnspan=2, sticky="ew", padx=8, pady=12)

        ttk.Button(actions_lf, text="💖 Fully Heal Entire Party (HP & PP)", command=self.on_heal_party).pack(side=tk.LEFT, padx=6)
        ttk.Button(actions_lf, text="⭐ Perfect Party IVs (All 31s)", command=self.on_max_party_ivs).pack(side=tk.LEFT, padx=6)
        ttk.Button(actions_lf, text="🎒 Max Money & Coins", command=self.on_max_finances).pack(side=tk.LEFT, padx=6)

    def add_money(self, delta):
        val = min(999999, max(0, self.money_var.get() + delta))
        self.money_var.set(val)

    def set_money_val(self, val):
        self.money_var.set(val)

    def add_coins(self, delta):
        val = min(9999, max(0, self.coins_var.get() + delta))
        self.coins_var.set(val)

    def set_coins_val(self, val):
        self.coins_var.set(val)

    def on_max_finances(self):
        self.set_money_val(999999)
        self.set_coins_val(9999)
        self.status_var.set("Money set to ₽999,999 and Coins to 9,999")

    # ------------------ PARTY TAB ------------------
    def build_party_tab(self):
        paned = ttk.PanedWindow(self.party_tab, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        # Left: Party list
        left_f = ttk.Frame(paned, padding=6)
        paned.add(left_f, weight=1)

        ttk.Label(left_f, text="Party Slots:", font=("Sans", 10, "bold")).pack(anchor=tk.W, pady=(0, 4))
        self.party_listbox = tk.Listbox(left_f, width=28, height=12, font=("Sans", 10))
        self.party_listbox.pack(fill=tk.BOTH, expand=True)
        self.party_listbox.bind("<<ListboxSelect>>", self.on_party_select)

        party_btn_f = ttk.Frame(left_f)
        party_btn_f.pack(fill=tk.X, pady=(4, 0))
        ttk.Button(party_btn_f, text="💖 Heal Selected", command=self.on_heal_selected_mon).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        ttk.Button(party_btn_f, text="⭐ 31 IVs", command=self.on_max_selected_ivs).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)

        # Right: Pokemon Editor
        self.mon_editor_f = ttk.Frame(paned, padding=8)
        paned.add(self.mon_editor_f, weight=3)

        # Top row: Species, Nickname, Level, Shiny
        row0 = ttk.Frame(self.mon_editor_f)
        row0.pack(fill=tk.X, pady=4)

        ttk.Label(row0, text="Species:").pack(side=tk.LEFT, padx=(0, 4))
        self.species_cb = AutocompleteCombobox(row0, width=22)
        self.species_cb.set_completion_list(list(SPECIES.values()))
        self.species_cb.pack(side=tk.LEFT, padx=(0, 10))
        self.species_cb.bind("<<ComboboxSelected>>", self.on_species_change)

        ttk.Label(row0, text="Nickname:").pack(side=tk.LEFT, padx=(0, 4))
        self.mon_nick_var = tk.StringVar()
        ttk.Entry(row0, textvariable=self.mon_nick_var, width=14).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Label(row0, text="Level:").pack(side=tk.LEFT, padx=(0, 4))
        self.mon_lvl_var = tk.IntVar(value=1)
        ttk.Spinbox(row0, from_=1, to=100, textvariable=self.mon_lvl_var, width=4).pack(side=tk.LEFT, padx=(0, 10))

        self.mon_shiny_var = tk.BooleanVar()
        ttk.Checkbutton(row0, text="★ Shiny", variable=self.mon_shiny_var).pack(side=tk.LEFT)

        # Row 1: Nature, Tera Type, Held Item, Ball
        row1 = ttk.Frame(self.mon_editor_f)
        row1.pack(fill=tk.X, pady=4)

        ttk.Label(row1, text="Nature:").pack(side=tk.LEFT, padx=(0, 4))
        nature_opts = [f"{n} ({NATURE_STATS[n][0]}, {NATURE_STATS[n][1]})" for n in NATURES]
        self.nature_cb = ttk.Combobox(row1, values=nature_opts, width=20, state="readonly")
        self.nature_cb.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Label(row1, text="Tera Type:").pack(side=tk.LEFT, padx=(0, 4))
        self.tera_cb = ttk.Combobox(row1, values=TERA_TYPES, width=12, state="readonly")
        self.tera_cb.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Label(row1, text="Held Item:").pack(side=tk.LEFT, padx=(0, 4))
        self.held_cb = AutocompleteCombobox(row1, width=18)
        self.held_cb.set_completion_list(list(ITEMS.values()))
        self.held_cb.pack(side=tk.LEFT)

        # Row 2: HP & Stats
        stats_lf = ttk.LabelFrame(self.mon_editor_f, text=" Stats & HP ", padding=6)
        stats_lf.pack(fill=tk.X, pady=6)

        hp_f = ttk.Frame(stats_lf)
        hp_f.pack(fill=tk.X, pady=2)
        ttk.Label(hp_f, text="Current HP:").pack(side=tk.LEFT, padx=(0, 4))
        self.mon_hp_var = tk.IntVar()
        ttk.Spinbox(hp_f, from_=0, to=999, textvariable=self.mon_hp_var, width=5).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Label(hp_f, text="Max HP:").pack(side=tk.LEFT, padx=(0, 4))
        self.mon_maxhp_var = tk.IntVar()
        ttk.Spinbox(hp_f, from_=1, to=999, textvariable=self.mon_maxhp_var, width=5).pack(side=tk.LEFT, padx=(0, 15))

        ttk.Label(hp_f, text="Friendship:").pack(side=tk.LEFT, padx=(0, 4))
        self.mon_friend_var = tk.IntVar()
        ttk.Spinbox(hp_f, from_=0, to=255, textvariable=self.mon_friend_var, width=5).pack(side=tk.LEFT, padx=(0, 15))

        ttk.Label(hp_f, text="EXP:").pack(side=tk.LEFT, padx=(0, 4))
        self.mon_exp_var = tk.IntVar()
        ttk.Entry(hp_f, textvariable=self.mon_exp_var, width=10).pack(side=tk.LEFT)

        # IVs and EVs frame
        iv_ev_f = ttk.Frame(self.mon_editor_f)
        iv_ev_f.pack(fill=tk.X, pady=4)

        # IVs Box
        iv_lf = ttk.LabelFrame(iv_ev_f, text=" Individual Values (IVs: 0-31) ", padding=6)
        iv_lf.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 4))

        self.iv_vars = [tk.IntVar() for _ in range(6)]
        stat_names = ["HP", "Attack", "Defense", "Speed", "Sp. Atk", "Sp. Def"]
        for i, name in enumerate(stat_names):
            r = i // 2
            c = (i % 2) * 2
            ttk.Label(iv_lf, text=f"{name}:").grid(row=r, column=c, sticky=tk.W, padx=2, pady=2)
            ttk.Spinbox(iv_lf, from_=0, to=31, textvariable=self.iv_vars[i], width=4).grid(row=r, column=c+1, padx=4, pady=2)

        # EVs Box
        ev_lf = ttk.LabelFrame(iv_ev_f, text=" Effort Values (EVs: 0-252) ", padding=6)
        ev_lf.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(4, 0))

        self.ev_vars = [tk.IntVar() for _ in range(6)]
        for i, name in enumerate(stat_names):
            r = i // 2
            c = (i % 2) * 2
            ttk.Label(ev_lf, text=f"{name}:").grid(row=r, column=c, sticky=tk.W, padx=2, pady=2)
            ttk.Spinbox(ev_lf, from_=0, to=252, textvariable=self.ev_vars[i], width=5).grid(row=r, column=c+1, padx=4, pady=2)

        # Moves Box
        moves_lf = ttk.LabelFrame(self.mon_editor_f, text=" Moves & PP ", padding=6)
        moves_lf.pack(fill=tk.X, pady=6)

        self.move_cbs: list[AutocompleteCombobox] = []
        self.pp_vars: list[tk.IntVar] = []
        move_names_list = ["(None)"] + sorted(list(MOVES.values()))

        for i in range(4):
            mf = ttk.Frame(moves_lf)
            mf.pack(fill=tk.X, pady=2)
            ttk.Label(mf, text=f"Move {i+1}:", width=8).pack(side=tk.LEFT)
            cb = AutocompleteCombobox(mf, width=25)
            cb.set_completion_list(move_names_list)
            cb.pack(side=tk.LEFT, padx=(0, 10))
            self.move_cbs.append(cb)

            ttk.Label(mf, text="PP:").pack(side=tk.LEFT, padx=(0, 4))
            pp_v = tk.IntVar()
            ttk.Spinbox(mf, from_=0, to=99, textvariable=pp_v, width=4).pack(side=tk.LEFT)
            self.pp_vars.append(pp_v)

        # Apply mon edits button
        btn_f = ttk.Frame(self.mon_editor_f)
        btn_f.pack(fill=tk.X, pady=6)
        ttk.Button(btn_f, text="✔ Apply Changes to Selected Pokémon", command=self.apply_mon_edits).pack(side=tk.RIGHT, padx=4)

    # ------------------ BAG TAB ------------------
    def update_tree_style(self):
        row_height = max(28, int(self.tree_font_size * 2.6))
        self.style.configure("Treeview", font=("Sans", self.tree_font_size), rowheight=row_height)
        self.style.configure("Treeview.Heading", font=("Sans", max(10, self.tree_font_size), "bold"), padding=(4, 6))

    def zoom_in_tree(self, event=None):
        if self.tree_font_size < 22:
            self.tree_font_size += 1
            if hasattr(self, 'zoom_lbl'):
                self.zoom_lbl.config(text=f"{self.tree_font_size}pt")
            self.update_tree_style()

    def zoom_out_tree(self, event=None):
        if self.tree_font_size > 8:
            self.tree_font_size -= 1
            if hasattr(self, 'zoom_lbl'):
                self.zoom_lbl.config(text=f"{self.tree_font_size}pt")
            self.update_tree_style()

    def zoom_reset_tree(self, event=None):
        self.tree_font_size = 11
        if hasattr(self, 'zoom_lbl'):
            self.zoom_lbl.config(text=f"{self.tree_font_size}pt")
        self.update_tree_style()

    def build_bag_tab(self):
        top_f = ttk.Frame(self.bag_tab)
        top_f.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(top_f, text="Bag Pocket:", font=("Sans", 10, "bold")).pack(side=tk.LEFT, padx=(0, 8))
        self.pocket_cb = ttk.Combobox(top_f, values=list(BAG_POCKET_INFO.keys()), state="readonly", width=16)
        self.pocket_cb.set("Medicine")
        self.pocket_cb.pack(side=tk.LEFT, padx=(0, 10))
        self.pocket_cb.bind("<<ComboboxSelected>>", lambda e: self.refresh_bag_view())

        ttk.Button(top_f, text="Add Item...", command=self.on_add_bag_item).pack(side=tk.LEFT, padx=3)
        ttk.Button(top_f, text="Delete Item", command=self.on_delete_bag_item).pack(side=tk.LEFT, padx=3)

        # Zoom / Size controls
        zoom_f = ttk.Frame(top_f)
        zoom_f.pack(side=tk.LEFT, padx=(12, 0))
        ttk.Label(zoom_f, text="Text Size:").pack(side=tk.LEFT, padx=(0, 3))
        ttk.Button(zoom_f, text="➖", width=3, command=self.zoom_out_tree).pack(side=tk.LEFT, padx=1)
        self.zoom_lbl = ttk.Label(zoom_f, text=f"{self.tree_font_size}pt", font=("Sans", 9, "bold"), width=5, anchor=tk.CENTER)
        self.zoom_lbl.pack(side=tk.LEFT, padx=2)
        ttk.Button(zoom_f, text="➕", width=3, command=self.zoom_in_tree).pack(side=tk.LEFT, padx=1)

        # Quick preset buttons
        preset_f = ttk.Frame(top_f)
        preset_f.pack(side=tk.RIGHT)
        ttk.Button(preset_f, text="+99 Rare Candies", command=lambda: self.add_preset_item("Medicine", "Rare Candy", 99)).pack(side=tk.LEFT, padx=2)
        ttk.Button(preset_f, text="+99 Master Balls", command=lambda: self.add_preset_item("PokeBalls", "Master Ball", 99)).pack(side=tk.LEFT, padx=2)
        ttk.Button(preset_f, text="+99 Max Revives", command=lambda: self.add_preset_item("Medicine", "Max Revive", 99)).pack(side=tk.LEFT, padx=2)

        # Bag Treeview
        tree_f = ttk.Frame(self.bag_tab)
        tree_f.pack(fill=tk.BOTH, expand=True)

        cols = ("slot", "item", "qty")
        self.bag_tree = ttk.Treeview(tree_f, columns=cols, show="headings", height=14)
        self.bag_tree.heading("slot", text="Slot")
        self.bag_tree.heading("item", text="Item Name")
        self.bag_tree.heading("qty", text="Quantity")
        self.bag_tree.column("slot", width=80, minwidth=50, stretch=False, anchor=tk.CENTER)
        self.bag_tree.column("item", width=460, minwidth=180, stretch=True, anchor=tk.W)
        self.bag_tree.column("qty", width=120, minwidth=70, stretch=False, anchor=tk.CENTER)

        # Striped row colors
        self.bag_tree.tag_configure('even', background='#ffffff')
        self.bag_tree.tag_configure('odd', background='#f4f5f7')

        tree_scroll = ttk.Scrollbar(tree_f, orient=tk.VERTICAL, command=self.bag_tree.yview)
        self.bag_tree.configure(yscrollcommand=tree_scroll.set)
        self.bag_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.bag_tree.bind("<Double-1>", self.on_bag_double_click)

    # ------------------ EVENT HANDLERS ------------------
    def on_open_file(self):
        path = filedialog.askopenfilename(
            title="Open Pokémon SoulGold Save File",
            filetypes=[("GBA Save Files", "*.sav"), ("All Files", "*.*")]
        )
        if path:
            self.load_save_file(path)

    def on_switch_save(self, event=None):
        if not hasattr(self, 'save_switch_cb'):
            return
        sel_idx = self.save_switch_cb.current()
        saves = get_available_saves()
        if 0 <= sel_idx < len(saves):
            target_path = saves[sel_idx]["path"]
            self.load_save_file(target_path)

    def on_clone_to_v113(self):
        v113_path = "/home/josecachy/Downloads/GBA/Soulgold (v1.1.3).sav"
        v11_path = "/home/josecachy/Downloads/GBA/Pokemon Soulgold.sav"
        if not self.sav or not self.current_party:
            if os.path.exists(v11_path):
                source_sav = SoulGoldSave(v11_path)
            else:
                messagebox.showerror("No Source Save", "Could not find a valid Pokémon SoulGold save to clone from.")
                return
        else:
            source_sav = self.sav

        dest_sav = SoulGoldSave(v113_path if os.path.exists(v113_path) else None)
        dest_sav.clone_from(source_sav)
        dest_sav.save(v113_path)
        messagebox.showinfo("Cloned Successfully", f"Your save data was successfully migrated and saved to:\n{v113_path}\n\nYou can now play SoulGold v1.1.3 with your full progress!")
        self.load_save_file(v113_path)

    def load_save_file(self, filepath: str):
        try:
            self.sav = SoulGoldSave(filepath)
            version_str = self.sav.detect_version()
            self.file_label.config(text=os.path.basename(filepath), font=("Sans", 9, "bold"))
            self.version_badge.config(text=f"[{version_str}]", foreground="#2e7d32" if "1.1.3" in version_str else "#1565c0")
            self.status_var.set(f"Loaded '{os.path.basename(filepath)}' ({version_str})")

            # Check if save is uninitialized blank flash
            if self.sav.is_blank_flash:
                alt_path = "/home/josecachy/Downloads/GBA/Pokemon Soulgold.sav"
                if os.path.exists(alt_path) and os.path.abspath(alt_path) != os.path.abspath(filepath):
                    ans = messagebox.askyesno(
                        "Blank Save File Detected",
                        f"'{os.path.basename(filepath)}' is currently empty/uninitialized.\n\n"
                        f"Would you like to clone your active save data from 'Pokemon Soulgold.sav' into this file so you can continue your adventure in {version_str}?",
                        icon="question"
                    )
                    if ans:
                        alt_sav = SoulGoldSave(alt_path)
                        self.sav.clone_from(alt_sav)
                        self.sav.save(filepath)
                        self.status_var.set(f"Successfully cloned progress into '{os.path.basename(filepath)}'")

            # Populate Trainer Tab
            self.trainer_name_var.set(self.sav.get_trainer_name())
            self.gender_var.set(self.sav.get_gender())
            tid, sid = self.sav.get_trainer_id()
            self.tid_var.set(tid)
            self.sid_var.set(sid)
            h, m, s = self.sav.get_play_time()
            self.hours_var.set(h)
            self.mins_var.set(m)
            self.secs_var.set(s)
            self.money_var.set(self.sav.get_money())
            self.coins_var.set(self.sav.get_coins())

            # Populate Party Tab
            self.current_party = self.sav.get_party()
            self.refresh_party_listbox()
            if self.current_party:
                self.party_listbox.select_set(0)
                self.load_mon_into_editor(0)

            # Populate Bag Tab
            self.refresh_bag_view()
        except Exception as e:
            messagebox.showerror("Error Opening File", f"Failed to load save file:\n{str(e)}")

    def refresh_party_listbox(self):
        self.party_listbox.delete(0, tk.END)
        for i, mon in enumerate(self.current_party):
            shiny = "★ " if mon.is_shiny else ""
            self.party_listbox.insert(tk.END, f"{i+1}: {shiny}{mon.species_name} (Lv.{mon.level}) - {mon.hp}/{mon.max_hp}")

    def on_party_select(self, event):
        sel = self.party_listbox.curselection()
        if sel:
            idx = sel[0]
            self.load_mon_into_editor(idx)

    def load_mon_into_editor(self, idx: int):
        if idx >= len(self.current_party):
            return
        self.selected_mon_idx = idx
        mon = self.current_party[idx]

        self.species_cb.set(mon.species_name)
        self.mon_nick_var.set(mon.nickname)
        self.mon_lvl_var.set(mon.level)
        self.mon_shiny_var.set(mon.is_shiny)

        nat = mon.nature
        for item in self.nature_cb['values']:
            if item.startswith(nat):
                self.nature_cb.set(item)
                break

        if 0 <= mon.tera_type < len(TERA_TYPES):
            self.tera_cb.set(TERA_TYPES[mon.tera_type])
        else:
            self.tera_cb.set("None")

        self.held_cb.set(ITEMS.get(mon.held_item, "None"))

        self.mon_hp_var.set(mon.hp)
        self.mon_maxhp_var.set(mon.max_hp)
        self.mon_friend_var.set(mon.friendship)
        self.mon_exp_var.set(mon.experience)

        for i in range(6):
            self.iv_vars[i].set(mon.ivs[i])
            self.ev_vars[i].set(mon.evs[i])

        for i in range(4):
            m_id = mon.moves[i]
            self.move_cbs[i].set(MOVES.get(m_id, "(None)"))
            self.pp_vars[i].set(mon.pps[i])

    def apply_mon_edits(self):
        if not self.current_party or self.selected_mon_idx >= len(self.current_party):
            return
        mon = self.current_party[self.selected_mon_idx]

        # Species
        spec_str = self.species_cb.get()
        if spec_str.lower() in SPECIES_BY_NAME:
            mon.species = SPECIES_BY_NAME[spec_str.lower()]

        mon.nickname = self.mon_nick_var.get()
        mon.level = max(1, min(100, self.mon_lvl_var.get()))
        mon.set_shiny(self.mon_shiny_var.get())

        # Nature
        nat_str = self.nature_cb.get().split()[0]
        mon.set_nature(nat_str)

        # Tera type
        tera_str = self.tera_cb.get()
        if tera_str in TERA_TYPES:
            mon.tera_type = TERA_TYPES.index(tera_str)

        # Held Item
        held_str = self.held_cb.get()
        if held_str.lower() in ITEMS_BY_NAME:
            mon.held_item = ITEMS_BY_NAME[held_str.lower()]

        mon.hp = self.mon_hp_var.get()
        mon.max_hp = self.mon_maxhp_var.get()
        mon.friendship = max(0, min(255, self.mon_friend_var.get()))
        mon.experience = max(0, self.mon_exp_var.get())

        for i in range(6):
            mon.ivs[i] = max(0, min(31, self.iv_vars[i].get()))
            mon.evs[i] = max(0, min(252, self.ev_vars[i].get()))

        for i in range(4):
            mv_str = self.move_cbs[i].get()
            if mv_str.lower() in MOVES_BY_NAME:
                mon.moves[i] = MOVES_BY_NAME[mv_str.lower()]
            elif mv_str == "(None)":
                mon.moves[i] = 0
            mon.pps[i] = max(0, min(99, self.pp_vars[i].get()))

        self.sav.set_party_mon(self.selected_mon_idx, mon)
        self.refresh_party_listbox()
        self.party_listbox.select_set(self.selected_mon_idx)
        self.status_var.set(f"Changes applied to slot {self.selected_mon_idx + 1} ({mon.species_name})")

    def on_species_change(self, event):
        spec_str = self.species_cb.get()
        if spec_str.lower() in SPECIES_BY_NAME:
            clean_name = SPECIES[SPECIES_BY_NAME[spec_str.lower()]]
            self.mon_nick_var.set(clean_name)

    def on_heal_selected_mon(self):
        if self.current_party and self.selected_mon_idx < len(self.current_party):
            mon = self.current_party[self.selected_mon_idx]
            mon.heal()
            self.mon_hp_var.set(mon.max_hp)
            for i in range(4):
                self.pp_vars[i].set(mon.pps[i])
            self.status_var.set(f"Healed {mon.species_name}")

    def on_max_selected_ivs(self):
        for iv_var in self.iv_vars:
            iv_var.set(31)
        self.status_var.set("IVs set to 31 for selected Pokémon")

    def on_heal_party(self):
        if not self.sav:
            return
        self.apply_mon_edits()
        self.sav.heal_party()
        self.current_party = self.sav.get_party()
        self.refresh_party_listbox()
        self.load_mon_into_editor(self.selected_mon_idx)
        self.status_var.set("💖 Entire party fully healed (HP & PP restored)!")

    def on_max_party_ivs(self):
        if not self.sav:
            return
        self.apply_mon_edits()
        self.sav.max_party_ivs()
        self.current_party = self.sav.get_party()
        self.refresh_party_listbox()
        self.load_mon_into_editor(self.selected_mon_idx)
        self.status_var.set("⭐ All party Pokémon IVs set to 31!")

    # ------------------ BAG METHODS ------------------
    def refresh_bag_view(self):
        if not self.sav:
            return
        pocket = self.pocket_cb.get()
        items = self.sav.get_bag_pocket(pocket)

        for item in self.bag_tree.get_children():
            self.bag_tree.delete(item)

        for i, (item_id, qty) in enumerate(items):
            item_name = ITEMS.get(item_id, f"Item #{item_id}")
            tag = 'even' if (i % 2 == 0) else 'odd'
            self.bag_tree.insert("", tk.END, values=(i + 1, item_name, qty), tags=(tag,))

    def on_bag_double_click(self, event):
        item = self.bag_tree.selection()
        if not item:
            return
        vals = self.bag_tree.item(item[0], "values")
        slot_idx = int(vals[0]) - 1
        curr_name = vals[1]
        curr_qty = int(vals[2])

        # Open small dialog to edit quantity
        dlg = tk.Toplevel(self)
        dlg.title("Edit Item Quantity")
        dlg.geometry("280x130")
        dlg.resizable(False, False)
        dlg.transient(self)

        ttk.Label(dlg, text=f"{curr_name}", font=("Sans", 10, "bold")).pack(pady=6)
        qf = ttk.Frame(dlg)
        qf.pack(pady=4)
        ttk.Label(qf, text="Quantity:").pack(side=tk.LEFT, padx=4)
        qty_var = tk.IntVar(value=curr_qty)
        sp = ttk.Spinbox(qf, from_=1, to=999, textvariable=qty_var, width=6)
        sp.pack(side=tk.LEFT, padx=4)

        def save_qty():
            new_qty = max(1, min(999, qty_var.get()))
            pocket = self.pocket_cb.get()
            items = self.sav.get_bag_pocket(pocket)
            if slot_idx < len(items):
                items[slot_idx] = (items[slot_idx][0], new_qty)
                self.sav.set_bag_pocket(pocket, items)
                self.refresh_bag_view()
                self.status_var.set(f"Updated {curr_name} quantity to {new_qty}")
            dlg.destroy()

        btn_f = ttk.Frame(dlg)
        btn_f.pack(pady=6)
        ttk.Button(btn_f, text="OK", command=save_qty).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_f, text="Cancel", command=dlg.destroy).pack(side=tk.LEFT, padx=4)

    def on_add_bag_item(self):
        if not self.sav:
            return
        pocket = self.pocket_cb.get()

        dlg = tk.Toplevel(self)
        dlg.title(f"Add Item to {pocket}")
        dlg.geometry("380x160")
        dlg.resizable(False, False)
        dlg.transient(self)

        ttk.Label(dlg, text="Select Item:").pack(anchor=tk.W, padx=12, pady=(10, 2))
        cb = AutocompleteCombobox(dlg, width=35)
        cb.set_completion_list(list(ITEMS.values()))
        cb.pack(padx=12, pady=2)

        qf = ttk.Frame(dlg)
        qf.pack(fill=tk.X, padx=12, pady=8)
        ttk.Label(qf, text="Quantity:").pack(side=tk.LEFT, padx=(0, 4))
        qty_var = tk.IntVar(value=10)
        ttk.Spinbox(qf, from_=1, to=999, textvariable=qty_var, width=6).pack(side=tk.LEFT)

        def confirm_add():
            name = cb.get()
            if name.lower() in ITEMS_BY_NAME:
                item_id = ITEMS_BY_NAME[name.lower()]
                qty = max(1, min(999, qty_var.get()))
                items = self.sav.get_bag_pocket(pocket)
                capacity = BAG_POCKET_INFO[pocket]["count"]
                if len(items) >= capacity:
                    messagebox.showwarning("Pocket Full", f"The {pocket} pocket is already full!")
                    return
                # Check if item already in pocket
                for idx, (existing_id, existing_qty) in enumerate(items):
                    if existing_id == item_id:
                        items[idx] = (item_id, min(999, existing_qty + qty))
                        self.sav.set_bag_pocket(pocket, items)
                        self.refresh_bag_view()
                        self.status_var.set(f"Increased {name} to {items[idx][1]}")
                        dlg.destroy()
                        return
                items.append((item_id, qty))
                self.sav.set_bag_pocket(pocket, items)
                self.refresh_bag_view()
                self.status_var.set(f"Added {name} x{qty} to {pocket}")
                dlg.destroy()
            else:
                messagebox.showerror("Invalid Item", f"Item '{name}' not recognized.")

        btn_f = ttk.Frame(dlg)
        btn_f.pack(pady=4)
        ttk.Button(btn_f, text="Add", command=confirm_add).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_f, text="Cancel", command=dlg.destroy).pack(side=tk.LEFT, padx=4)

    def on_delete_bag_item(self):
        if not self.sav:
            return
        item = self.bag_tree.selection()
        if not item:
            return
        vals = self.bag_tree.item(item[0], "values")
        slot_idx = int(vals[0]) - 1
        name = vals[1]

        if messagebox.askyesno("Delete Item", f"Remove '{name}' from bag?"):
            pocket = self.pocket_cb.get()
            items = self.sav.get_bag_pocket(pocket)
            if slot_idx < len(items):
                items.pop(slot_idx)
                self.sav.set_bag_pocket(pocket, items)
                self.refresh_bag_view()
                self.status_var.set(f"Removed {name} from {pocket}")

    def add_preset_item(self, pocket: str, item_name: str, qty: int):
        if not self.sav:
            return
        if item_name.lower() in ITEMS_BY_NAME:
            item_id = ITEMS_BY_NAME[item_name.lower()]
            items = self.sav.get_bag_pocket(pocket)
            for idx, (existing_id, existing_qty) in enumerate(items):
                if existing_id == item_id:
                    items[idx] = (item_id, min(999, existing_qty + qty))
                    self.sav.set_bag_pocket(pocket, items)
                    self.pocket_cb.set(pocket)
                    self.refresh_bag_view()
                    self.status_var.set(f"Added {item_name} x{qty} to {pocket}")
                    return
            items.append((item_id, qty))
            self.sav.set_bag_pocket(pocket, items)
            self.pocket_cb.set(pocket)
            self.refresh_bag_view()
            self.status_var.set(f"Added {item_name} x{qty} to {pocket}")

    # ------------------ SAVE & EXPORT ------------------
    def commit_all_changes(self):
        if not self.sav:
            return
        # Trainer Tab
        self.sav.set_trainer_name(self.trainer_name_var.get())
        self.sav.set_gender(self.gender_var.get())
        self.sav.set_trainer_id(self.tid_var.get(), self.sid_var.get())
        self.sav.set_play_time(self.hours_var.get(), self.mins_var.get(), self.secs_var.get())
        self.sav.set_money(self.money_var.get())
        self.sav.set_coins(self.coins_var.get())

        # Current Party Mon
        self.apply_mon_edits()

    def on_save_file(self):
        if not self.sav:
            messagebox.showinfo("No File", "Please open a save file first.")
            return
        try:
            self.commit_all_changes()
            self.sav.save()
            self.status_var.set(f"Successfully saved to '{os.path.basename(self.sav.filepath)}' (Backup created)")
            messagebox.showinfo("Saved", f"Save file updated successfully!\nAn automatic backup (.bak) was also created.")
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save:\n{str(e)}")

    def on_save_as(self):
        if not self.sav:
            return
        path = filedialog.asksaveasfilename(
            title="Save As",
            defaultextension=".sav",
            filetypes=[("GBA Save Files", "*.sav"), ("All Files", "*.*")]
        )
        if path:
            try:
                self.commit_all_changes()
                self.sav.save(path, make_backup=False)
                self.status_var.set(f"Saved copy to '{path}'")
                messagebox.showinfo("Saved", f"File saved as '{path}'")
            except Exception as e:
                messagebox.showerror("Save Error", f"Failed to save as:\n{str(e)}")

    def on_about(self):
        messagebox.showinfo(
            "About",
            "Pokémon SoulGold GBA Save Editor\n"
            "Custom-built for pokeemerald-expansion / SoulGold engine.\n\n"
            "• Supports Pokémon SoulGold v1.1 & v1.1.3\n"
            "• Gen 1-9 species, moves, abilities, full IV/EV editing\n"
            "• Full party heal, bag inventory management, money/coins\n"
            "• Dual-slot flash checksum integrity verification\n"
            "• Automatic rolling 2-backup safety mechanism"
        )

def main(save_arg: str = None):
    if save_arg is None and len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        save_arg = sys.argv[1]
    app = SoulGoldEditorApp(save_arg)
    app.mainloop()

if __name__ == "__main__":
    main()
