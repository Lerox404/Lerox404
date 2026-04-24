from datetime import date, datetime
from pathlib import Path
import json
import os
import urllib.request
import urllib.parse

API = 'https://api.github.com'
USER = os.getenv('GITHUB_USERNAME', 'Lerox404')
TOKEN = os.getenv('GITHUB_TOKEN', '')
DISPLAY = os.getenv('DISPLAY_NAME', 'Leon')
START_DATE = os.getenv('START_DATE', '2026-04-24')

OUT_SVG = Path('assets/profile-card.svg')
OUT_JSON = Path('assets/profile-data.json')
OUT_SVG.parent.mkdir(parents=True, exist_ok=True)

HEADERS = {
    'Accept': 'application/vnd.github+json',
    'User-Agent': 'profile-card-generator'
}
if TOKEN:
    HEADERS['Authorization'] = f'Bearer {TOKEN}'
    HEADERS['X-GitHub-Api-Version'] = '2022-11-28'

def esc(s: str) -> str:
    return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

def get_json(url: str):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode('utf-8'))

def paged(url: str):
    page = 1
    out = []
    while True:
        sep = '&' if '?' in url else '?'
        data = get_json(f'{url}{sep}per_page=100&page={page}')
        if not data:
            break
        out.extend(data)
        if len(data) < 100:
            break
        page += 1
    return out

def fmt_int(n: int) -> str:
    return f'{n:,}'

def fmt_big(n: int) -> str:
    sign = '-' if n < 0 else ''
    n = abs(n)
    if n >= 1_000_000:
        return f'{sign}{n/1_000_000:.2f}M'
    if n >= 1_000:
        return f'{sign}{n/1_000:.2f}K'
    return f'{sign}{n}'

def uptime_text(start_str: str) -> str:
    start = datetime.strptime(start_str, '%Y-%m-%d').date()
    today = date.today()
    delta = today - start
    years = delta.days // 365
    months = (delta.days % 365) // 30
    days = (delta.days % 365) % 30
    return f'{years} years, {months} months, {days} days'

def graphql(query: str, variables: dict):
    body = json.dumps({'query': query, 'variables': variables}).encode('utf-8')
    req = urllib.request.Request(f'{API}/graphql', data=body, headers={**HEADERS, 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode('utf-8'))

def total_commit_contributions(user: str) -> int:
    years_query = '''query($login:String!){ user(login:$login){ contributionsCollection { contributionYears } } }'''
    years_data = graphql(years_query, {'login': user})
    years = years_data['data']['user']['contributionsCollection']['contributionYears']
    total = 0
    q = '''query($login:String!,$from:DateTime!,$to:DateTime!){ user(login:$login){ contributionsCollection(from:$from,to:$to){ totalCommitContributions } } }'''
    for year in years:
        data = graphql(q, {
            'login': user,
            'from': f'{year}-01-01T00:00:00Z',
            'to': f'{year}-12-31T23:59:59Z'
        })
        total += data['data']['user']['contributionsCollection']['totalCommitContributions']
    return total

def fetch_stats(user: str):
    user_data = get_json(f'{API}/users/{urllib.parse.quote(user)}')
    repos = paged(f'{API}/users/{urllib.parse.quote(user)}/repos?sort=updated&type=owner')

    repo_count = len(repos)
    stars = sum(r.get('stargazers_count', 0) for r in repos)
    followers = user_data.get('followers', 0)
    created_at = user_data.get('created_at', '')[:10]

    code_bytes = 0
    for repo in repos:
        name = repo['name']
        owner = repo['owner']['login']
        try:
            langs = get_json(f'{API}/repos/{urllib.parse.quote(owner)}/{urllib.parse.quote(name)}/languages')
            if isinstance(langs, dict):
                code_bytes += sum(int(v) for v in langs.values())
        except Exception:
            pass

    try:
        commits = total_commit_contributions(user)
    except Exception:
        commits = 0

    return {
        'github_created_at': created_at,
        'public_repos': repo_count,
        'contributed_repos': repo_count,
        'stars': stars,
        'followers': followers,
        'commits': commits,
        'code_bytes': code_bytes,
    }

stats = fetch_stats(USER)
start = START_DATE if START_DATE else stats['github_created_at']
uptime = uptime_text(start)

OUT_JSON.write_text(json.dumps(stats, indent=2), encoding='utf-8')


ascii_art = [
"              %%##%%#",                                        
"           %%%%%%%%%#",                                       
"           %%%#*+++#%#",                                      
"          %%%%#++==++++   ######",                            
"          %%%###*+===**   %%%%%#=",                           
"          #%*****+++-*#   %%%%%%=-",                          
"            ++++*#=--*#   %##*#%+-",                          
"            ##+#**=-+*    %%%%*=--",                          
"              +*+*=-+%%   +++++==-:",                         
"            %%++++=-=#%#%#%%%#+==+#",                         
"         %%%%%*+++++*%%%%%%%#%##%%%##*",                      
"        %%%%%%#*+**#%%%%%%%%%%%%%%%%%*+",                     
"      %%%%%%%%%#####%%%%%%%%%%%%%%%%%#*",                     
"      %%%%%%%%%###%%%%%%%%%%%%%%%%%%%%#+",                    
"     %%%%%%%%%%##%%%%%%%%%%%%%%%%%%%%%#**",                   
"     %%%%%%%%%%#%%%#%%%%%%%%%%%%%%%%%%%%#",                   
"     %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%##",                  
"      %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%",                   
"      %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%",                    
"      %%%%%%%%%%%%%%%%%%%%%%%%%%%%",                         
"      %%%%%%%%%%%%%%%%%%%%%%%%%%%%%",                         
"       %%%%%%%%%%%%%%%#%%%%%%%%%%%%%",                        
"       %%@%%%%%%%%%%%%%%%%%%%%%%%%%%",                        
"        %%%%%%%%%%%%%%%%%%%%%%%%%%%%#",                       
"        %%%%%%%%%%%##%%%#%%%%%%%%%%%%",                       
"        %%%%%%%%%%%###%##%%%%%%%%%%%%%",                      
"         %%%%%%%%%%%%%%##%%%%%%%%%%%%%",                      
"         %%%%%%%%%%%%%####%%%%%%%%%%%%",                      
"          %%%%%%%%%%%%%##%%%%%%%%%%%%%",                      
"           %%%%%%%%@%%%%%%%%%%%%%%%%#",                       
"            %%%%%%%%%%%%%%%%%%%%%%%%%",                       
"             %%%%%%%%%%%%%%%%%%%%%%%%",                       
"               %%%%%%%%%%%%%%%%%%%%%%",                       
"               %%%%%%%%%%%%%%%%%%%%%%%",                      
"                 %%%%%%%%%%%%%%%%%%%%",                       
"                  %%%%%%%%%%%%%%%%%%%%",                      
"                   %%%%%%%%%%%%%%%%%%%%",                     
"                     %%%%%%%%%%%%%%%%%%",                     
"                       %%%%%%%%%%%%%%%%",                     
"                        %%%%%%%%%%%%%",                       
"                         %%%%%%%%%%%%%",                      
"                          %%%%%%%%%%%%" 
]

base_rows = [
    ('OS', 'Linux (OpenSUSE Tumbleweed), Windows 11'),
    ('Uptime', uptime),
    ('Host', f'{DISPLAY}, Inc.'),
    ('Kernel', 'IT-Student / Developer'),
    ('IDE', os.getenv('IDE', 'VS Code, Linux Terminal')),
    ('', ''),
    ('Languages.Programming', os.getenv('PROGRAMMING_LANGS', 'JavaScript, TypeScript, Python, SQL')),
    ('Languages.Computer', os.getenv('COMPUTER_LANGS', 'HTML, CSS, Git')),
    ('Languages.Real', os.getenv('REAL_LANGS', 'German, English C1')),
    ('', ''),
    ('Hobbies.Software', os.getenv('HOBBIES_SOFTWARE', 'Web Projects, Programming Projects')),
    ('Hobbies.Hardware', os.getenv('HOBBIES_HARDWARE', 'Embedded Systems')),
    ('Hobbies.Others', os.getenv('HOBBIES_OTHERS', 'grinding code and games')),
    ('', ''),
    ('Contact', ''),
    ('Discord', os.getenv('CONTACT_DISCORD', '.lerox.')),
    ('Email', os.getenv('CONTACT_EMAIL', 'lerox.github@gmail.com')),
    ('GitHub', USER),
]

def esc_ascii(s: str) -> str:
    return (
        str(s)
        .replace('&', '&amp;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
        .replace(' ', '&#160;')
    )


TEXT_X = 470
ASCII_X = 90
ASCII_FONT = 14
TEXT_FONT = 16
LINE_GAP = 28
ASCII_GAP = 14
LINE_WIDTH = 58

BOX_X = 35
BOX_Y = 75
BOX_W = 1130
BOX_H = 705

COLOR_PREFIX = "#8b949e"
COLOR_LABEL = "#e3a14f"
COLOR_VALUE = "#8cc2ff"
COLOR_TEXT = "#d0d7de"
COLOR_GREEN = "#22c55e"
COLOR_RED = "#ef4444"


def top_header_line(y, username, width=LINE_WIDTH):
    left = f'{username} '
    dashes = '─' * max(2, width - len(left))
    return (
        f'<text x="{TEXT_X}" y="{y}" font-size="{TEXT_FONT}" font-family="monospace">'
        f'<tspan fill="{COLOR_TEXT}">{esc(left)}</tspan>'
        f'<tspan fill="{COLOR_TEXT}">{dashes}</tspan>'
        f'</text>'
    )


def make_dots(left: str, right: str, width: int = LINE_WIDTH) -> str:
    return '.' * max(2, width - len(left) - len(right))


def normal_line(y, label, value, width=LINE_WIDTH):
    prefix = '.'
    label_text = f'{label}:'
    value_text = str(value)
    left_text = prefix + label_text
    dots = make_dots(left_text, value_text, width)
    return (
        f'<text x="{TEXT_X}" y="{y}" font-size="{TEXT_FONT}" font-family="monospace">'
        f'<tspan fill="{COLOR_PREFIX}">{esc(prefix)}</tspan>'
        f'<tspan fill="{COLOR_LABEL}">{esc(label_text)}</tspan>'
        f'<tspan fill="{COLOR_PREFIX}">{dots}</tspan>'
        f'<tspan fill="{COLOR_VALUE}">{esc(value_text)}</tspan>'
        f'</text>'
    )


def section_line(y, title, width=LINE_WIDTH):
    left = f'- {title} '
    dashes = '─' * max(2, width - len(left))
    return (
        f'<text x="{TEXT_X}" y="{y}" font-size="{TEXT_FONT}" font-family="monospace">'
        f'<tspan fill="{COLOR_TEXT}">{esc(left)}</tspan>'
        f'<tspan fill="{COLOR_PREFIX}">{dashes}</tspan>'
        f'</text>'
    )


def stats_pair_line(y, left_label, left_value, right_label=None, right_value=None):
    def part(label, value, width):
        prefix = '.'
        label_text = f'{label}:'
        value_text = str(value)
        left_text = prefix + label_text
        dots = '.' * max(2, width - len(left_text) - len(value_text))
        return (
            f'<tspan fill="{COLOR_PREFIX}">{esc(prefix)}</tspan>'
            f'<tspan fill="{COLOR_LABEL}">{esc(label_text)}</tspan>'
            f'<tspan fill="{COLOR_PREFIX}">{dots}</tspan>'
            f'<tspan fill="{COLOR_VALUE}">{esc(value_text)}</tspan>'
        )

    if right_label is None:
        content = part(left_label, left_value, 58)
    else:
        content = (
            part(left_label, left_value, 27) +
            f'<tspan fill="{COLOR_PREFIX}"> | </tspan>' +
            part(right_label, right_value, 23)
        )

    return (
        f'<text x="{TEXT_X}" y="{y}" font-size="{TEXT_FONT}" font-family="monospace">'
        f'{content}'
        f'</text>'
    )


def code_size_line(y, bytes_total, width=58):
    prefix = '.'
    label_text = 'GitHub LOC:'
    value_text = fmt_big(bytes_total)
    left_text = prefix + label_text
    dots = '.' * max(2, width - len(left_text) - len(value_text))
    return (
        f'<text x="{TEXT_X}" y="{y}" font-size="{TEXT_FONT}" font-family="monospace">'
        f'<tspan fill="{COLOR_PREFIX}">{esc(prefix)}</tspan>'
        f'<tspan fill="{COLOR_LABEL}">{esc(label_text)}</tspan>'
        f'<tspan fill="{COLOR_PREFIX}">{dots}</tspan>'
        f'<tspan fill="{COLOR_VALUE}">{esc(value_text)}</tspan>'
        f'</text>'
    )


ascii_height = len(ascii_art) * ASCII_GAP
base_row_count = sum(1 for label, value in base_rows if not (label == '' and value == ''))
blank_row_count = sum(1 for label, value in base_rows if label == '' and value == '')
right_height = 30 + base_row_count * LINE_GAP + blank_row_count * 20 + 18 + 30 + 3 * LINE_GAP
content_height = max(ascii_height, right_height)
content_start_y = BOX_Y + (BOX_H - content_height) / 2

svg_lines = []

art_y = content_start_y + 10
for art in ascii_art:
    svg_lines.append(
        f'<text x="{ASCII_X}" y="{art_y}" font-size="{ASCII_FONT}" font-family="monospace" fill="#c9d1d9" xml:space="preserve">{esc_ascii(art)}</text>'
    )
    art_y += ASCII_GAP

y = content_start_y + 6
header_name = f'{USER}@github'
svg_lines.append(top_header_line(y, header_name))
y += 30

for label, value in base_rows:
    if label == '' and value == '':
        y += 20
        continue
    if label == 'Contact':
        svg_lines.append(section_line(y, label))
    else:
        svg_lines.append(normal_line(y, label, value))
    y += LINE_GAP

y += 18
svg_lines.append(section_line(y, 'GitHub Stats'))
y += 30

svg_lines.append(stats_pair_line(
    y,
    'Repos',
    f'{fmt_int(stats["public_repos"])} {{Contributed: {fmt_int(stats["contributed_repos"])}}}',
    'Stars',
    fmt_int(stats["stars"])
))
y += LINE_GAP

svg_lines.append(stats_pair_line(
    y,
    'Commits',
    fmt_int(stats["commits"]),
    'Followers',
    fmt_int(stats["followers"])
))
y += LINE_GAP

svg_lines.append(code_size_line(y, stats["code_bytes"]))

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="860" viewBox="0 0 1200 860" role="img" aria-label="Profile card for {esc(DISPLAY)}">
  <rect width="1200" height="860" fill="#081019"/>
  <text x="35" y="42" font-family="monospace" font-size="24" fill="#dde6f3">{esc(DISPLAY)} / README.md</text>
  <rect x="{BOX_X}" y="{BOX_Y}" width="{BOX_W}" height="{BOX_H}" rx="18" fill="#111a24"/>
  <g font-family="monospace">
    {''.join(svg_lines)}
  </g>
</svg>'''

OUT_SVG.write_text(svg, encoding='utf-8')