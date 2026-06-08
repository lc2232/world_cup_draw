# World Cup 2026 Draw

A locally-hosted sweepstake app for the 2026 FIFA World Cup. Enter your group of players, draw teams (randomly or manually), then track everyone's remaining teams as the tournament progresses — with live match results fetched automatically.

---

## Purpose

This app is designed for a group of friends running a World Cup sweepstake. Each player is assigned a set of teams from the 48-team 2026 tournament. As teams are eliminated, they are crossed off each player's list. The last player with a team still in the tournament wins.

The app handles:
- Distributing 48 teams fairly across any number of players
- Tracking group stage standings and knockout results automatically via the football-data.org API
- Showing a live dashboard of each player's remaining teams

---

## Prerequisites

- Python 3.10+
- A virtual environment (`.venv` is already included in this repo)
- A football-data.org API key (free or paid — see [API Setup](#api-setup) below)

---

## Setup

**1. Install dependencies into the virtual environment:**
```bash
.venv/bin/pip install -r requirements.txt
```

**2. Configure your API key:**
```bash
cp .env.example .env
```
Then open `.env` and replace `your_key_here` with your football-data.org API key.

**3. Start the app:**
```bash
.venv/bin/python app.py
```

**4. Open in your browser:**
```
http://localhost:5000
```

---

## Typical Usage

### Step 1 — Player Setup
Navigate to `/setup` (or just open the app — it redirects there automatically if no draw exists).

Enter the names of everyone taking part in the sweepstake. A minimum of 2 players is required; there is no upper limit. Click **Continue**.

### Step 2 — The Draw
Choose how to assign teams:

- **Random Draw** — the app shuffles all 48 teams and distributes them as evenly as possible. If 48 doesn't divide evenly by the number of players, some players will receive one extra team.
- **Manual Entry** — a table shows all 48 teams with a dropdown next to each. Assign every team to a player by hand. Use the search box to filter by team name, or click **Auto-fill Unassigned** to let the app distribute any remaining teams automatically.

Once the draw is complete, assignments are saved locally and you are taken to the dashboard.

### Step 3 — The Dashboard
The main dashboard has two panels:

- **Standings (left)** — each player listed with their full team list. Eliminated teams appear crossed out and faded.
- **Tournament (right)** — group stage standings (collapsible per group) and knockout stage results as they come in.

Click **Refresh Results** at any time to fetch the latest match data from the API. Results are cached for 5 minutes to stay within API rate limits.

### Resetting the Draw
Click **Reset** in the navigation bar to clear all data and start a new draw. This is irreversible.

---

## API Setup

Match results are fetched from [football-data.org](https://www.football-data.org).

1. Register for a free account at [football-data.org/client/register](https://www.football-data.org/client/register)
2. Copy your API token from your account dashboard
3. Paste it into your `.env` file as `FOOTBALL_DATA_API_KEY`

> **Note:** The free tier (Plan 0) covers major European club leagues. Live World Cup data may require the **Starter plan** (~$7/month). Without a valid key, the app still runs — the Refresh button will show an error message and the dashboard will display whatever data was last successfully cached.

---

## Project Structure

```
world_cup_draw/
├── app.py                  # Flask app — routes, API integration, draw logic
├── requirements.txt
├── .env.example            # Copy to .env and add your API key
├── data/
│   ├── teams.json          # 48-team fallback list; overwritten by API on first draw
│   └── draw.json           # Generated file: player assignments and tournament state
├── templates/
│   ├── base.html           # Shared layout and navigation
│   ├── setup.html          # Player name entry
│   ├── draw.html           # Random / manual team assignment
│   ├── dashboard.html      # Live standings and bracket
│   └── reset.html          # Confirm reset screen
└── static/
    ├── style.css           # Theme (see Themes below)
    └── app.js              # Refresh button logic
```

`draw.json` is created automatically when a draw is made and lives only on your machine. It is safe to delete it to start over (equivalent to using the Reset button).

---

