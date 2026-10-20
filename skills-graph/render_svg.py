"""Renders the skills graph as an animated SVG (rotating 3D projection) for the README.

GitHub READMEs can't run JavaScript, so this precomputes a 3D force layout and
animates its rotation with SMIL. Keep the data in sync with src.js.

Usage: python3 skills-graph/render_svg.py  ->  assets/skills-graph.svg
"""
import math
import random
from pathlib import Path

# ---------- data (mirror of src.js) ----------
GROUPS = {
    'me':       ('#ffffff', 'Gusta'),
    'lang':     ('#58a6ff', 'Languages'),
    'backend':  ('#3fb950', 'Backend'),
    'frontend': ('#d2a8ff', 'Frontend'),
    'data':     ('#f0883e', 'Data & AI'),
    'tools':    ('#ff7b72', 'DevOps & Tools'),
}

SKILLS = {
    'lang':     ['Java', 'Python', 'C', 'C#', 'TypeScript', 'JavaScript', 'Haskell', 'R'],
    'backend':  ['Spring Boot', 'Flask', 'Node.js', 'REST / OpenAPI'],
    'frontend': ['React', 'HTML', 'CSS'],
    'data':     ['MySQL', 'PostgreSQL', 'Graphs', 'Machine Learning', 'Expert Systems'],
    'tools':    ['Docker', 'Linux', 'Git'],
}

RELATED = [
    ('Java', 'Spring Boot'), ('Spring Boot', 'PostgreSQL'), ('Spring Boot', 'REST / OpenAPI'),
    ('Spring Boot', 'Docker'), ('Spring Boot', 'MySQL'), ('Java', 'Graphs'),
    ('Python', 'Flask'), ('Flask', 'MySQL'), ('Flask', 'HTML'),
    ('TypeScript', 'React'), ('JavaScript', 'React'), ('TypeScript', 'JavaScript'),
    ('JavaScript', 'Node.js'), ('React', 'CSS'), ('HTML', 'CSS'),
    ('Python', 'Machine Learning'), ('C#', 'Expert Systems'),
    ('PostgreSQL', 'Graphs'), ('Docker', 'Linux'), ('Git', 'Linux'), ('C', 'Linux'),
]

# ---------- graph ----------
nodes = {'Gusta': {'group': 'me', 'kind': 'root'}}
links = []
for g, items in SKILLS.items():
    hub = GROUPS[g][1]
    nodes[hub] = {'group': g, 'kind': 'hub'}
    links.append(('Gusta', hub, 'hub'))
    for s in items:
        nodes[s] = {'group': g, 'kind': 'skill'}
        links.append((hub, s, 'member'))
links += [(a, b, 'related') for a, b in RELATED]

# ---------- 3D force layout ----------
random.seed(7)
pos = {n: [random.uniform(-60, 60) for _ in range(3)] for n in nodes}
pos['Gusta'] = [0.0, 0.0, 0.0]
DIST = {'hub': 55, 'member': 32, 'related': 60}
STRENGTH = {'hub': 1.0, 'member': 1.0, 'related': 0.05}
names = list(nodes)
for it in range(600):
    alpha = 1 - it / 600
    force = {n: [0.0, 0.0, 0.0] for n in names}
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            d = [pos[a][k] - pos[b][k] for k in range(3)]
            r2 = max(sum(x * x for x in d), 1.0)
            f = 1800 / r2
            for k in range(3):
                force[a][k] += d[k] * f
                force[b][k] -= d[k] * f
    for a, b, kind in links:
        d = [pos[b][k] - pos[a][k] for k in range(3)]
        r = max(math.sqrt(sum(x * x for x in d)), 0.01)
        f = (r - DIST[kind]) / r * STRENGTH[kind] * 0.5
        for k in range(3):
            force[a][k] += d[k] * f
            force[b][k] -= d[k] * f
    for n in names:
        if n == 'Gusta':
            continue
        for k in range(3):
            pos[n][k] += max(-8, min(8, force[n][k] * 0.3 * alpha))

# ---------- projection ----------
W, H = 900, 560
FRAMES, DUR = 90, 60  # one full turn per minute
radius = max(math.hypot(p[0], p[2]) for p in pos.values()) + 20
CAM = radius * 3.2
scale = 1.0


def project(p, a):
    x = p[0] * math.cos(a) + p[2] * math.sin(a)
    z = -p[0] * math.sin(a) + p[2] * math.cos(a)
    persp = CAM / (CAM - z)
    return W / 2 + x * scale * persp, H / 2 + p[1] * scale * persp, z


# fit the widest projection of any frame inside the canvas (with room for labels)
unit = [project(p, 2 * math.pi * f / FRAMES) for p in pos.values() for f in range(FRAMES)]
scale = min((W / 2 - 80) / max(abs(x - W / 2) for x, _, _ in unit),
            (H / 2 - 24) / max(abs(y - H / 2) for _, y, _ in unit))


frames = {n: [project(pos[n], 2 * math.pi * f / FRAMES) for f in range(FRAMES + 1)] for n in names}


def values(seq):
    return ';'.join(f'{v:.1f}' for v in seq)


def anim(attr, seq):
    return f'<animate attributeName="{attr}" dur="{DUR}s" repeatCount="indefinite" values="{values(seq)}"/>'


def depth_opacity(n, lo, hi):
    return [lo + (hi - lo) * (z + radius) / (2 * radius) for _, _, z in frames[n]]


def esc(s):
    return s.replace('&', '&amp;')


color = {n: GROUPS[v['group']][0] for n, v in nodes.items()}
out = [
    f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
    'font-family="JetBrains Mono, Fira Code, Menlo, Consolas, monospace">',
    '<defs><radialGradient id="bg" cx="50%" cy="45%" r="70%">'
    '<stop offset="0%" stop-color="#161b22"/><stop offset="100%" stop-color="#0d1117"/></radialGradient></defs>',
    f'<rect width="{W}" height="{H}" rx="12" fill="url(#bg)"/>',
]

# links (static line + slow flowing particle on hub/member links)
for a, b, kind in links:
    stroke = 'rgba(201,209,217,0.35)' if kind == 'related' else color[b]
    width = {'hub': 1.4, 'member': 0.8, 'related': 0.5}[kind]
    xy = [anim(f'{k}1', [f[i] for f in frames[a]]) + anim(f'{k}2', [f[i] for f in frames[b]])
          for i, k in enumerate('xy')]
    out.append(f'<line stroke="{stroke}" stroke-width="{width}" stroke-opacity="0.55">{"".join(xy)}</line>')
    if kind != 'related':
        out.append(
            f'<line stroke="{color[b]}" stroke-width="2.6" stroke-linecap="round" pathLength="100" '
            f'stroke-dasharray="0.1 99.9">{"".join(xy)}'
            f'<animate attributeName="stroke-dashoffset" from="100" to="0" dur="{random.uniform(9, 14):.1f}s" '
            'repeatCount="indefinite"/></line>'
        )

# labels
SIZE = {'root': 20, 'hub': 13, 'skill': 11}
for n in sorted(names, key=lambda n: {'skill': 0, 'hub': 1, 'root': 2}[nodes[n]['kind']]):
    kind = nodes[n]['kind']
    xs, ys = [f[0] for f in frames[n]], [f[1] for f in frames[n]]
    op = anim('opacity', depth_opacity(n, 0.45, 1.0)) if kind == 'skill' else ''
    out.append(f'<g>{op}')
    if kind != 'skill':
        w, h = len(n) * SIZE[kind] * 0.62 + 14, SIZE[kind] + 10
        fill = 'rgba(88,166,255,0.18)' if kind == 'root' else 'rgba(13,17,23,0.85)'
        out.append(
            f'<rect width="{w:.1f}" height="{h}" rx="4" fill="{fill}" stroke="{color[n]}" stroke-width="1">'
            f'{anim("x", [x - w / 2 for x in xs])}{anim("y", [y - h / 2 for y in ys])}</rect>'
        )
    weight = 500 if kind == 'skill' else 700
    out.append(
        f'<text font-size="{SIZE[kind]}" font-weight="{weight}" fill="{color[n]}" text-anchor="middle" '
        f'dominant-baseline="central">{anim("x", xs)}{anim("y", ys)}{esc(n)}</text></g>'
    )

out.append('</svg>')
dest = Path(__file__).resolve().parent.parent / 'assets' / 'skills-graph.svg'
dest.write_text('\n'.join(out))
print(f'wrote {dest} ({dest.stat().st_size // 1024} KB)')
