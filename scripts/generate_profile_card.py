from datetime import date, datetime
from pathlib import Path
import json
import os
import urllib.request
import urllib.parse

API = 'https://api.github.com'
USER = os.getenv('GITHUB_USERNAME', 'YOUR_GITHUB_USERNAME')
TOKEN = os.getenv('GITHUB_TOKEN', '')
DISPLAY = os.getenv('DISPLAY_NAME', 'Leon')
START_DATE = os.getenv('START_DATE', '2024-08-01')

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

    additions = 0
    deletions = 0
    counted_repos = 0
    for repo in repos:
        name = repo['name']
        owner = repo['owner']['login']
        try:
            freq = get_json(f'{API}/repos/{urllib.parse.quote(owner)}/{urllib.parse.quote(name)}/stats/code_frequency')
            if isinstance(freq, list):
                counted_repos += 1
                for week in freq:
                    if len(week) >= 3:
                        additions += max(0, int(week[1]))
                        deletions += abs(min(0, int(week[2])))
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
        'loc_total': additions + deletions,
        'loc_added': additions,
        'loc_deleted': deletions,
        'loc_counted_repos': counted_repos,
    }

stats = fetch_stats(USER)
start = START_DATE if START_DATE else stats['github_created_at']
uptime = uptime_text(start)

OUT_JSON.write_text(json.dumps(stats, indent=2), encoding='utf-8')

ascii_art = [
"               .",
"            .*%%%##",
"          %@@@%%@%#",
"       =:.*:@@@@@@@%",
"     *#++*+@%@@@-*@%@@=",
"  %@%#*##@@@*%@##%@@@=",
" @@@@@.=@%@@#*#*@@@@=",
"%@@@%@--.:@@@#**--=@+=",
"@@@@@@@@@@@@@@@@*****%@@%#",
"@@@@@@@@@@@@@@-@@@**@@@@@@%@*%@",
"%@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@",
" .@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@",
"    @@@@@@@@@@@@@@@@@@@@@@@@@@%.",
"       @@@@@@@@@@@@@@@@@@@@@@:.",
"         @@@@@@@@@@@@@@@@@@@",
"          *@@@@@@@@@@@@@@@@",
"           @@@@@@@@@@@@@@@%",
"           .@@@@@@@@@@@@@@*",
"           .-@@@@@@@@@@@@@=",
"            -@@@@@@@@@@@@@*",
"            =:%@@@@@@@@@@@%",
"            =:*@@@@@@@@@@@%=",
"             .==%@@@@@@@@@@@%",
"              ==-.@@@@@@@@@@@%-"
]

base_rows = [
    ('OS', 'Linux (Fedora KDE)'),
    ('Uptime', uptime),
    ('Host', f'{DISPLAY}, Inc.'),
    ('Kernel', 'IT-Umschueler / Developer'),
    ('IDE', os.getenv('IDE', 'VS Code, Linux Terminal')),
    ('', ''),
    ('Languages.Programming', os.getenv('PROGRAMMING_LANGS', 'JavaScript, TypeScript, Python, SQL')),
    ('Languages.Computer', os.getenv('COMPUTER_LANGS', 'HTML, CSS, React, Vue, Git')),
    ('Languages.Real', os.getenv('REAL_LANGS', 'German, English')),
    ('', ''),
    ('Hobbies.Software', os.getenv('HOBBIES_SOFTWARE', 'Web Projects, Frontend, Databases')),
    ('Hobbies.Hardware', os.getenv('HOBBIES_HARDWARE', 'Linux, PCs, Troubleshooting')),
    ('Hobbies.Others', os.getenv('HOBBIES_OTHERS', 'RPGs, Soulslikes, FFXIV, LoL, Shooter')),
    ('', ''),
    ('Contact', ''),
    ('Discord', os.getenv('CONTACT_DISCORD', 'dein_discord')),
    ('Email', os.getenv('CONTACT_EMAIL', 'deine@mail.de')),
    ('GitHub', USER),
]

def normal_line(y, label, value):
    return (
        f'<text x="410" y="{y}" font-size="16">'
        f'<tspan fill="#8ba0b8">. </tspan>'
        f'<tspan fill="#e59b4c">{esc(label)}</tspan>'
        f'<tspan fill="#8ba0b8">: .......................... </tspan>'
        f'<tspan fill="#d6deeb">{esc(value)}</tspan>'
        f'</text>'
    )

def section_line(y, title):
    return f'<text x="410" y="{y}" font-size="16" fill="#d8e0ea">- {esc(title)} <tspan fill="#708197">------------------------------------------------</tspan></text>'

svg_lines = []
y = 95
for art in ascii_art:
    svg_lines.append(f'<text x="70" y="{y}" font-size="16" fill="#d6deeb">{esc(art)}</text>')
    y += 16

y = 90
for label, value in base_rows:
    if label == '' and value == '':
        y += 20
        continue
    if label == 'Contact':
        svg_lines.append(section_line(y, label))
    else:
        svg_lines.append(normal_line(y, label, value))
    y += 28

y += 18
svg_lines.append(section_line(y, 'GitHub Stats'))
y += 30
svg_lines.append(
    f'<text x="410" y="{y}" font-size="16">'
    f'<tspan fill="#8ba0b8">. </tspan><tspan fill="#e59b4c">Repos</tspan><tspan fill="#8ba0b8">: ........................... </tspan>'
    f'<tspan fill="#d6deeb">{fmt_int(stats["public_repos"])} {{Contributed: {fmt_int(stats["contributed_repos"])}}}  |  </tspan>'
    f'<tspan fill="#e59b4c">Stars</tspan><tspan fill="#8ba0b8">: ......... </tspan><tspan fill="#d6deeb">{fmt_int(stats["stars"])} </tspan>'
    f'</text>'
)
y += 28
svg_lines.append(
    f'<text x="410" y="{y}" font-size="16">'
    f'<tspan fill="#8ba0b8">. </tspan><tspan fill="#e59b4c">Commits</tspan><tspan fill="#8ba0b8">: ......................... </tspan>'
    f'<tspan fill="#d6deeb">{fmt_int(stats["commits"])}                    |  </tspan>'
    f'<tspan fill="#e59b4c">Followers</tspan><tspan fill="#8ba0b8">: ..... </tspan><tspan fill="#d6deeb">{fmt_int(stats["followers"])} </tspan>'
    f'</text>'
)
y += 28
svg_lines.append(
    f'<text x="410" y="{y}" font-size="16">'
    f'<tspan fill="#8ba0b8">. </tspan><tspan fill="#e59b4c">GitHub LOC</tspan><tspan fill="#8ba0b8">: ...................... </tspan>'
    f'<tspan fill="#d6deeb">{fmt_int(stats["loc_total"])}  (</tspan>'
    f'<tspan fill="#22c55e">+{fmt_big(stats["loc_added"])} </tspan>'
    f'<tspan fill="#d6deeb">, </tspan>'
    f'<tspan fill="#ef4444">-{fmt_big(stats["loc_deleted"])} </tspan>'
    f'<tspan fill="#d6deeb">)</tspan>'
    f'</text>'
)

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="860" viewBox="0 0 1200 860" role="img" aria-label="Profile card for {esc(DISPLAY)}">
  <rect width="1200" height="860" fill="#081019"/>
  <text x="35" y="42" font-family="monospace" font-size="24" fill="#dde6f3">{esc(DISPLAY)} / README.md</text>
  <text x="1148" y="42" text-anchor="end" font-family="monospace" font-size="24" fill="#dde6f3">✎</text>
  <rect x="35" y="75" width="1130" height="705" rx="18" fill="#111a24"/>
  <g font-family="monospace">
    {''.join(svg_lines)}
  </g>
  <rect x="0" y="805" width="1200" height="55" fill="#2e2e2e"/>
  <text x="45" y="841" font-family="system-ui, sans-serif" font-size="22" font-weight="700" fill="#f1f1f1">Posted in r/coolgithubprojects by u/{esc(USER)}</text>
  <text x="1160" y="841" text-anchor="end" font-family="system-ui, sans-serif" font-size="20" font-weight="700" fill="#ffffff">reddit</text>
</svg>'''

OUT_SVG.write_text(svg, encoding='utf-8')
