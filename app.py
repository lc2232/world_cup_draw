import json
import os
import random
import requests
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from flask import Flask, jsonify, redirect, render_template, request, url_for

load_dotenv()

app = Flask(__name__)

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
DRAW_FILE = os.path.join(DATA_DIR, 'draw.json')
TEAMS_FILE = os.path.join(DATA_DIR, 'teams.json')

API_KEY = os.getenv('FOOTBALL_DATA_API_KEY', '')
API_BASE = 'https://api.football-data.org/v4'
WC_SEASON = '2026'
REFRESH_COOLDOWN = timedelta(minutes=5)
TOURNAMENT_START = 'JUN 11 2026'

PLAYER_COLORS = ['#c04010', '#3a6215', '#8040c0', '#1060a0', '#a06000', '#b03060', '#107050', '#804010']

ROUND_ORDER = ['LAST_32', 'LAST_16', 'QUARTER_FINALS', 'SEMI_FINALS', 'FINAL', '3RD_PLACE']
ROUND_DISPLAY = {
    'LAST_32': 'ROUND OF 32',
    'LAST_16': 'ROUND OF 16',
    'QUARTER_FINALS': 'QUARTER FINALS',
    'SEMI_FINALS': 'SEMI FINALS',
    'FINAL': 'FINAL',
    '3RD_PLACE': '3RD PLACE',
}

FALLBACK_TEAMS = [
    {'name': 'Germany', 'confederation': 'UEFA'},
    {'name': 'France', 'confederation': 'UEFA'},
    {'name': 'Spain', 'confederation': 'UEFA'},
    {'name': 'England', 'confederation': 'UEFA'},
    {'name': 'Portugal', 'confederation': 'UEFA'},
    {'name': 'Netherlands', 'confederation': 'UEFA'},
    {'name': 'Belgium', 'confederation': 'UEFA'},
    {'name': 'Croatia', 'confederation': 'UEFA'},
    {'name': 'Switzerland', 'confederation': 'UEFA'},
    {'name': 'Austria', 'confederation': 'UEFA'},
    {'name': 'Denmark', 'confederation': 'UEFA'},
    {'name': 'Scotland', 'confederation': 'UEFA'},
    {'name': 'Serbia', 'confederation': 'UEFA'},
    {'name': 'Hungary', 'confederation': 'UEFA'},
    {'name': 'Slovakia', 'confederation': 'UEFA'},
    {'name': 'Turkey', 'confederation': 'UEFA'},
    {'name': 'Argentina', 'confederation': 'CONMEBOL'},
    {'name': 'Brazil', 'confederation': 'CONMEBOL'},
    {'name': 'Uruguay', 'confederation': 'CONMEBOL'},
    {'name': 'Colombia', 'confederation': 'CONMEBOL'},
    {'name': 'Ecuador', 'confederation': 'CONMEBOL'},
    {'name': 'Venezuela', 'confederation': 'CONMEBOL'},
    {'name': 'Japan', 'confederation': 'AFC'},
    {'name': 'South Korea', 'confederation': 'AFC'},
    {'name': 'Iran', 'confederation': 'AFC'},
    {'name': 'Australia', 'confederation': 'AFC'},
    {'name': 'Saudi Arabia', 'confederation': 'AFC'},
    {'name': 'Iraq', 'confederation': 'AFC'},
    {'name': 'Uzbekistan', 'confederation': 'AFC'},
    {'name': 'Jordan', 'confederation': 'AFC'},
    {'name': 'United States', 'confederation': 'CONCACAF'},
    {'name': 'Mexico', 'confederation': 'CONCACAF'},
    {'name': 'Canada', 'confederation': 'CONCACAF'},
    {'name': 'Costa Rica', 'confederation': 'CONCACAF'},
    {'name': 'Panama', 'confederation': 'CONCACAF'},
    {'name': 'Honduras', 'confederation': 'CONCACAF'},
    {'name': 'New Zealand', 'confederation': 'OFC'},
    {'name': 'Morocco', 'confederation': 'CAF'},
    {'name': 'Senegal', 'confederation': 'CAF'},
    {'name': 'Egypt', 'confederation': 'CAF'},
    {'name': 'Nigeria', 'confederation': 'CAF'},
    {'name': 'Ivory Coast', 'confederation': 'CAF'},
    {'name': 'Cameroon', 'confederation': 'CAF'},
    {'name': 'South Africa', 'confederation': 'CAF'},
    {'name': 'Algeria', 'confederation': 'CAF'},
    {'name': 'Tunisia', 'confederation': 'CAF'},
    {'name': 'Paraguay', 'confederation': 'CONMEBOL'},
    {'name': 'China PR', 'confederation': 'AFC'},
]


# ─── Data helpers ──────────────────────────────────────────────────────────────

def load_draw():
    if not os.path.exists(DRAW_FILE):
        return None
    with open(DRAW_FILE) as f:
        return json.load(f)


def save_draw(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(DRAW_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def load_teams():
    if os.path.exists(TEAMS_FILE):
        with open(TEAMS_FILE) as f:
            data = json.load(f)
            if data:
                return data
    return FALLBACK_TEAMS


def fetch_teams_from_api():
    if not API_KEY:
        return None
    headers = {'X-Auth-Token': API_KEY}
    try:
        r = requests.get(
            f'{API_BASE}/competitions/WC/teams',
            headers=headers,
            params={'season': WC_SEASON},
            timeout=10,
        )
        if r.status_code == 200:
            teams = [
                {
                    'name': t['name'],
                    'shortName': t.get('shortName', t['name']),
                    'tla': t.get('tla', ''),
                    'confederation': t.get('area', {}).get('name', ''),
                }
                for t in r.json().get('teams', [])
            ]
            if teams:
                os.makedirs(DATA_DIR, exist_ok=True)
                with open(TEAMS_FILE, 'w') as f:
                    json.dump(teams, f, indent=2)
                return teams
    except Exception:
        pass
    return None


# ─── Draw logic ────────────────────────────────────────────────────────────────

def distribute_teams(teams, player_names):
    team_names = [t['name'] for t in teams]
    shuffled = random.sample(team_names, len(team_names))
    n = len(player_names)
    base = len(shuffled) // n
    extra = len(shuffled) % n
    assignments = {}
    i = 0
    for idx, name in enumerate(player_names):
        count = base + (1 if idx < extra else 0)
        assignments[name] = shuffled[i:i + count]
        i += count
    return assignments


# ─── API refresh ───────────────────────────────────────────────────────────────

def can_refresh(draw):
    last = (draw or {}).get('tournament_state', {}).get('last_updated')
    if not last:
        return True
    try:
        last_dt = datetime.fromisoformat(last)
        if last_dt.tzinfo is None:
            last_dt = last_dt.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) - last_dt > REFRESH_COOLDOWN
    except ValueError:
        return True


def fetch_and_update_state(draw):
    if not API_KEY:
        return draw, 'No API key. Add FOOTBALL_DATA_API_KEY to your .env file.'

    headers = {'X-Auth-Token': API_KEY}

    def get(path, **params):
        r = requests.get(f'{API_BASE}{path}', headers=headers, params={'season': WC_SEASON, **params}, timeout=10)
        if r.status_code == 403:
            raise PermissionError('API key lacks access to World Cup data (paid tier may be required).')
        if r.status_code == 429:
            raise TimeoutError('Rate limit hit. Please wait before refreshing.')
        r.raise_for_status()
        return r.json()

    try:
        standings_data = get('/competitions/WC/standings')
        matches_data = get('/competitions/WC/matches')
    except (PermissionError, TimeoutError) as e:
        return draw, str(e)
    except Exception as e:
        return draw, f'Connection error: {e}'

    existing = draw.get('tournament_state', {})
    new_state = build_tournament_state(standings_data, matches_data, existing)
    new_state['last_updated'] = datetime.now(timezone.utc).isoformat()
    draw['tournament_state'] = new_state
    save_draw(draw)
    return draw, None


def build_tournament_state(standings_data, matches_data, existing):
    eliminated = set(existing.get('eliminated_teams', []))
    group_standings = {}
    knockout_matches = list(existing.get('knockout_matches', []))
    seen_ids = {m.get('id') for m in knockout_matches}

    group_thirds = []

    for standing in standings_data.get('standings', []):
        if standing.get('type') != 'TOTAL':
            continue
        raw_group = standing.get('group', '')
        group_name = raw_group.replace('GROUP_', '') if raw_group else '?'
        table = standing.get('table', [])
        rows = [
            {
                'team': row['team']['name'],
                'played': row['playedGames'],
                'points': row['points'],
                'won': row['won'],
                'draw': row['draw'],
                'lost': row['lost'],
                'gf': row['goalsFor'],
                'ga': row['goalsAgainst'],
                'gd': row['goalDifference'],
                'position': row['position'],
            }
            for row in table
        ]
        group_standings[group_name] = rows

        # Group complete when all 4 teams have played 3 games
        if len(rows) == 4 and all(r['played'] >= 3 for r in rows):
            fourth = next((r for r in rows if r['position'] == 4), None)
            if fourth:
                eliminated.add(fourth['team'])
            third = next((r for r in rows if r['position'] == 3), None)
            if third:
                group_thirds.append({**third, 'group': group_name})

    # After all 12 groups done, eliminate worst 4 third-place teams
    if len(group_thirds) == 12:
        group_thirds.sort(key=lambda x: (-x['points'], -x['gd'], -x['gf']))
        for t in group_thirds[8:]:
            eliminated.add(t['team'])

    knockout_rounds = {'LAST_32', 'LAST_16', 'QUARTER_FINALS', 'SEMI_FINALS', 'FINAL', '3RD_PLACE'}
    for match in matches_data.get('matches', []):
        if match.get('stage') not in knockout_rounds:
            continue
        if match.get('status') != 'FINISHED':
            continue
        mid = match.get('id')
        if mid in seen_ids:
            continue

        home = match['homeTeam']['name']
        away = match['awayTeam']['name']
        ft = match['score']['fullTime']
        hs = ft.get('home') or 0
        as_ = ft.get('away') or 0

        if hs > as_:
            winner, loser = home, away
        elif as_ > hs:
            winner, loser = away, home
        else:
            pen = match['score'].get('penalties') or {}
            winner, loser = (home, away) if (pen.get('home') or 0) >= (pen.get('away') or 0) else (away, home)

        if match['stage'] != '3RD_PLACE':
            eliminated.add(loser)

        seen_ids.add(mid)
        knockout_matches.append({
            'id': mid,
            'round': match['stage'],
            'home': home,
            'away': away,
            'winner': winner,
            'home_score': hs,
            'away_score': as_,
        })

    return {
        'last_updated': existing.get('last_updated'),
        'eliminated_teams': list(eliminated),
        'group_standings': group_standings,
        'knockout_matches': knockout_matches,
    }


# ─── Context processor ─────────────────────────────────────────────────────────

@app.context_processor
def inject_globals():
    draw = load_draw()
    return {
        'has_draw': draw is not None and bool(draw.get('players')),
        'player_colors': PLAYER_COLORS,
    }


# ─── Routes ────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    draw = load_draw()
    if draw and draw.get('players'):
        if any(p.get('teams') for p in draw['players']):
            return redirect(url_for('dashboard'))
        return redirect(url_for('draw_page'))
    return redirect(url_for('setup'))


@app.route('/setup', methods=['GET', 'POST'])
def setup():
    if request.method == 'POST':
        names = [n.strip() for n in request.form.getlist('player_name') if n.strip()]
        if len(names) < 2:
            return render_template('setup.html', error='Please enter at least 2 player names.')
        draw = {
            'players': [{'name': n, 'teams': []} for n in names],
            'tournament_state': {
                'last_updated': None,
                'eliminated_teams': [],
                'group_standings': {},
                'knockout_matches': [],
            },
        }
        save_draw(draw)
        return redirect(url_for('draw_page'))
    return render_template('setup.html')


@app.route('/draw')
def draw_page():
    draw = load_draw()
    if not draw:
        return redirect(url_for('setup'))
    teams = load_teams()
    n = len(draw['players'])
    for i, player in enumerate(draw['players']):
        player['color'] = PLAYER_COLORS[i % len(PLAYER_COLORS)]
    return render_template(
        'draw.html',
        draw=draw,
        teams=teams,
        total_teams=len(teams),
        base_per_player=len(teams) // n,
        extra_players=len(teams) % n,
    )


@app.route('/draw/random', methods=['POST'])
def draw_random():
    draw = load_draw()
    if not draw:
        return redirect(url_for('setup'))
    teams = load_teams()
    if API_KEY:
        fetched = fetch_teams_from_api()
        if fetched:
            teams = fetched
    player_names = [p['name'] for p in draw['players']]
    assignments = distribute_teams(teams, player_names)
    for player in draw['players']:
        player['teams'] = assignments[player['name']]
    save_draw(draw)
    return redirect(url_for('draw_page'))


@app.route('/draw/manual', methods=['POST'])
def draw_manual():
    draw = load_draw()
    if not draw:
        return redirect(url_for('setup'))
    team_names = request.form.getlist('team_name')
    team_players = request.form.getlist('team_player')
    assignments = {p['name']: [] for p in draw['players']}
    for team_name, player_name in zip(team_names, team_players):
        if player_name and player_name in assignments:
            assignments[player_name].append(team_name)
    for player in draw['players']:
        player['teams'] = assignments[player['name']]
    save_draw(draw)
    return redirect(url_for('dashboard'))


@app.route('/dashboard')
def dashboard():
    draw = load_draw()
    if not draw or not any(p.get('teams') for p in draw['players']):
        return redirect(url_for('draw_page'))

    eliminated = set(draw.get('tournament_state', {}).get('eliminated_teams', []))

    player_team_map = {}
    for i, player in enumerate(draw['players']):
        color = PLAYER_COLORS[i % len(PLAYER_COLORS)]
        player['color'] = color
        player['remaining_count'] = sum(1 for t in player['teams'] if t not in eliminated)
        for team in player['teams']:
            player_team_map[team] = color

    last_raw = draw.get('tournament_state', {}).get('last_updated')
    if last_raw:
        try:
            dt = datetime.fromisoformat(last_raw)
            last_updated_display = dt.strftime('%d %b %Y %H:%M UTC')
        except ValueError:
            last_updated_display = last_raw
    else:
        last_updated_display = 'NEVER'

    knockout_by_round = {}
    for match in draw.get('tournament_state', {}).get('knockout_matches', []):
        knockout_by_round.setdefault(match['round'], []).append(match)

    return render_template(
        'dashboard.html',
        draw=draw,
        eliminated=eliminated,
        player_team_map=player_team_map,
        last_updated_display=last_updated_display,
        knockout_by_round=knockout_by_round,
        round_order=ROUND_ORDER,
        round_display=ROUND_DISPLAY,
        tournament_start=TOURNAMENT_START,
    )


@app.route('/api/refresh', methods=['POST'])
def api_refresh():
    draw = load_draw()
    if not draw:
        return jsonify({'error': 'No draw found'}), 404
    if not can_refresh(draw):
        return jsonify({'status': 'cached', 'message': 'Refresh available in a few minutes'})
    draw, error = fetch_and_update_state(draw)
    if error:
        return jsonify({'status': 'error', 'message': error})
    return jsonify({'status': 'ok', 'state': draw['tournament_state']})


@app.route('/api/state')
def api_state():
    draw = load_draw()
    if not draw:
        return jsonify({'error': 'No draw found'}), 404
    return jsonify(draw)


@app.route('/reset', methods=['GET', 'POST'])
def reset():
    if request.method == 'POST':
        if os.path.exists(DRAW_FILE):
            os.remove(DRAW_FILE)
        return redirect(url_for('setup'))
    return render_template('reset.html')


if __name__ == '__main__':
    app.run(debug=True, port=5000)
