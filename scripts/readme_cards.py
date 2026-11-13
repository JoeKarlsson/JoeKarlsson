"""Draws the images on Joe's GitHub profile README, in joekarlsson.com's style.

    python scripts/readme_cards.py static    # header + homelab card (run by hand when they change)
    python scripts/readme_cards.py nightly   # stats card, newsletter card, latest posts (the Action runs this)

The scribbles copy the site exactly (scripts/scribbles.json and the CSS below come from
joekarlsson.com's src/data/scribbles.ts and src/styles/motion.css): same paths, one-pen
stroke timing, crayon line and boil. Under reduced motion they show fully drawn and still.
"""

import base64
import datetime
import json
import math
import os
import random
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
README = ROOT / "README.md"
LOGIN = "JoeKarlsson"
SITE = "https://www.joekarlsson.com"

PINK, INK, PAPER, GREY = "#ff4fd8", "#111111", "#ededed", "#8a8a8a"
SCRIBBLES = json.loads((ROOT / "scripts" / "scribbles.json").read_text())
CHALK = SCRIBBLES["CHALK"]
FONT = base64.b64encode((ASSETS / "fonts" / "Anton-subset.ttf").read_bytes()).decode()

STYLE = f"""<style>@font-face{{font-family:Anton;src:url(data:font/ttf;base64,{FONT})}}text{{font-family:Anton}}
.redraw path{{stroke-dasharray:1;stroke-dashoffset:1;animation:redraw var(--dur,7s) var(--del,0s) cubic-bezier(0.45,0.55,0.3,1) infinite}}
@keyframes redraw{{0%{{stroke-dashoffset:1}}35%,85%{{stroke-dashoffset:0}}100%{{stroke-dashoffset:-1}}}}
.redraw-strokes path{{stroke-dasharray:1;stroke-dashoffset:1;animation:redraw-stroke var(--dur,7s) calc(var(--del,0s) + var(--i,0) * var(--dur,7s) * min(0.045, 0.4 / var(--n,1))) infinite}}
@keyframes redraw-stroke{{0%{{stroke-dashoffset:1;animation-timing-function:cubic-bezier(0.3,0.6,0.4,1)}}4.5%,80%{{stroke-dashoffset:0;animation-timing-function:ease-in}}84%,100%{{stroke-dashoffset:-1}}}}
.led{{animation:blink var(--b) var(--d) steps(1) infinite}}@keyframes blink{{0%{{opacity:1}}50%{{opacity:.25}}}}
@media (prefers-reduced-motion:no-preference){{.redraw,.redraw-strokes{{filter:url(#boil)}}}}
@media (prefers-reduced-motion:reduce){{.redraw path,.redraw-strokes path{{animation:none;stroke-dashoffset:0}}.led{{animation:none}}}}</style>"""

DEFS = """<defs><filter id="crayon" x="-5%" y="-5%" width="110%" height="110%"><feTurbulence type="fractalNoise" baseFrequency="1.2" numOctaves="2" seed="3" result="n"/><feDisplacementMap in="SourceGraphic" in2="n" scale="2.5" result="d"/><feTurbulence type="fractalNoise" baseFrequency="2.2" seed="8" result="g"/><feColorMatrix in="g" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 -1.6 1.5" result="holes"/><feComposite in="d" in2="holes" operator="in"/></filter>
<filter id="boil" x="-25%" y="-25%" width="150%" height="150%"><feTurbulence type="turbulence" baseFrequency="0.02" numOctaves="1" seed="11" result="w"><animate attributeName="seed" values="11;22;33" dur="0.5s" calcMode="discrete" repeatCount="indefinite"/></feTurbulence><feDisplacementMap in="SourceGraphic" in2="w" scale="5"/></filter></defs>"""


def svg_open(width, height, title):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
        f"<title>{title}</title>{STYLE}{DEFS}"
        f'<rect width="{width}" height="{height}" rx="14" fill="{INK}"/>'
    )


def split_strokes(path):
    return [stroke.strip() for stroke in re.split(r"(?=M)", path) if stroke.strip()]


def scribble(path, x, y, width, height, color, duration, delay, view_box="0 0 900 300", stroke_width=8):
    """One self-drawing mark, as the site's Scribble component draws it."""
    strokes = split_strokes(path)
    several = len(strokes) > 1
    paths = "".join(
        f'<path pathLength="1" d="{d}"' + (f' style="--i:{i}"' if several else "") + "/>"
        for i, d in enumerate(strokes)
    )
    return (
        f'<svg class="{"redraw-strokes" if several else "redraw"}" style="--dur:{duration};--del:{delay};--n:{len(strokes)}" '
        f'x="{x:.0f}" y="{y:.0f}" width="{width:.0f}" height="{height:.0f}" viewBox="{view_box}" overflow="visible">'
        f'<g fill="none" stroke="{color}" stroke-width="{stroke_width}" stroke-linecap="round" stroke-linejoin="round" filter="url(#crayon)">{paths}</g></svg>'
    )


def arrow_between(start, tip, canvas, color, duration, delay):
    """The site's arrow, scaled and turned so its tail sits at `start` and its head at `tip`."""
    tail_x, tail_y, head_x, head_y = 90, 10, 630, 166  # in the arrow's own 760x170 drawing
    want = (tip[0] - start[0], tip[1] - start[1])
    scale = math.hypot(*want) / math.hypot(head_x - tail_x, head_y - tail_y)
    turn = math.atan2(want[1], want[0]) - math.atan2(head_y - tail_y, head_x - tail_x)
    cos, sin = math.cos(turn), math.sin(turn)

    def move(match):
        x, y = float(match.group(1)) - tail_x, float(match.group(2)) - tail_y
        return f"{start[0] + scale * (x * cos - y * sin):.1f},{start[1] + scale * (x * sin + y * cos):.1f}"

    moved = " ".join(re.sub(r"(-?[\d.]+),(-?[\d.]+)", move, s) for s in split_strokes(SCRIBBLES["arrow"]["path"]))
    width, height = canvas
    return scribble(moved, 0, 0, width, height, color, duration, delay, f"0 0 {width} {height}", max(4, 8 * scale))


# ---------- static cards ----------


def header_svg():
    width, height = 626, 506
    tally, hatch = SCRIBBLES["tally"], SCRIBBLES["hatch"]
    return (
        svg_open(width, height, "Joe Karlsson: I build weird things and show my work")
        + f'<text x="34" y="150" fill="{PAPER}" font-size="150">JOE</text>'
        + f'<text x="34" y="296" fill="{PAPER}" font-size="150" textLength="556" lengthAdjust="spacingAndGlyphs">KARLSSON</text>'
        + scribble(SCRIBBLES["HERO_COIL"], 12, 150, 590, 196, PINK, "9s", "0.3s")
        + scribble(tally["path"], width - 0.18 * width - 14, 14, 0.18 * width, 0.09 * height, CHALK, "9s", "0.6s", tally["viewBox"])
        + scribble(hatch["path"], width - 0.22 * width - 8, height - 0.16 * height - 8, 0.22 * width, 0.16 * height, PINK, "8s", "3.2s", hatch["viewBox"])
        + f'<text x="36" y="398" fill="{PAPER}" font-size="46">I BUILD WEIRD THINGS</text>'
        + f'<text x="36" y="456" fill="{PINK}" font-size="46">AND SHOW MY WORK</text></svg>'
    )


# A snapshot, not live data: counted from the homelab's services list on 2026-11-12
HOMELAB_NODES = [("NODE 1", 44), ("NODE 2", 30)]


def homelab_svg():
    width, height = 1252, 372
    random.seed(4)  # the same blink pattern every time the card is redrawn
    total = sum(count for _, count in HOMELAB_NODES)
    parts = [
        svg_open(width, height, f"Homelab: {total} self-hosted services on {len(HOMELAB_NODES)} Proxmox nodes"),
        f'<text x="44" y="96" fill="{PINK}" font-size="64">HOMELAB</text>',
        f'<text x="44" y="240" fill="{PAPER}" font-size="140">{total}</text>',
        f'<text x="44" y="278" fill="{PINK}" font-size="22" letter-spacing="1">SELF-HOSTED SERVICES</text>',
        f'<text x="44" y="308" fill="{GREY}" font-size="16" letter-spacing="1">{len(HOMELAB_NODES)} PROXMOX NODES · BACKED UP NIGHTLY</text>',
    ]
    rack_x, rack_width, rack_height = 448, 760, 110
    for row, (name, count) in enumerate(HOMELAB_NODES):
        y = 110 + row * 130
        parts.append(f'<rect x="{rack_x}" y="{y}" width="{rack_width}" height="{rack_height}" rx="8" fill="#1a1a1a" stroke="#2c2c2c"/>')
        parts += [f'<rect x="{rack_x + 16}" y="{y + 18 + i * 12}" width="70" height="4" rx="2" fill="#2c2c2c"/>' for i in range(7)]
        parts.append(f'<text x="{rack_x + 104}" y="{y + 34}" fill="{GREY}" font-size="16" letter-spacing="1">{name} · {count} SERVICES</text>')
        for i in range(count):
            parts.append(
                f'<circle class="led" cx="{rack_x + 112 + (i % 22) * 28}" cy="{y + 58 + (i // 22) * 20}" r="5" fill="{PINK}" '
                f'style="--b:{random.uniform(1.4, 4.5):.2f}s;--d:-{random.uniform(0, 4):.2f}s"/>'
            )
    # From the end of HOMELAB, down onto Node 1
    parts.append(arrow_between((284, 64), (612, 104), (width, height), CHALK, "9s", "1s"))
    return "".join(parts) + "</svg>"


# ---------- nightly: stats ----------


def github_graphql(query, variables=None):
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables or {}}).encode(),
        headers={"Authorization": f"bearer {os.environ['GH_TOKEN']}", "Content-Type": "application/json"},
    )
    body = json.load(urllib.request.urlopen(request, timeout=60))
    if body.get("errors"):
        raise RuntimeError(f"GitHub GraphQL error: {body['errors']}")
    return body["data"]


def github_rest(path):
    request = urllib.request.Request(
        f"https://api.github.com/{path}",
        headers={"Authorization": f"bearer {os.environ['GH_TOKEN']}", "Accept": "application/vnd.github+json"},
    )
    return json.load(urllib.request.urlopen(request, timeout=60))


def streaks(days, today):
    """Current and longest runs of days with contributions. `days` is [(iso date, count)] in order.
    Today with nothing yet doesn't break the current streak: the day isn't over."""
    days = [(day, count) for day, count in days if day <= today]
    longest = run = 0
    for _, count in days:
        run = run + 1 if count > 0 else 0
        longest = max(longest, run)
    current = 0
    index = len(days) - 1
    if index >= 0 and days[index][0] == today and days[index][1] == 0:
        index -= 1
    while index >= 0 and days[index][1] > 0:
        current += 1
        index -= 1
    return current, longest


def commit_hours(commits):
    """Commits per hour of the day, in the author's own timezone (the offset in their commit dates)."""
    hours = [0] * 24
    for date in commits:
        hours[datetime.datetime.fromisoformat(date).hour] += 1
    return hours


def fetch_stats():
    user = github_graphql(
        """query($login:String!){user(login:$login){createdAt contributionsCollection{contributionYears}
        repositories(ownerAffiliations:OWNER,privacy:PUBLIC,isFork:false,first:100){nodes{stargazerCount}}}}""",
        {"login": LOGIN},
    )["user"]
    years, days = {}, []
    for year in sorted(user["contributionsCollection"]["contributionYears"]):
        calendar = github_graphql(
            """query($login:String!,$from:DateTime!,$to:DateTime!){user(login:$login){
            contributionsCollection(from:$from,to:$to){contributionCalendar{totalContributions weeks{contributionDays{date contributionCount}}}}}}""",
            {"login": LOGIN, "from": f"{year}-01-01T00:00:00Z", "to": f"{year}-12-31T23:59:59Z"},
        )["user"]["contributionsCollection"]["contributionCalendar"]
        years[year] = calendar["totalContributions"]
        days += [(d["date"], d["contributionCount"]) for week in calendar["weeks"] for d in week["contributionDays"]]
    days = sorted(set(days))
    today = datetime.date.today().isoformat()
    current, longest = streaks(days, today)
    commits = []
    for page in range(1, 11):  # search returns at most 1,000 results
        items = github_rest(f"search/commits?q=author:{LOGIN}&sort=author-date&order=desc&per_page=100&page={page}")["items"]
        commits += [item["commit"]["author"]["date"] for item in items]
        if len(items) < 100:
            break
    return {
        "total": sum(years.values()),
        "since": user["createdAt"][:4],
        "years": years,
        "current": current,
        "longest": longest,
        "best_day": max(count for _, count in days),
        "stars": sum(repo["stargazerCount"] for repo in user["repositories"]["nodes"]),
        "hours": commit_hours(commits),
        "hour_sample": len(commits),
    }


def stats_svg(stats):
    width, height = 626, 506
    parts = [
        svg_open(width, height, f"{stats['total']:,} GitHub contributions since {stats['since']}"),
        f'<text x="40" y="112" fill="{PINK}" font-size="92">{stats["total"]:,}</text>',
        f'<text x="40" y="140" fill="{PAPER}" font-size="20" letter-spacing="1">CONTRIBUTIONS SINCE {stats["since"]}</text>',
    ]
    for x, number, label in [(40, stats["current"], "DAY STREAK"), (170, stats["longest"], "LONGEST STREAK"),
                             (320, stats["best_day"], "BEST DAY"), (450, stats["stars"], "STARS")]:
        parts.append(f'<text x="{x}" y="198" fill="{PAPER}" font-size="44">{number:,}</text>')
        parts.append(f'<text x="{x}" y="220" fill="{PINK}" font-size="14" letter-spacing="1">{label}</text>')
    years = sorted(stats["years"])
    tallest = max(stats["years"].values()) or 1
    left, top, chart_width, chart_height = 40, 250, width - 80, 120
    step = chart_width / len(years)
    for i, year in enumerate(years):
        bar = max(3, chart_height * stats["years"][year] / tallest)
        x = left + i * step
        parts.append(f'<rect x="{x + 3:.1f}" y="{top + chart_height - bar:.1f}" width="{step - 6:.1f}" height="{bar:.1f}" '
                     f'fill="{PINK if year == years[-1] else "#5c2350"}"/>')
        if year in (years[0], years[-1]):
            parts.append(f'<text x="{x + step / 2:.1f}" y="{top + chart_height + 18}" fill="{GREY}" font-size="13" text-anchor="middle">{year}</text>')
    parts.append(f'<text x="{left + chart_width - step - 18:.1f}" y="{top + 22}" fill="{PINK}" font-size="22" text-anchor="end">'
                 f'{stats["years"][years[-1]]:,} THIS YEAR</text>')
    strip_y = top + chart_height + 40
    parts.append(f'<text x="40" y="{strip_y + 4}" fill="{PAPER}" font-size="14" letter-spacing="1">WHEN I COMMIT</text>')
    busiest = max(stats["hours"]) or 1
    shades = ["#ff4fd8", "#d43bb4", "#a8388f", "#7a2a69", "#5c2350", "#3d1a37"]
    cell = (width - 80) / 24
    for hour, count in enumerate(stats["hours"]):
        color = "#262626" if count == 0 else shades[min(5, int((1 - count / busiest) * 6))]
        parts.append(f'<rect x="{40 + hour * cell + 1:.1f}" y="{strip_y + 14}" width="{cell - 2:.1f}" height="22" fill="{color}"/>')
    for hour, label in [(0, "MIDNIGHT"), (6, "6AM"), (12, "NOON"), (18, "6PM")]:
        parts.append(f'<text x="{40 + hour * cell + 1:.1f}" y="{strip_y + 54}" fill="{GREY}" font-size="12">{label}</text>')
    return "".join(parts) + "</svg>"


# ---------- nightly: newsletter ----------


def fetch_text(url, accept="text/html"):
    request = urllib.request.Request(url, headers={"Accept": accept, "User-Agent": "readme-cards"})
    return urllib.request.urlopen(request, timeout=60).read().decode()


def latest_issue(newsletter_markdown):
    """The newest Works on My Machine issue from the newsletter page's Markdown version:
    `- [![](card image)](issue url)Nov 12, 2026 [Title](issue url)`."""
    match = re.search(r"^- \[!\[[^\]]*\]\((?P<image>[^)]+)\)\]\((?P<url>[^)]+)\)(?P<date>[A-Z][a-z]{2} \d{1,2}, \d{4}) \[(?P<title>[^\]]+)\]",
                      newsletter_markdown, re.M)
    if not match:
        raise ValueError("No issue found on the newsletter page: its Markdown layout changed")
    return match.groupdict()


def wrap_words(text, width):
    lines, line = [], ""
    for word in text.split():
        if line and len(line) + 1 + len(word) > width:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    return lines + [line] if line else lines


def newsletter_svg(issue, image_bytes):
    width, height = 1252, 330
    underline = SCRIBBLES["underline"]
    image = base64.b64encode(image_bytes).decode()
    kind = "webp" if image_bytes[8:12] == b"WEBP" else "png" if image_bytes[:4] == b"\x89PNG" else "jpeg"
    title_lines = wrap_words(issue["title"].upper(), 20)[:3]
    parts = [
        svg_open(width, height, "Works on My Machine, Joe Karlsson's newsletter: subscribe"),
        f'<text x="44" y="70" fill="{GREY}" font-size="18" letter-spacing="2">THE NEWSLETTER</text>',
        f'<text x="44" y="150" fill="{PAPER}" font-size="78">WORKS ON MY</text>',
        f'<text x="44" y="226" fill="{PINK}" font-size="78">MACHINE</text>',
        scribble(underline["path"], 40, 222, 300, 40, PINK, "9s", "0.8s", underline["viewBox"]),
        f'<text x="44" y="280" fill="{PAPER}" font-size="20" letter-spacing="0.5">TECH WRITING, AI, HOMELAB BUILDS AND OPEN SOURCE</text>',
        f'<text x="44" y="306" fill="{GREY}" font-size="16" letter-spacing="0.5">FREE, AND EVERY ISSUE HAS AN UNSUBSCRIBE LINK</text>',
        f'<text x="700" y="70" fill="{GREY}" font-size="18" letter-spacing="2">LATEST ISSUE</text>',
        f'<image x="700" y="86" width="230" height="130" preserveAspectRatio="xMidYMid slice" href="data:image/{kind};base64,{image}"/>',
    ]
    for i, line in enumerate(title_lines):
        parts.append(f'<text x="948" y="{118 + i * 34}" fill="{PAPER}" font-size="30">{escape(line)}</text>')
    parts.append(f'<text x="948" y="{118 + len(title_lines) * 34 - 6}" fill="{GREY}" font-size="15">{issue["date"].upper()}</text>')
    parts.append(f'<rect x="700" y="244" width="508" height="58" rx="8" fill="{PINK}"/>')
    parts.append('<text x="954" y="285" fill="#000" font-size="30" text-anchor="middle" letter-spacing="1">SUBSCRIBE →</text>')
    return "".join(parts) + "</svg>"


def escape(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ---------- nightly: latest posts ----------

POSTS_START, POSTS_END = "<!-- POSTS:START -->", "<!-- POSTS:END -->"


def capture_latest_posts(count=4):
    """Screenshots the newest posts' thumbnails from joekarlsson.com's homepage, so they look
    exactly like the site (pink grading, tape, scribbles drawn in), and returns their titles and links."""
    from playwright.sync_api import sync_playwright

    posts = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1300, "height": 1000}, reduced_motion="reduce")
        page.goto(f"{SITE}/", wait_until="networkidle")
        page.add_style_tag(content="section > ul > li { border-color: transparent !important; }")  # row dividers
        heading = page.locator("h2").filter(has_text=re.compile(r"^\s*Recent posts\s*$"))  # stays found once hidden
        rows = heading.locator("xpath=..").locator(":scope > ul > li")
        if rows.count() < count:
            raise RuntimeError(f"Found {rows.count()} recent posts on the homepage, expected {count}: its layout changed")
        for i in range(count):
            row = rows.nth(i)
            # Marks hang over into neighboring rows (the newest post's NEW tag): show only this row
            rows.evaluate_all("(rows, keep) => rows.forEach((r, j) => r.style.visibility = j === keep ? 'visible' : 'hidden')", i)
            heading.evaluate("h => h.style.visibility = 'hidden'")
            row.scroll_into_view_if_needed()
            page.wait_for_timeout(1500)  # lazy images load and the halftone draws
            thumbnail = row.locator("a[aria-hidden='true']").first
            box, row_box = thumbnail.bounding_box(), row.bounding_box()
            pad = 26  # tape and scribbles reach past the picture, but stay inside the row so neighbors' marks don't show
            top = max(box["y"] - pad, row_box["y"])
            bottom = min(box["y"] + box["height"] + pad, row_box["y"] + row_box["height"])
            page.screenshot(path=str(ASSETS / "posts" / f"post-{i + 1}.png"),
                            clip={"x": box["x"] - pad, "y": top, "width": box["width"] + 2 * pad, "height": bottom - top})
            link = row.locator("div > a").first
            posts.append({"title": link.inner_text().strip(), "url": SITE + link.get_attribute("href")})
        browser.close()
    return posts


def posts_table(posts):
    cells = [
        f'<td width="50%" valign="top"><a href="{post["url"]}"><img src="assets/posts/post-{i + 1}.png" alt="" width="100%"></a><br>'
        f'<a href="{post["url"]}"><b>{escape(post["title"])}</b></a></td>'
        for i, post in enumerate(posts)
    ]
    rows = ["<tr>" + "".join(cells[i:i + 2]) + "</tr>" for i in range(0, len(cells), 2)]
    return "<table>" + "".join(rows) + "</table>"


def replace_between(text, start, end, new):
    if start not in text or end not in text:
        raise ValueError(f"README is missing the {start} / {end} markers")
    before, rest = text.split(start, 1)
    _, after = rest.split(end, 1)
    return f"{before}{start}\n{new}\n{end}{after}"


# ---------- commands ----------


def main(command):
    if command == "static":
        (ASSETS / "header.svg").write_text(header_svg())
        (ASSETS / "homelab.svg").write_text(homelab_svg())
    elif command == "nightly":
        (ASSETS / "stats.svg").write_text(stats_svg(fetch_stats()))
        issue = latest_issue(fetch_text(f"{SITE}/newsletter/", accept="text/markdown"))
        image = urllib.request.urlopen(urllib.request.Request(issue["image"], headers={"User-Agent": "readme-cards"}), timeout=60).read()
        (ASSETS / "newsletter.svg").write_text(newsletter_svg(issue, image))
        (ASSETS / "posts").mkdir(exist_ok=True)
        README.write_text(replace_between(README.read_text(), POSTS_START, POSTS_END, posts_table(capture_latest_posts())))
    else:
        raise SystemExit(f"Unknown command {command!r}: use static or nightly")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "")
