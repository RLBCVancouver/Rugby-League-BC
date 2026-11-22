#!/usr/bin/env python3
"""Builds the Rugby League BC website.

Page text lives in pages/*.html. Editable content lives in data/*.json (edited
through Pages CMS). This script wraps every page in the shared header and footer,
fills in the data-driven parts ({{name}} markers), generates one page per club and
per news article, and writes the finished site to dist/.

Netlify runs this on every deploy. If anything in the data is invalid the build
fails and the previous version of the site stays live.
"""
import json, re, html, os, shutil, struct, datetime, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)
OUT = 'dist'
SITE = (os.environ.get('SITE_URL') or os.environ.get('URL') or 'https://www.rugbyleaguebc.ca').rstrip('/')
ORG = 'Rugby League BC'
esc = lambda x: html.escape(str(x), quote=True)


def load(name):
    with open(os.path.join('data', name), encoding='utf-8') as f:
        return json.load(f)


def need(cond, msg):
    if not cond:
        sys.exit('DATA ERROR: ' + msg)


def parse_date(v, what):
    try:
        return datetime.date.fromisoformat(str(v)[:10])
    except ValueError:
        sys.exit(f'DATA ERROR: {what} date "{v}" is not a valid date (use YYYY-MM-DD)')


def slugify(t):
    return re.sub(r'[^a-z0-9]+', '-', str(t).lower()).strip('-')


# ---------- images ----------
def img_size(src):
    p = src.lstrip('/')
    if not os.path.isfile(p):
        return None
    try:
        with open(p, 'rb') as f:
            d = f.read(64)
        if d[:8] == b'\x89PNG\r\n\x1a\n':
            return struct.unpack('>II', d[16:24])
        if d[:4] == b'RIFF' and d[8:12] == b'WEBP':
            k = d[12:16]
            if k == b'VP8 ':
                return struct.unpack('<HH', d[26:30])[0] & 0x3fff, struct.unpack('<HH', d[26:30])[1] & 0x3fff
            if k == b'VP8L':
                b = struct.unpack('<I', d[21:25])[0]
                return (b & 0x3fff) + 1, ((b >> 14) & 0x3fff) + 1
            if k == b'VP8X':
                return int.from_bytes(d[24:27], 'little') + 1, int.from_bytes(d[27:30], 'little') + 1
    except Exception:
        pass
    return None


def img(src, alt, cls='', lazy=True):
    wh = img_size(src)
    dim = f' width="{wh[0]}" height="{wh[1]}"' if wh else ''
    c = f' class="{cls}"' if cls else ''
    l = ' loading="lazy" decoding="async"' if lazy else ''
    return f'<img src="{esc(src)}" alt="{esc(alt)}"{dim}{c}{l}>'


FIT_LOGOS = ('club-valley-warriors',)  # wide crossed-swords crest: fill more of the circle


def tile(logo, name, cls=''):
    if logo and any(f in logo for f in FIT_LOGOS):
        cls = (cls + ' tile-fit').strip()
    return f'<span class="tile {cls}">{img(logo, name)}</span>'


CHEV = ('<svg class="chev" viewBox="0 0 1440 110" preserveAspectRatio="none" aria-hidden="true" focusable="false">'
        '<polygon class="c1" points="0,18 720,68 1440,18 1440,32 720,82 0,32"/>'
        '<polygon class="c2" points="0,32 720,82 1440,32 1440,46 720,96 0,46"/>'
        '<polygon class="c3" points="0,46 720,96 1440,46 1440,60 720,110 0,60"/>'
        '<polygon class="c0" points="0,60 720,110 1440,60 1440,111 0,111"/></svg>')

NAV = [('/fixtures/', 'Fixtures & results'), ('/competitions/', 'Competitions'), ('/clubs/', 'Clubs'),
       ('/representative-teams/', 'Rep teams'), ('/get-involved/', 'Get involved'), ('/news/', 'News'), ('/about/', 'About')]
NAV_MORE = [('/gallery/', 'Gallery'), ('/rugby-league-explained/', 'Rugby league explained'), ('/faq/', 'FAQ'), ('/partners/', 'Partners'), ('/contact/', 'Contact')]


def fmt_date(d, year=False, wk=True):
    s = (d.strftime('%a ') if wk else '') + d.strftime('%b ') + str(d.day)
    return s + (f', {d.year}' if year else '')


# ---------- data-driven parts ----------
class Data:
    def __init__(self):
        self.settings = load('settings.json')
        self.clubs_file = load('clubs.json')
        self.clubs = self.clubs_file['clubs']
        self.fx = load('fixtures.json')
        self.honours = load('honours.json')['seasons']
        self.board = load('board.json')['people']
        self.partners = load('partners.json')
        self.news = load('news.json')['articles']
        self.gallery = load('gallery.json')['photos']
        self.faq = load('faq.json')['items']
        self.by_id = {}
        for c in self.clubs:
            need(c.get('id') and c.get('name') and c.get('slug') and c.get('logo'), 'every club needs an id, name, slug and logo')
            need(c['id'] not in self.by_id, f'two clubs share the id "{c["id"]}"')
            self.by_id[c['id']] = c
        # match clubs by id, short name or full name so the editor can type any of them
        self.lookup = {}
        for c in self.clubs:
            for k in (c['id'], c.get('short', ''), c['name']):
                if k:
                    self.lookup[k.strip().lower()] = c['id']
        self.matches = []
        for m in self.fx.get('matches') or []:
            need(m.get('date') and m.get('home') and m.get('away'), 'every match needs a date, a home team and an away team')
            d = parse_date(m['date'], 'match')
            self.matches.append(dict(m, _d=d))
        self.matches.sort(key=lambda m: m['_d'])
        for a in self.news:
            need(a.get('title'), 'every news article needs a title')
            a['slug'] = a.get('slug') or slugify(a['title'])
        need(len({a['slug'] for a in self.news}) == len(self.news), 'two news articles share the same slug')

    def team(self, key):
        cid = self.lookup.get(str(key).strip().lower())
        if cid:
            c = self.by_id[cid]
            return {'id': cid, 'name': c['name'], 'short': c.get('short') or c['name'], 'logo': c['logo'], 'url': f'/clubs/{c["slug"]}/'}
        return {'id': slugify(key), 'name': str(key), 'short': str(key), 'logo': '', 'url': ''}


def is_num(v):
    return str(v).strip().isdigit()


def r_match(D, m):
    h, a = D.team(m['home']), D.team(m['away'])
    played = is_num(m.get('home_score', '')) and is_num(m.get('away_score', ''))
    if played:
        hs, as_ = int(m['home_score']), int(m['away_score'])
        mid = (f'<div class="mx-score"><b class="{"w" if hs > as_ else ""}">{hs}</b><i aria-hidden="true">–</i>'
               f'<b class="{"w" if as_ > hs else ""}">{as_}</b></div>')
    else:
        mid = f'<div class="mx-score mx-up">{esc(m.get("time") or "vs")}</div>'

    def side(t, cls):
        crest = tile(t['logo'], '', 'tile-s') if t['logo'] else '<span class="tile tile-s tile-blank" aria-hidden="true"></span>'
        nm = f'<a href="{t["url"]}">{esc(t["name"])}</a>' if t['url'] else esc(t['name'])
        return f'<div class="mx-team {cls}">{crest}<span>{nm}</span></div>'
    meta = ' · '.join(esc(x) for x in (m.get('venue'), m.get('note')) if x)
    meta = f'<p class="mx-meta">{meta}</p>' if meta else ''
    return f'<li class="mx" data-teams="{esc(h["id"])} {esc(a["id"])}">{side(h, "mx-home")}{mid}{side(a, "mx-away")}{meta}</li>'


def r_results(D, only=None):
    """Matches grouped by round, in the order they were played."""
    groups = []
    for m in D.matches:
        if only and only not in (D.team(m['home'])['id'], D.team(m['away'])['id']):
            continue
        key = (m['_d'], m.get('round') or '')
        if not groups or groups[-1][0] != key:
            groups.append((key, []))
        groups[-1][1].append(m)
    if not groups:
        return '<p class="empty">No matches listed yet. Check back once the draw is confirmed.</p>'
    out = []
    for (d, rnd), ms in groups:
        final = 'final' in rnd.lower()
        out.append(f'<section class="rd{" rd-final" if final else ""}"><h3 class="rd-h"><span>{esc(rnd) or "Match"}</span>'
                   f'<time datetime="{d.isoformat()}">{fmt_date(d, year=True)}</time></h3><ol class="mxs">'
                   + ''.join(r_match(D, m) for m in ms) + '</ol></section>')
    return ''.join(out)


def ladder_rows(D):
    t = {}
    for m in D.matches:
        if not str(m.get('round', '')).lower().startswith('round'):
            continue
        if not (is_num(m.get('home_score', '')) and is_num(m.get('away_score', ''))):
            continue
        h, a = D.team(m['home']), D.team(m['away'])
        hs, as_ = int(m['home_score']), int(m['away_score'])
        for me, f, ag in ((h, hs, as_), (a, as_, hs)):
            r = t.setdefault(me['id'], {'t': me, 'p': 0, 'w': 0, 'l': 0, 'd': 0, 'pf': 0, 'pa': 0})
            r['p'] += 1; r['pf'] += f; r['pa'] += ag
            r['w' if f > ag else 'l' if f < ag else 'd'] += 1
    return sorted(t.values(), key=lambda r: (-r['w'], -r['d'], -(r['pf'] - r['pa']), -r['pf'], r['t']['name']))


def r_ladder(D, compact=False):
    rows = ladder_rows(D)
    if not rows:
        return '<p class="empty">The ladder appears here once results are in.</p>'
    body = ''
    for i, r in enumerate(rows, 1):
        tm = r['t']
        diff = r['pf'] - r['pa']
        nm = f'<a href="{tm["url"]}">{esc(tm["name"])}</a>' if tm['url'] else esc(tm['name'])
        crest = tile(tm['logo'], '', 'tile-xs') if tm['logo'] else ''
        extra = '' if compact else f'<td>{r["d"]}</td><td>{r["pf"]}</td><td>{r["pa"]}</td>'
        body += (f'<tr><td class="pos">{i}</td><th scope="row">{crest}<span>{nm}</span></th><td>{r["p"]}</td><td>{r["w"]}</td><td>{r["l"]}</td>'
                 f'{extra}<td class="diff">{"+" if diff > 0 else ""}{diff}</td></tr>')
    head_extra = '' if compact else '<th scope="col"><abbr title="Drawn">D</abbr></th><th scope="col"><abbr title="Points for">PF</abbr></th><th scope="col"><abbr title="Points against">PA</abbr></th>'
    return ('<div class="ladder-wrap"><table class="ladder' + ('' if compact else ' ladder-full') + '"><thead><tr><th scope="col"><span class="vh">Position</span></th><th scope="col">Club</th>'
            '<th scope="col"><abbr title="Played">P</abbr></th><th scope="col"><abbr title="Won">W</abbr></th><th scope="col"><abbr title="Lost">L</abbr></th>'
            f'{head_extra}<th scope="col"><abbr title="Points difference">+/−</abbr></th></tr></thead><tbody>{body}</tbody></table></div>')


def r_filter(D):
    ids = []
    for m in D.matches:
        for k in (m['home'], m['away']):
            t = D.team(k)
            if t['id'] not in [i['id'] for i in ids]:
                ids.append(t)
    if len(ids) < 3:
        return ''
    b = '<button type="button" class="chip on" data-team="" aria-pressed="true">All clubs</button>'
    b += ''.join(f'<button type="button" class="chip" data-team="{esc(t["id"])}" aria-pressed="false">{esc(t["short"])}</button>' for t in ids)
    return f'<div class="chips" role="group" aria-label="Show matches for one club">{b}</div>'


def faq_items(D):
    comp = [c['name'] for c in D.clubs if not c.get('status')]
    clubs = ', '.join(comp[:-1]) + ' and ' + comp[-1] if len(comp) > 1 else ''.join(comp)
    pres = next((p['name'] for p in D.board if p['role'].lower() == 'president' and p['name'].lower() != 'vacant'), 'the board')
    h = D.honours[0] if D.honours else None
    prem = ''
    if h:
        prem = f'{h["premier"]} won the {h["year"]} RLBC premiership' + (f', beating {h["runner_up"]} {h.get("score", "").replace("-", chr(8211))} in the grand final.' if h.get('runner_up') and h.get('score') else '.')
        prem += ' Past premiers are listed on the About page.'
    out = []
    for it in D.faq:
        need(it.get('q') and it.get('a'), 'every FAQ needs a question and an answer')
        out.append((it['q'], it['a'].replace('{clubs}', clubs).replace('{president}', pres).replace('{premier}', prem)))
    return out


def r_faq(D):
    return ''.join(f'<h2 class="faq-q">{esc(q)}</h2><p>{esc(a)}</p>' for q, a in faq_items(D))


def faq_ld(D):
    return {"@context": "https://schema.org", "@type": "FAQPage",
            "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq_items(D)]}


def crumb_ld(path, title):
    segs = [x for x in path.strip('/').split('/') if x]
    if not segs:
        return None
    items = [("Home", SITE + "/")]
    parents = {'clubs': 'Clubs', 'news': 'News'}
    if len(segs) > 1 and segs[0] in parents:
        items.append((parents[segs[0]], f'{SITE}/{segs[0]}/'))
    items.append((title, SITE + path))
    return {"@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": n, "item": u} for i, (n, u) in enumerate(items)]}


def r_notice(D):
    f = D.fx
    if not f.get('show_notice'):
        return ''
    t = f'<b>{esc(f["notice_title"])}</b> ' if f.get('notice_title') else ''
    return f'<p class="notice" role="note">{t}{esc(f.get("notice_text", ""))}</p>'


def r_provisional(D):
    f = D.fx
    rows = f.get('provisional_dates') or []
    if not f.get('show_provisional_dates') or not rows:
        return ''
    li = ''
    if f.get('provisional_months_only', True):
        months = {}
        for r in rows:
            d = parse_date(r.get('date'), 'provisional')
            months.setdefault((d.year, d.month), []).append(r.get('label', ''))
        for (y, mth), labels in sorted(months.items()):
            name = datetime.date(y, mth, 1).strftime('%B')
            items = ''.join(f'<span>{esc(x)}</span>' for x in labels)
            li += f'<li class="pm"><time datetime="{y}-{mth:02d}"><b>{name}</b></time>{items}</li>'
        intro = 'Here\'s the shape of the season. Exact dates, venues and kick-off times are still to be confirmed.'
    else:
        for r in rows:
            d = parse_date(r.get('date'), 'provisional')
            li += f'<li><time datetime="{d.isoformat()}"><b>{d.strftime("%b")} {d.day}</b></time><span>{esc(r.get("label", ""))}</span></li>'
        intro = 'Every date here is provisional. Venues and kick-off times are still to be confirmed.'
    return (f'<section class="band band-chalk" id="dates"><div class="wrap"><div class="sec-h"><h2>{esc(f.get("provisional_heading") or "Provisional dates")}</h2>'
            f'<p>{intro}</p></div><ol class="pdates rv">{li}</ol></div></section>')


def event_cards(D, limit=None):
    evs = []
    for e in D.fx.get('events') or []:
        need(e.get('date') and e.get('title'), 'every event needs a date and a title')
        d = parse_date(e['date'], 'event')
        end = parse_date(e['end_date'], 'event end') if e.get('end_date') else d
        evs.append((d, end, e))
    evs.sort(key=lambda x: x[0])
    out = ''
    for d, end, e in evs:
        day = f'{d.day}–{end.day}' if end != d and end.month == d.month else str(d.day)
        if e.get('month_only'):
            day = d.strftime('%b')
        st = f'<span class="pill">{esc(e["status"])}</span>' if e.get('status') else ''
        meta = ' · '.join(esc(x) for x in (e.get('time'), e.get('venue')) if x)
        title = esc(e['title'])
        if e.get('link'):
            title = f'<a href="{esc(e["link"])}">{title}</a>'
        out += (f'<li class="ev" data-end="{end.isoformat()}"><time class="ev-date" datetime="{d.strftime('%Y-%m') if e.get('month_only') else d.isoformat()}"><b>{day}</b><span>{str(d.year) if e.get('month_only') else d.strftime("%b") + ' ' + str(d.year)}</span></time>'
                f'<div class="ev-main">{st}<h3>{title}</h3><p>{meta}</p></div></li>')
    return f'<ol class="evs" data-limit="{limit or 0}">{out}</ol><p class="empty evs-empty" hidden>No events listed right now. Follow <a href="{esc(D.settings["social"]["instagram"])}">@rugbyleaguebc</a> for announcements.</p>'


def r_final(D):
    """Scoreboard for the latest grand final in the match list."""
    gf = [m for m in D.matches if 'grand final' in str(m.get('round', '')).lower() and is_num(m.get('home_score', '')) and is_num(m.get('away_score', ''))]
    if not gf:
        return ''
    m = gf[-1]
    h, a = D.team(m['home']), D.team(m['away'])
    hs, as_ = int(m['home_score']), int(m['away_score'])
    win = h if hs >= as_ else a

    def side(t, s, w):
        return (f'<div class="sb-side{" sb-win" if w else ""}">{tile(t["logo"], t["name"] + " crest", "tile-l") if t["logo"] else ""}'
                f'<span class="sb-name">{esc(t["name"])}</span><b class="sb-pts">{s}</b></div>')
    return (f'<div class="sb rv"><p class="sb-top"><span>{esc(D.fx.get("season", ""))} grand final</span><span>{fmt_date(m["_d"], year=True)} · {esc(m.get("venue", ""))}</span></p>'
            f'<div class="sb-row">{side(h, hs, hs > as_)}<span class="sb-v" aria-hidden="true">–</span>{side(a, as_, as_ > hs)}</div>'
            f'<p class="sb-foot"><span>{esc(D.fx.get("season", ""))} premiers</span> <a href="{win["url"]}">{esc(win["name"])}</a></p></div>')


def club_honours(D, name):
    prem = sorted((s['year'] for s in D.honours if s.get('premier') == name), reverse=False)
    ru = sorted(s['year'] for s in D.honours if s.get('runner_up') == name)
    return prem, ru


def r_club_cards(D):
    out = ''
    for c in D.clubs:
        prem, ru = club_honours(D, c['name'])
        st = f'<span class="pill">{esc(c["status"])}</span>' if c.get('status') else ''
        facts = f'<span>Est. {esc(c["founded"])}</span>' if c.get('founded') else ''
        if c.get('home_field'):
            facts += f'<span>{esc(c["home_field"].split(".")[0])}</span>'
        hon = f'<p class="cc-hon"><b>{len(prem)}</b> premiership{"s" if len(prem) != 1 else ""}: {", ".join(prem)}</p>' if prem else ''
        out += (f'<li class="cc"><a class="cc-a" href="/clubs/{esc(c["slug"])}/">{tile(c["logo"], c["name"] + " crest", "tile-l")}'
                f'<div class="cc-b">{st}<h3>{esc(c["name"])}</h3><p class="cc-f">{facts}</p>{hon}</div></a></li>')
    return f'<ul class="ccs rv">{out}</ul>'


def r_gallery(D, n=None, strip=False):
    items = ''
    for p in (D.gallery[:n] if n else D.gallery):
        need(p.get('image') and p.get('alt'), 'every gallery photo needs an image and a description')
        src = p['image']
        sm = src[:-5] + '-sm.webp' if src.endswith('.webp') and os.path.isfile(sm_path := src[:-5].lstrip('/') + '-sm.webp') else src
        wh = img_size(src)
        dim = f' width="{wh[0]}" height="{wh[1]}"' if wh else ''
        items += (f'<li><a href="{esc(src)}" data-gallery><picture><source media="(max-width:700px)" srcset="{esc(sm)}">'
                  f'<img src="{esc(src)}" alt="{esc(p["alt"])}"{dim} loading="lazy" decoding="async"></picture></a></li>')
    return f'<ul class="{"gal gal-strip" if strip else "gal"}">{items}</ul>'


def r_club_strip(D):
    return '<ul class="crests rv">' + ''.join(
        f'<li><a href="/clubs/{esc(c["slug"])}/">{tile(c["logo"], c["name"] + " crest")}<span>{esc(c["name"])}</span></a></li>'
        for c in D.clubs if not c.get('status')) + '</ul>'


def logo_list(items, cls='crests crests-s'):
    out = ''
    for i in items:
        inner = f'{tile(i["logo"], i["name"])}<span>{esc(i["name"])}</span>'
        out += f'<li><a href="{esc(i["url"])}" target="_blank" rel="noopener">{inner}</a></li>' if i.get('url') else f'<li><span class="nolink">{inner}</span></li>'
    return f'<ul class="{cls}">{out}</ul>'


def r_partners(D, big=True):
    out = ''
    for p in D.partners['partners']:
        need(p.get('name') and p.get('website') and p.get('logo'), 'every partner needs a name, website and logo')
        lab = f'<em>{esc(p["label"])}</em>' if p.get('label') else ''
        out += (f'<li><a href="{esc(p["website"])}" target="_blank" rel="noopener">{tile(p["logo"], p["name"] + " logo", "tile-p tile-dark" if p.get("dark") else "tile-p")}'
                f'<span>{esc(p["name"])}{lab}</span></a></li>')
    return f'<ul class="partners rv">{out}</ul>'


def r_employers(D):
    return '<ul class="partners partners-2 rv">' + ''.join(
        f'<li><a href="{esc(p["website"])}" target="_blank" rel="noopener">{tile(p["logo"], p["name"] + " logo", "tile-p")}<span>{esc(p["name"])}</span></a></li>'
        for p in D.partners.get('employers') or []) + '</ul>'


def r_board(D):
    out = ''
    for p in D.board:
        need(p.get('name') and p.get('role'), 'every board member needs a name and a role')
        vacant = p['name'].strip().lower() == 'vacant'
        if p.get('photo'):
            av = img(p['photo'], p['name'], 'av')
        else:
            ini = '' if vacant else ''.join(w[0] for w in p['name'].split()[:2]).upper()
            av = f'<span class="av av-i" aria-hidden="true">{esc(ini)}</span>'
        e = (p.get('email') or '').strip() or 'board@rugbyleaguebc.ca'
        label = 'Email the board' if vacant or not p.get('email') else f'Email {p["name"].split()[0]}'
        out += (f'<li class="person{" vacant" if vacant else ""}">{av}<div><b>{esc(p["role"])}</b><span>{esc(p["name"])}</span>'
                f'<a href="mailto:{esc(e)}">{esc(label)}</a></div></li>')
    return f'<ul class="people rv">{out}</ul>'


def r_honour_roll(D):
    rows = ''
    for s in D.honours:
        need(s.get('year') and s.get('premier'), 'every season in the honour roll needs a year and a premier')
        sc = esc(s.get('score', '')).replace('-', '–')
        link = f'<a class="zoom" href="{esc(s["results_image"])}" data-zoom="{esc(s["year"])} season results">Full results</a>' if s.get('results_image') else ''
        rows += (f'<tr><th scope="row">{esc(s["year"])}</th><td class="hr-p">{esc(s["premier"])}</td><td class="hr-s">{sc}</td>'
                 f'<td>{esc(s.get("runner_up", ""))}</td><td class="hr-v">{esc(s.get("venue", ""))}</td><td class="hr-l">{link}</td></tr>')
    return ('<div class="ladder-wrap rv"><table class="roll"><thead><tr><th scope="col">Year</th><th scope="col">Premiers</th><th scope="col">Final</th>'
            f'<th scope="col">Runners-up</th><th scope="col">Venue</th><th scope="col"><span class="vh">Results</span></th></tr></thead><tbody>{rows}</tbody></table></div>')


def r_news_cards(D, limit=None):
    out = ''
    for a in D.news[:limit] if limit else D.news:
        if a.get('image'):
            im = img(a.get('card_image') or a['image'], a.get('card_image_alt') or a.get('image_alt') or '')
            if a.get('card_image_pos'):
                im = im.replace('<img ', f'<img style="object-position:{esc(a["card_image_pos"])}" ', 1)
            cr = f'<span class="nc-cr">{esc(a["card_credit"])}</span>' if a.get('card_credit') else ''
            media = f'<div class="nc-m">{im}{cr}</div>'
        else:
            media = f'<div class="nc-m nc-m-none" aria-hidden="true">{CHEV}</div>'
        tag = f'<span class="tag">{esc(a["tag"])}</span>' if a.get('tag') else ''
        date = ''
        if a.get('date'):
            d = parse_date(a['date'], 'news')
            date = f'<time datetime="{d.isoformat()}">{fmt_date(d, year=True, wk=False)}</time>'
        out += (f'<li class="nc"><a href="/news/{esc(a["slug"])}/">{media}<div class="nc-b"><p class="nc-t">{tag}{date}</p>'
                f'<h3>{esc(a["title"])}</h3><p>{esc(a.get("summary", ""))}</p></div></a></li>')
    return f'<ul class="ncs rv">{out}</ul>'


def r_registration(D):
    s = D.settings
    li = ''
    live = bool(s.get('registration_open'))
    for r in s.get('registration_links') or []:
        need(r.get('label'), 'every registration link needs a label')
        note = f'<span>{esc(r["note"])}</span>' if r.get('note') else ''
        if live and r.get('url'):
            li += f'<li><a class="reg" href="{esc(r["url"])}" target="_blank" rel="noopener"><b>{esc(r["label"])}</b>{note}</a></li>'
        else:
            li += f'<li><div class="reg reg-off"><b>{esc(r["label"])}</b>{note}<em>Link coming soon</em></div></li>'
    lede = s.get('registration_note', '') if live else (s.get('registration_closed_note') or 'Registration links are coming soon.')
    return f'<h3>{esc(s.get("registration_heading") or "Register")}</h3><p>{esc(lede)}</p><ul class="regs">{li}</ul>'


def reg_btn(D, url, label, cls='btn btn-blue'):
    if D.settings.get('registration_open') and url:
        return f'<a class="{cls}" href="{esc(url)}" target="_blank" rel="noopener">{esc(label)}</a>'
    return f'<span class="{cls} btn-off" aria-disabled="true">{esc(label)}: coming soon</span>'


def yt(vid, title):
    return (f'<button type="button" class="yt" data-yt="{esc(vid)}" aria-label="Play video: {esc(title)}">'
            f'{img("/assets/img/yt-" + vid + ".webp", "")}<span class="yt-play" aria-hidden="true"></span></button>')


def socials(D):
    names = [('instagram', 'Instagram'), ('facebook', 'Facebook'), ('youtube', 'YouTube'), ('x', 'X'), ('linkedin', 'LinkedIn')]
    return ''.join(f'<li><a href="{esc(D.settings["social"][k])}" target="_blank" rel="noopener">{n}</a></li>' for k, n in names if D.settings['social'].get(k))


# ---------- layout ----------
def layout(D, path, title, desc, main, og='og-home.jpg', ld=None, body_cls=''):
    full_title = title if (path == '/' or len(title) + len(ORG) + 3 > 62) else f'{title} | {ORG}'
    url = SITE + path
    draft = D.settings.get('show_draft_notice')
    nav = ''
    for href, label in NAV:
        cur = ' aria-current="page"' if path == href or (href != '/' and path.startswith(href)) else ''
        nav += f'<li><a href="{href}"{cur}>{label}</a></li>'
    cur_attr = ' aria-current="page"'
    more = ''.join('<li><a href="%s"%s>%s</a></li>' % (h, cur_attr if path.startswith(h) else '', l) for h, l in NAV_MORE)
    ft_nav = ''.join('<li><a href="%s">%s</a></li>' % (h, l) for h, l in NAV)
    ft_more = ''.join('<li><a href="%s">%s</a></li>' % (h, l) for h, l in NAV_MORE)
    data_json = json.dumps({"clubs": {c["id"]: {"name": c["name"], "short": c.get("short") or c["name"], "logo": c["logo"], "url": "/clubs/" + c["slug"] + "/"} for c in D.clubs},
                            "lookup": D.lookup, "sheet": D.settings.get("fixtures_sheet_csv_url", "")}, ensure_ascii=False).replace('</', '<\\/')
    year = datetime.date.today().year
    mailing = esc(D.settings["mailing_list_url"])
    crest_hd = img("/assets/img/crest-160.webp", "", lazy=False)
    crest_ft = img("/assets/img/crest-160.webp", "Rugby League BC crest")
    fam = (('/representative-teams/', 'rep-team-bc', 'Team BC, the RLBC provincial team', 'tile-s tile-bare', False),
           ('/representative-teams/#bulldogs', 'rep-bulldogs', 'BC Bulldogs', 'tile-s tile-bare', False), ('/representative-teams/#storm', 'rep-storm', 'BC Storm', 'tile-s tile-bare', False),
           ('/representative-teams/#silver-foxes', 'rep-silver-foxes', 'BC Silver Foxes', 'tile-s tile-bare', False),
           ('', 'org-canada-rugby-league-wide', 'Canada Rugby League', 'tile-s tile-w tile-crl', False),
           ('https://www.intrl.sport', 'org-international-rugby-league', 'International Rugby League', 'tile-s tile-w', True))
    fam_html = ''.join(('<a href="%s"%s>%s</a>' % (h, ' target="_blank" rel="noopener"' if ext else '', tile('/assets/img/' + f + '.webp', n, cl))) if h else ('<span>%s</span>' % tile('/assets/img/' + f + '.webp', n, cl)) for h, f, n, cl, ext in fam)
    soc = socials(D)
    org_ld = {"@context": "https://schema.org", "@type": "SportsOrganization", "name": "Rugby League British Columbia", "alternateName": ["RLBC", "Rugby League BC"],
              "url": SITE + "/", "logo": SITE + "/assets/img/icon-512.png", "sport": "Rugby league", "foundingDate": "2011", "email": "board@rugbyleaguebc.ca",
              "areaServed": {"@type": "AdministrativeArea", "name": "British Columbia, Canada"},
              "parentOrganization": {"@type": "SportsOrganization", "name": "Canada Rugby League"},
              "sameAs": [v for v in D.settings['social'].values() if v]}
    org_ld["@id"] = SITE + "/#org"
    lds = [org_ld]
    if path == '/':
        lds.append({"@context": "https://schema.org", "@type": "WebSite", "@id": SITE + "/#website", "url": SITE + "/", "name": "Rugby League BC",
                    "inLanguage": "en-CA", "publisher": {"@id": SITE + "/#org"}})
    bc = crumb_ld(path, title)
    if bc:
        lds.append(bc)
    lds += (ld or [])
    ld_html = ''.join(f'<script type="application/ld+json">{json.dumps(x, ensure_ascii=False)}</script>' for x in lds)
    notice = ''
    if draft:
        notice = ('<!-- DRAFT NOTICE BAR: delete before go-live (or turn off "Show the draft notice" in Site settings) -->'
                  '<p class="draft" role="note"><b>Draft preview.</b> This is the new Rugby League BC site in progress, shared for board review. Details may change before launch.</p>'
                  '<!-- /DRAFT NOTICE BAR -->')
    robots = ('<meta name="robots" content="noindex, nofollow">' if (draft or D.settings.get('hide_from_search'))
              else '<meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1">')
    return f'''<!DOCTYPE html>
<html lang="en-CA">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(full_title)}</title>
<meta name="description" content="{esc(desc)}">
{robots}
<link rel="canonical" href="{esc(url)}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Rugby League BC">
<meta property="og:title" content="{esc(full_title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{esc(url)}">
<meta property="og:image" content="{SITE}/assets/og/{og}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(full_title)}">
<meta name="twitter:description" content="{esc(desc)}">
<meta name="twitter:image" content="{SITE}/assets/og/{og}">
<meta name="theme-color" content="#0B1B3F">
<link rel="icon" href="/assets/img/favicon-32.png" sizes="32x32" type="image/png">
<link rel="apple-touch-icon" href="/assets/img/apple-touch-icon.png">
<link rel="manifest" href="/site.webmanifest">
<link rel="preload" href="/assets/fonts/league-gothic-latin-400-normal.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="/assets/fonts/public-sans-latin-wght-normal.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="/assets/site.css">
{ld_html}
</head>
<body class="{body_cls}">
<a class="skip" href="#main">Skip to content</a>
{notice}
<header class="hd">
  <div class="wrap hd-in">
    <a class="brand" href="/" aria-label="Rugby League BC home">{crest_hd}<span><b>Rugby League</b><i>British Columbia</i></span></a>
    <nav class="nav" aria-label="Main"><ul>{nav}</ul></nav>
    <a class="btn btn-gold hd-cta" href="/get-involved/#play">Play</a>
    <button type="button" class="menu-b" aria-expanded="false" aria-controls="menu"><span class="vh">Menu</span><i aria-hidden="true"></i></button>
  </div>
  <div class="menu" id="menu" hidden>
    <nav class="wrap" aria-label="All pages"><ul class="menu-1">{nav}</ul><ul class="menu-2">{more}</ul>
    <a class="btn btn-gold" href="/get-involved/#play">Register to play</a></nav>
  </div>
</header>
<main id="main">
{main}
</main>
<footer class="ft">
  <div class="wrap ft-top">
    <div class="ft-brand">{crest_ft}
      <p>Rugby League British Columbia is the governing body for rugby league in BC, operating under Canada Rugby League.</p>
      <a class="btn btn-line" href="{mailing}" target="_blank" rel="noopener">Join the mailing list</a>
    </div>
    <nav aria-label="Footer"><h2>The league</h2><ul>{ft_nav}</ul></nav>
    <nav aria-label="More pages"><h2>More</h2><ul>{ft_more}<li><a href="mailto:board@rugbyleaguebc.ca">Email the board</a></li></ul></nav>
    <nav aria-label="Social media"><h2>Follow</h2><ul>{soc}</ul></nav>
  </div>
  <div class="wrap ft-fam">{fam_html}</div>
  <div class="wrap ft-end">
    <p>© {year} Rugby League British Columbia. All rights reserved.</p>
    <p>Website by <a href="https://www.mcleodtech.ca/" target="_blank" rel="noopener">McLeod Technologies</a>, Official Technology Partner.</p>
  </div>
</footer>
<dialog class="zoom-d" aria-label="Image viewer"><form method="dialog"><button class="zoom-x" aria-label="Close">Close</button></form><img alt=""></dialog>
<script type="application/json" id="rlbc-data">{data_json}</script>
<script src="/assets/site.js" defer></script>
<script src="/assets/chat.js" defer></script>
</body>
</html>
'''


def page_head(title, lede='', crumb=None, extra='', bg=''):
    c = f'<p class="crumb"><a href="{crumb[0]}">{esc(crumb[1])}</a></p>' if crumb else ''
    l = f'<p class="ph-lede">{lede}</p>' if lede else ''
    cls, b = 'ph', ''
    if bg:
        small = bg.replace('.webp', '-sm.webp')
        src = f'<source media="(max-width:700px)" srcset="{esc(small)}">' if os.path.isfile(small.lstrip('/')) else ''
        cls, b = 'ph ph-photo', f'<div class="ph-img" aria-hidden="true"><picture>{src}{img(bg, "", lazy=False)}</picture></div>'
    return f'<section class="{cls}">{b}<div class="wrap">{c}<h1>{title}</h1>{l}{extra}</div>{CHEV}</section>'


def read_page(name):
    """pages/NAME.html: 'key: value' lines, then a line of ---, then the page body."""
    raw = open(os.path.join('pages', name), encoding='utf-8').read()
    head, _, body = raw.partition('\n---\n')
    meta = {}
    for line in head.splitlines():
        if ':' in line:
            k, v = line.split(':', 1)
            meta[k.strip()] = v.strip()
    return meta, body


def fill(body, parts):
    def rep(m):
        k = m.group(1)
        need(k in parts, f'page uses {{{{{k}}}}} but the build has nothing called that')
        return parts[k]
    body = re.sub(r'\{\{img:([^|}]+)\|([^}]*)\}\}', lambda m: img(m.group(1).strip(), html.unescape(m.group(2).strip())), body)
    return re.sub(r'\{\{([a-z0-9_-]+)\}\}', rep, body)


def write(path, text):
    dst = os.path.join(OUT, path.strip('/'), 'index.html') if path != '/404.html' else os.path.join(OUT, '404.html')
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, 'w', encoding='utf-8') as f:
        f.write(text)


def club_page(D, c):
    prem, ru = club_honours(D, c['name'])
    rows = ''

    def row(k, v):
        return f'<div><dt>{esc(k)}</dt><dd>{v}</dd></div>' if v else ''
    rows += row('Home field', esc(c.get('home_field', '')))
    rows += row('Founded', esc(c.get('founded', '')))
    for co in c.get('coaches') or []:
        rows += row(co.get('role') or 'Coach', esc(co.get('name', '')))
    rows += row('Practices', esc(c.get('practices', '')))
    if c.get('email'):
        rows += row('Contact', f'<a href="mailto:{esc(c["email"])}">{esc(c["email"]).replace("@", "@<wbr>", 1)}</a>')
    if c.get('website'):
        shown = re.sub(r'^https?://(www\.)?', '', c['website']).rstrip('/')
        rows += row('Website', f'<a href="{esc(c["website"])}" target="_blank" rel="noopener">{esc(shown)}</a>')
    if c.get('instagram'):
        handle = '@' + c['instagram'].rstrip('/').split('/')[-1].split('?')[0]
        rows += row('Instagram', f'<a href="{esc(c["instagram"])}" target="_blank" rel="noopener">{esc(handle)}</a>')
    hon = ''
    if prem:
        hon += f'<li><b>{len(prem)}</b><span>RLBC premiership{"s" if len(prem) != 1 else ""}</span><em>{", ".join(prem)}</em></li>'
    if ru:
        hon += f'<li><b>{len(ru)}</b><span>Grand final runner-up</span><em>{", ".join(ru)}</em></li>'
    if c.get('nines_titles'):
        n = [x.strip() for x in c['nines_titles'].split(',') if x.strip()]
        hon += f'<li><b>{len(n)}</b><span>RLBC 9s title{"s" if len(n) != 1 else ""}</span><em>{", ".join(n)}</em></li>'
    hon = f'<section class="band band-chalk"><div class="wrap"><div class="sec-h"><h2>Honours</h2></div><ul class="hons rv">{hon}</ul></div></section>' if hon else ''
    has = any(c['id'] in (D.team(m['home'])['id'], D.team(m['away'])['id']) for m in D.matches)
    res = (f'<section class="band"><div class="wrap"><div class="sec-h"><h2>{esc(D.fx.get("season", ""))} season</h2>'
           f'<a class="more" href="/fixtures/">All fixtures and results</a></div><div class="rds rv">{r_results(D, c["id"])}</div></div></section>') if has else ''
    st = f'<span class="pill">{esc(c["status"])}</span>' if c.get('status') else ''
    cta = ''
    if c.get('email'):
        cta = f'<a class="btn btn-gold" href="mailto:{esc(c["email"])}">Contact the club</a>'
    main = (page_head(esc(c['name']), '', ('/clubs/', 'Clubs'), f'<div class="ph-club">{tile(c["logo"], c["name"] + " crest", "tile-xl")}{st}</div>', bg=c.get('photo') or '')
            + f'<section class="band"><div class="wrap club-top"><dl class="facts rv">{rows}</dl><div class="club-cta rv"><h2>Want to play for the {esc(c.get("short") or c["name"])}?</h2>'
              f'<p>Clubs welcome new and experienced players. Get in touch with the club directly, then register through RLBC.</p><p class="btns">{cta}<a class="btn btn-line-d" href="/get-involved/#play">How to register</a></p></div></div></section>'
            + hon + res)
    desc = f'{c["name"]}: {("home field " + c["home_field"].split(".")[0] + ", ") if c.get("home_field") else ""}founded {c.get("founded", "")}. Club contacts, honours and results in Rugby League BC.'
    team = {"@context": "https://schema.org", "@type": "SportsTeam", "name": c['name'], "sport": "Rugby league", "url": f'{SITE}/clubs/{c["slug"]}/',
            "memberOf": {"@id": SITE + "/#org"}}
    if c.get('logo'):
        team["logo"] = SITE + c['logo']
    if c.get('founded'):
        team["foundingDate"] = c['founded']
    if c.get('home_field'):
        team["location"] = {"@type": "Place", "name": c['home_field'].split('.')[0]}
    if c.get('instagram'):
        team["sameAs"] = [c['instagram']] + ([c['website']] if c.get('website') else [])
    return layout(D, f'/clubs/{c["slug"]}/', c['name'] + ' rugby league club', desc, main, ld=[team])


def clean_body(b):
    # news text comes from the editor as HTML; drop anything that could run code
    b = re.sub(r'<\s*(script|style|iframe|object|embed)[^>]*>.*?<\s*/\s*\1\s*>', '', b, flags=re.S | re.I)
    b = re.sub(r'\son\w+\s*=\s*("[^"]*"|\'[^\']*\'|\S+)', '', b, flags=re.I)
    b = re.sub(r'<a href="(https?://[^"]+)"', r'<a href="\1" target="_blank" rel="noopener"', b)
    return b


def article_page(D, a):
    tag = f'<span class="tag">{esc(a["tag"])}</span>' if a.get('tag') else ''
    date = ''
    if a.get('date'):
        d = parse_date(a['date'], 'news')
        date = f'<time datetime="{d.isoformat()}">{fmt_date(d, year=True, wk=False)}</time>'
    extra = f'<p class="nc-t">{tag}{date}</p>' if tag or date else ''
    media = ''
    if a.get('image'):
        wh = img_size(a['image']) or (1, 1)
        kind = 'art-m-logo' if 'crest-' in a['image'] else 'art-m-poster' if wh[1] > wh[0] else ''
        media = f'<figure class="art-m {kind}">{img(a["image"], a.get("image_alt") or "")}</figure>'
    others = [x for x in D.news if x is not a][:3]
    more = ''.join(f'<li><a href="/news/{esc(x["slug"])}/">{esc(x["title"])}</a></li>' for x in others)
    main = (page_head(esc(a['title']), esc(a.get('summary', '')), ('/news/', 'News'), extra)
            + f'<section class="band"><div class="wrap art"><div class="prose">{clean_body(a.get("body", ""))}</div>'
              f'<div class="art-side">{media}<aside class="art-more"><h2>More news</h2><ul>{more}</ul><a class="more" href="/news/">All news</a></aside></div></div></section>')
    ld = []
    if a['slug'] == 'wellington-wedgetails-are-coming-to-vancouver':
        ld = [{"@context": "https://schema.org", "@type": "SportsEvent", "name": "Wellington Wedgetails vs BC Bulldogs", "sport": "Rugby league",
               "startDate": "2027-03-14T16:00:00-07:00", "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
               "location": {"@type": "Place", "name": "Brockton Oval, Stanley Park", "address": {"@type": "PostalAddress", "addressLocality": "Vancouver", "addressRegion": "BC", "addressCountry": "CA"}},
               "organizer": {"@type": "SportsOrganization", "name": "Rugby League British Columbia", "url": SITE + "/"}}]
    art = {"@context": "https://schema.org", "@type": "Article", "headline": a['title'], "description": a.get('summary') or a['title'],
           "mainEntityOfPage": f'{SITE}/news/{a["slug"]}/', "author": {"@id": SITE + "/#org"}, "publisher": {"@id": SITE + "/#org"}, "inLanguage": "en-CA"}
    if a.get('date'):
        art["datePublished"] = a['date']
    if a.get('image'):
        art["image"] = SITE + a['image']
    return layout(D, f'/news/{a["slug"]}/', a['title'], a.get('summary') or a['title'], main, ld=[art] + ld)


def main():
    D = Data()
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    s = D.settings
    parts = {
        'chev': CHEV,
        'events': event_cards(D), 'events_home': event_cards(D, 3), 'final': r_final(D), 'ladder': r_ladder(D), 'ladder_compact': r_ladder(D, compact=True),
        'results': r_results(D), 'filter': r_filter(D), 'notice': r_notice(D), 'provisional': r_provisional(D),
        'fx_lede': esc(D.fx.get('lede', '')), 'season': esc(D.fx.get('season', '')), 'season_heading': esc(D.fx.get('season_heading', '')),
        'faq': r_faq(D), 'gallery': r_gallery(D), 'gallery_home': r_gallery(D, 4, strip=True), 'club_cards': r_club_cards(D), 'club_strip': r_club_strip(D), 'coming_soon': logo_list(D.clubs_file.get('coming_soon') or []),
        'interprovincial': logo_list(D.clubs_file.get('interprovincial') or []),
        'partners': r_partners(D), 'employers': r_employers(D), 'board': r_board(D), 'honour_roll': r_honour_roll(D),
        'news_home': r_news_cards(D, 3), 'news_all': r_news_cards(D), 'registration': r_registration(D),
        'mailing_list_url': esc(s['mailing_list_url']), 'volunteer_form_url': esc(s['volunteer_form_url']), 'coach_btn': reg_btn(D, s.get('coach_registration_url'), 'Register as a coach'), 'admin_btn': reg_btn(D, s.get('admin_registration_url'), 'RLBC admin registration', 'btn btn-line-d'),
        'supporters_signup_url': esc(s['supporters_signup_url']), 'store_url': esc(s['store_url']), 'calendar_embed_url': esc(s['calendar_embed_url']),
        'clubs_map_embed_url': esc(s['clubs_map_embed_url']), 'instagram_url': esc(s['social']['instagram']),
        'yt_nines': yt('ba1S5Y9M6DU', 'Vancouver Dragons defeat Valley Vipers, RLBC 9s final 2026'), 'yt_rules': yt('vFwHtFJarhE', 'The rules of rugby league explained'),
        'yt_diff': yt('sRUHxGwv_VY', 'The difference between rugby union and rugby league explained'),
        'yt_bulldogs': yt('dMewu4Sf9og', '2018 Western Provincial Cup, BC Bulldogs vs Alberta Broncos'), 'yt_storm': yt('DFvc53VxyrU', 'BC Storm vs NZUTRL'),
    }
    urls = []
    for name in sorted(os.listdir('pages')):
        if not name.endswith('.html'):
            continue
        meta, body = read_page(name)
        path = meta['path']
        body = fill(body, parts)
        head = '' if meta.get('head') == 'none' else page_head(meta['h1'], fill(meta.get('lede', ''), parts))
        write(path, layout(D, path, meta['title'], meta['description'], head + body, og=meta.get('og', 'og-home.jpg'), body_cls=meta.get('class', ''),
                           ld=[faq_ld(D)] if meta.get('faq') else None))
        if path != '/404.html':
            urls.append(path)
    for c in D.clubs:
        write(f'/clubs/{c["slug"]}/', club_page(D, c)); urls.append(f'/clubs/{c["slug"]}/')
    for a in D.news:
        write(f'/news/{a["slug"]}/', article_page(D, a)); urls.append(f'/news/{a["slug"]}/')
    # static files
    for item in ('assets', '_headers', '_redirects', 'site.webmanifest'):
        if os.path.isdir(item):
            shutil.copytree(item, os.path.join(OUT, item))
        elif os.path.isfile(item):
            shutil.copy2(item, os.path.join(OUT, item))
    # chat widget: fill in the live site data so answers stay in step with the CMS
    comp_events = [{'title': e['title'], 'date': e['date'], 'end_date': e.get('end_date', '')} for e in (D.fx.get('events') or [])
                   if not e.get('status') and re.search(r'\bBC (Bulldogs|Storm|Silver)', e['title'])]
    h0 = D.honours[0] if D.honours else None
    chat_data = {
        'clubs': [{'name': c['name'], 'status': c.get('status', '')} for c in D.clubs],
        'events': comp_events,
        'provisional': [{'date': x['date'], 'label': x['label']} for x in (D.fx.get('provisional_dates') or [])] if D.fx.get('show_provisional_dates') else [],
        'registration_open': bool(s.get('registration_open')),
        'mailing_list_url': s['mailing_list_url'], 'volunteer_form_url': s['volunteer_form_url'], 'supporters_signup_url': s['supporters_signup_url'],
        'store_url': s['store_url'], 'instagram_url': s['social']['instagram'],
        'premier': (f'{h0["premier"]} are the {h0["year"]} premiers. ' if h0 else ''),
    }
    cj = os.path.join(OUT, 'assets', 'chat.js')
    src = open(cj, encoding='utf-8').read()
    need('/*RLBC_DATA*/ null' in src, 'chat.js lost its data placeholder')
    open(cj, 'w', encoding='utf-8').write(src.replace('/*RLBC_DATA*/ null', json.dumps(chat_data, ensure_ascii=False).replace('</', '<\\/')))
    mods = {f'/news/{a["slug"]}/': a['date'] for a in D.news if a.get('date')}
    sm = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + ''.join(
        f'  <url><loc>{SITE}{u}</loc>' + (f'<lastmod>{mods[u]}</lastmod>' if u in mods else '') + '</url>\n' for u in sorted(urls, key=lambda u: (u != '/', u))) + '</urlset>\n'
    open(os.path.join(OUT, 'sitemap.xml'), 'w').write(sm)
    bots = ['GPTBot', 'OAI-SearchBot', 'ChatGPT-User', 'ClaudeBot', 'Claude-SearchBot', 'Claude-User', 'PerplexityBot', 'Perplexity-User', 'Google-Extended', 'Applebot', 'Applebot-Extended', 'Bingbot', 'DuckAssistBot', 'Amazonbot', 'Meta-ExternalAgent', 'MistralAI-User', 'CCBot']
    open(os.path.join(OUT, 'robots.txt'), 'w').write(
        '# Rugby League BC: search engines and AI assistants are welcome to read this site.\nUser-agent: *\nAllow: /\n\n'
        + ''.join(f'User-agent: {b}\n' for b in bots) + f'Allow: /\n\nSitemap: {SITE}/sitemap.xml\n')
    # llms.txt: a plain-text summary for AI assistants, rebuilt from the data
    prem = D.honours[0] if D.honours else None
    L = ['# Rugby League BC (RLBC)', '',
         '> Rugby League British Columbia is the non-profit governing body for rugby league (the 13-a-side game) in British Columbia, Canada. Founded in 2011, it operates under Canada Rugby League.',
         '', '## Key facts',
         '- Clubs: ' + '; '.join(f'{c["name"]} ({c.get("home_field", "").split(".")[0]}, founded {c.get("founded", "")}{", " + c["status"].lower() if c.get("status") else ""})' for c in D.clubs) + '.']
    if prem:
        L.append(f'- {prem["year"]} premiers: {prem["premier"]}' + (f' (beat {prem["runner_up"]} {prem.get("score", "").replace("-", "–")} in the grand final).' if prem.get('runner_up') else '.'))
    L += ['- Past premiers: ' + ', '.join(f'{x["year"]} {x["premier"]}' for x in D.honours) + '.',
          '- Board: ' + ', '.join(f'{p["name"]} ({p["role"]})' for p in D.board if p['name'].lower() != 'vacant') + '.',
          '- Representative teams: BC Bulldogs (men), BC Storm (women), BC Silver Foxes (masters, 35+).',
          '- Contact: board@rugbyleaguebc.ca', '', '## Pages'] + [f'- {SITE}{u}' for u in urls if u.count('/') <= 2]
    L += ['', '## Coming up'] + [f'- {e["date"]}: {e["title"]}' + (f' ({e["status"].lower()})' if e.get('status') else '') + (f', {e["venue"]}' if e.get('venue') else '') for e in D.fx.get('events') or []]
    L += ['', '## How to get involved',
          f'- Play: find a club at {SITE}/clubs/ and register through the forms at {SITE}/get-involved/#play. One-day registration is for people who have never played.',
          f'- Coach, officiate or volunteer: {SITE}/get-involved/',
          f'- Sponsor: {SITE}/partners/ (contact richard.marshall@rugbyleaguebc.ca)',
          '', '## Frequently asked questions'] + [f'- {q} {a}' for q, a in faq_items(D)]
    L += ['', '## Full site text', f'- {SITE}/llms-full.txt']
    open(os.path.join(OUT, 'llms.txt'), 'w', encoding='utf-8').write('\n'.join(L) + '\n')
    # llms-full.txt: the readable text of every page, for AI assistants
    import html as _h
    full = ['# Rugby League BC: full site text', '']
    for u in sorted(urls, key=lambda u: (u != '/', u)):
        fp = os.path.join(OUT, u.strip('/'), 'index.html')
        if not os.path.isfile(fp):
            continue
        t = open(fp, encoding='utf-8').read()
        m = re.search(r'<main id="main">(.*?)</main>', t, re.S)
        if not m:
            continue
        body = re.sub(r'<(script|style|svg|dialog|iframe)\b.*?</\1>|<p\b[^>]*\bhidden\b[^>]*>.*?</p>', ' ', m.group(1), flags=re.S)
        body = re.sub(r'</(p|h[1-6]|li|div|section|dd|dt|tr)>', '\n', body)
        body = _h.unescape(re.sub(r'<[^>]+>', ' ', body))
        body = '\n'.join(re.sub(r'[ \t]+', ' ', ln).strip() for ln in body.splitlines())
        body = re.sub(r'\n{2,}', '\n', body).strip()
        ttl = _h.unescape(re.search(r'<title>(.*?)</title>', t, re.S).group(1))
        full += [f'## {ttl}', f'URL: {SITE}{u}', '', body, '']
    open(os.path.join(OUT, 'llms-full.txt'), 'w', encoding='utf-8').write('\n'.join(full) + '\n')
    print(f'Built {OUT}: {len(urls)} pages for {SITE}')


main()
