# Pokémon SoulGold Save Editor (Web & Desktop)

A powerful, modern save editor for **Pokémon SoulGold** (GBA ROM hack v1.1 & v1.1.3) built with pure Python and a sleek browser interface inspired by **pkmds.app**.

![UI Preview](soulgold_icon.png)

## Features

- **PC Storage Boxes (1–14)**: Full access to all 14 PC boxes (420 Pokémon slots total) with interactive 6×5 slot grid, sprite previews, shiny indicators, level badges, and live box renaming.
- **Party Pokémon**: Edit all 6 party slots with visual HP bars, sprites, and instant stats recalculation.
- **Complete Pokémon Customization**:
  - Species selector (Bulbasaur to Gen 9 + forms)
  - Shiny toggle (★) with personality recalculation preserving gender & nature
  - Nature modifier with positive/negative stat boosts
  - Tera Type assignment
  - Held items & Pokéballs
  - Movepool (4 moves + PP)
  - Precise IVs (0–31) with one-click "All 31s"
  - Precise EVs (0–252) with real-time 510 total cap counter
- **Trainer & Progression**: Name, Gender, Trainer ID (TID), Secret ID (SID), Money (₽), Game Corner Coins, and Play Time.
- **Bag & Inventory**: Edit item quantities across all 8 bag pockets (Medicine, Pokéballs, TMs/HMs, Mega Stones, Berries, etc.).
- **Automatic Sector Checksumming**: Recalculates and validates all 14 flash save sectors (0–13) and auxiliary counters on every save.
- **Zero Dependencies**: Runs with standard Python 3.8+ library. Zero pip packages required!

---

## 🚀 Quick Start (Local)

### 1. Launch Web App
```bash
python3 soulgold_web_server.py
```
Or use the launcher:
```bash
python3 soulgold_editor.py --web
```
Open your browser at `http://localhost:8080`.

### 2. Launch Desktop GUI (Tkinter)
```bash
python3 soulgold_editor.py
```

---

## ☁️ Deploy to Render.com (1-Click Hosting)

You can host this web application online for free on [Render.com](https://render.com) so you and your friends can access it anywhere from phone, tablet, or PC!

### Step 1: Push to GitHub (`jozeton-app`)
1. Create a new repository on GitHub under [https://github.com/jozeton-app](https://github.com/jozeton-app) (e.g. `soulgold-save-editor`).
2. Link and push your code:
   ```bash
   git remote add origin https://github.com/jozeton-app/<your-repo-name>.git
   git branch -M main
   git push -u origin main
   ```

### Step 2: Create Web Service on Render
1. Go to [dashboard.render.com](https://dashboard.render.com/) and click **New +** → **Web Service**.
2. Connect your GitHub repository (`jozeton-app/<your-repo-name>`).
3. Fill in the settings:
   - **Name**: `soulgold-save-editor` (or your choice)
   - **Runtime**: `Python 3` (or `Docker`)
   - **Build Command**: `pip install -r requirements.txt` (or leave empty)
   - **Start Command**: `python3 soulgold_web_server.py --host 0.0.0.0 --port $PORT --no-browser`
   - **Instance Type**: `Free`
4. Click **Deploy Web Service**!

Render will build and deploy the editor within 60 seconds, giving you a free, public HTTPS URL (e.g. `https://soulgold-save-editor.onrender.com`) with full file upload and download support!

---

## Testing

Run the automated test suite:
```bash
python3 -m unittest discover -s .
```

## License
MIT License
