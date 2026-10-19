#!/usr/bin/env python3
"""Bouwt de website van content/ + media/ + templates/ naar _site/.

De site is tweetalig: Nederlands op / en Engels op /en/.

Gebruik:  python build.py
Bekijk:   python -m http.server -d _site 8000   (daarna http://localhost:8000)
"""
import datetime
import hashlib
import html
import json
import re
import shutil
import sys
from pathlib import Path
from urllib.parse import urlparse

import markdown
import yaml
from jinja2 import Environment, FileSystemLoader, pass_context, select_autoescape
from markupsafe import Markup
from PIL import Image, ImageOps

ROOT = Path(__file__).parent.resolve()
OUT = ROOT / "_site"
WIDTHS = [480, 900, 1500]
LANGS = ("nl", "en")
MONTHS = {
    "nl": ["januari", "februari", "maart", "april", "mei", "juni", "juli",
           "augustus", "september", "oktober", "november", "december"],
    "en": ["January", "February", "March", "April", "May", "June", "July",
           "August", "September", "October", "November", "December"],
}
FRONT_MATTER = re.compile(r"\A---[ \t]*\n(.*?)\n---[ \t]*\n?(.*)\Z", re.S)

# Vaste teksten van de site. (Niet de namen items/keys/values/get/copy/update gebruiken.)
STRINGS = {
    "nl": {
        "skip": "Naar de inhoud",
        "nav_label": "Hoofdmenu",
        "nav_paintings": "Schilderijen",
        "nav_about": "Over",
        "nav_news": "Nieuws",
        "nav_contact": "Contact",
        "switch_label": "English version",
        "recent": "Recent werk",
        "all_paintings": "Alle schilderijen",
        "all_news": "Al het nieuws",
        "filter_all": "Alles",
        "only_for_sale": "Alleen te koop",
        "no_results": "Geen schilderijen gevonden met deze keuze.",
        "none_yet": "Hier komen binnenkort schilderijen te staan.",
        "for_sale": "Te koop",
        "sold": "Verkocht",
        "back_paintings": "Terug naar alle schilderijen",
        "back_news": "Terug naar nieuws",
        "label_year": "Jaar",
        "label_technique": "Techniek",
        "label_size": "Formaat",
        "label_price": "Prijs",
        "price_on_request": "Prijs op aanvraag",
        "ask": "Vraag naar dit schilderij",
        "interest_in": "Interesse in",
        "more_paintings": "Meer schilderijen",
        "newer": "Nieuwer",
        "older": "Ouder",
        "no_posts": "Er zijn nog geen berichten.",
        "label_email": "E-mail",
        "label_phone": "Telefoon",
        "label_whatsapp": "WhatsApp",
        "label_studio": "Atelier",
        "label_instagram": "Instagram",
        "label_facebook": "Facebook",
        "photo_soon": "Foto volgt",
        "only_other_language": "",
        "gallery_desc": "Schilderijen van {name}: bekijk het werk en vraag naar een schilderij.",
        "news_desc": "Nieuws, exposities en verhalen uit het atelier van {name}.",
        "painting_desc": "schilderij van {name}",
        "title_home": "schilderijen",
    },
    "en": {
        "skip": "Skip to content",
        "nav_label": "Main menu",
        "nav_paintings": "Paintings",
        "nav_about": "About",
        "nav_news": "News",
        "nav_contact": "Contact",
        "switch_label": "Nederlandse versie",
        "recent": "Recent work",
        "all_paintings": "All paintings",
        "all_news": "All news",
        "filter_all": "All",
        "only_for_sale": "For sale only",
        "no_results": "No paintings match this choice.",
        "none_yet": "Paintings will be shown here soon.",
        "for_sale": "For sale",
        "sold": "Sold",
        "back_paintings": "Back to all paintings",
        "back_news": "Back to news",
        "label_year": "Year",
        "label_technique": "Technique",
        "label_size": "Size",
        "label_price": "Price",
        "price_on_request": "Price on request",
        "ask": "Ask about this painting",
        "interest_in": "Interested in",
        "more_paintings": "More paintings",
        "newer": "Newer",
        "older": "Older",
        "no_posts": "There are no posts yet.",
        "label_email": "Email",
        "label_phone": "Phone",
        "label_whatsapp": "WhatsApp",
        "label_studio": "Studio",
        "label_instagram": "Instagram",
        "label_facebook": "Facebook",
        "photo_soon": "Photo coming soon",
        "only_other_language": "This text is only available in Dutch.",
        "gallery_desc": "Paintings by {name}: browse the work and ask about a painting.",
        "news_desc": "News, exhibitions and stories from the studio of {name}.",
        "painting_desc": "painting by {name}",
        "title_home": "paintings",
    },
}

warnings = []


def warn(msg):
    warnings.append(msg)
    print(f"  ! {msg}")


def lang_url(url, lang):
    """/schilderijen/ -> /en/schilderijen/ voor Engels."""
    if lang == "nl":
        return url
    return "/en" + url


# ---------------------------------------------------------------- inhoud lezen

def to_date(value):
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return datetime.date.fromisoformat(value.strip()[:10])
        except ValueError:
            pass
    return datetime.date(1970, 1, 1)


def render_markdown(text):
    out = markdown.markdown(text, extensions=["extra", "sane_lists"])
    return inline_images(out)


def clean(value):
    return str(value).strip() if value not in (None, "") else ""


def read_entry(path):
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    match = FRONT_MATTER.match(text)
    meta, body = ({}, text)
    if match:
        meta = yaml.safe_load(match.group(1)) or {}
        body = match.group(2)
    meta = dict(meta)
    meta["slug"] = path.stem
    meta["title"] = clean(meta.get("title")) or path.stem.replace("-", " ").capitalize()
    meta["date"] = to_date(meta.get("date"))
    meta["body_md"] = body.strip()
    meta["body"] = Markup(render_markdown(body)) if body.strip() else Markup("")
    body_en = clean(meta.get("body_en"))
    meta["body_en_html"] = Markup(render_markdown(body_en)) if body_en else Markup("")
    return meta


def read_folder(folder):
    d = ROOT / "content" / folder
    if not d.is_dir():
        return []
    return [read_entry(p) for p in sorted(d.glob("*.md"))]


# --------------------------------------------------------------------- foto's

_image_cache = {}


def process_image(web_path):
    """Verkleint een foto uit media/ naar webformaten. Geeft info terug of None."""
    if not web_path or not isinstance(web_path, str):
        return None
    if web_path in _image_cache:
        return _image_cache[web_path]
    src = ROOT / web_path.lstrip("/")
    if not src.is_file():
        warn(f"foto niet gevonden: {web_path}")
        _image_cache[web_path] = None
        return None
    key = hashlib.sha1(src.read_bytes()).hexdigest()[:8]
    stem = re.sub(r"[^a-z0-9]+", "-", src.stem.lower()).strip("-") or "foto"
    try:
        with Image.open(src) as im:
            im = ImageOps.exif_transpose(im)
            if im.mode in ("RGBA", "LA", "P"):  # doorzichtige delen worden wit
                im = im.convert("RGBA")
                flat = Image.new("RGB", im.size, (255, 255, 255))
                flat.paste(im, mask=im.split()[-1])
                im = flat
            elif im.mode != "RGB":
                im = im.convert("RGB")
            w0, h0 = im.size
            widths = sorted({w for w in WIDTHS if w < w0} | {min(w0, WIDTHS[-1])})
            for w in widths:
                h = round(h0 * w / w0)
                resized = im if w == w0 else im.resize((w, h), Image.LANCZOS)
                resized.save(OUT / "img" / f"{stem}-{key}-{w}.webp", quality=80, method=4)
                resized.save(OUT / "img" / f"{stem}-{key}-{w}.jpg", quality=82,
                             optimize=True, progressive=True)
            big = widths[-1]
            info = {"stem": stem, "key": key, "widths": widths,
                    "w": big, "h": round(h0 * big / w0)}
    except Exception as exc:  # beschadigde foto mag de site niet breken
        warn(f"foto kon niet worden gelezen: {web_path} ({exc})")
        info = None
    _image_cache[web_path] = info
    return info


def img(path, alt="", sizes="100vw", eager=False, cls="", lang="nl"):
    info = process_image(path)
    if not info:
        label = html.escape(STRINGS[lang]["photo_soon"], quote=True)
        return Markup(f'<div class="no-image" role="img" aria-label="{label}"></div>')

    def srcset(ext):
        return ", ".join(f"/img/{info['stem']}-{info['key']}-{w}.{ext} {w}w"
                         for w in info["widths"])

    fallback = f"/img/{info['stem']}-{info['key']}-{info['widths'][-1]}.jpg"
    sz = html.escape(sizes, quote=True)
    loading = "" if eager else ' loading="lazy"'
    klass = f' class="{html.escape(cls, quote=True)}"' if cls else ""
    return Markup(
        f'<picture><source type="image/webp" srcset="{srcset("webp")}" sizes="{sz}">'
        f'<img src="{fallback}" srcset="{srcset("jpg")}" sizes="{sz}" '
        f'alt="{html.escape(alt or "", quote=True)}" width="{info["w"]}" height="{info["h"]}"'
        f'{loading} decoding="async"{klass}></picture>')


def social_image(path):
    info = process_image(path)
    if not info:
        return ""
    w = min(info["widths"], key=lambda x: abs(x - 900))
    return f"/img/{info['stem']}-{info['key']}-{w}.jpg"


IMG_TAG = re.compile(r'<img\b[^>]*?\bsrc="(/media/[^"]+)"[^>]*?>', re.I)
ALT_ATTR = re.compile(r'\balt="([^"]*)"', re.I)


def inline_images(fragment):
    """Foto's die in een tekst zijn geplaatst worden ook verkleind."""
    def repl(m):
        alt = ALT_ATTR.search(m.group(0))
        return str(img(m.group(1), html.unescape(alt.group(1)) if alt else "",
                       "(min-width: 62rem) 40rem, 92vw"))
    return IMG_TAG.sub(repl, fragment)


# ----------------------------------------------------- tweetalige hulpfuncties

def localized(obj, key, lang):
    """Geeft de Engelse tekst (key_en) als die er is, anders de Nederlandse."""
    if lang == "en":
        value = obj.get(key + "_en")
        if value not in (None, ""):
            return value
    return obj.get(key, "")


def pair(obj, key):
    return {lang: localized(obj, key, lang) for lang in LANGS}


def has_english_body(entry):
    return bool(str(entry.get("body_en_html", "")).strip())


def body_html(entry, lang):
    if lang == "en" and has_english_body(entry):
        return entry["body_en_html"]
    return entry.get("body", Markup(""))


def body_is_fallback(entry, lang):
    return lang == "en" and not has_english_body(entry) and bool(str(entry.get("body", "")).strip())


def excerpt_text(entry, lang, length=190):
    if lang == "en" and clean(entry.get("samenvatting_en")):
        return clean(entry["samenvatting_en"])
    if lang == "en" and has_english_body(entry):
        source = entry["body_en_html"]
    elif clean(entry.get("samenvatting")):
        return clean(entry["samenvatting"])
    else:
        source = entry.get("body", "")
    text = re.sub(r"<[^>]+>", " ", str(source))
    text = re.sub(r"\s+", " ", html.unescape(text)).strip()
    if len(text) <= length:
        return text
    return text[:length].rsplit(" ", 1)[0] + "…"


def excerpt_lang(entry, lang):
    if lang == "en" and (clean(entry.get("samenvatting_en")) or has_english_body(entry)):
        return "en"
    return "nl"


def format_date(value, lang):
    d = to_date(value)
    if lang == "en":
        return f"{d.day} {MONTHS['en'][d.month - 1]} {d.year}"
    return f"{d.day} {MONTHS['nl'][d.month - 1]} {d.year}"


def format_euro(value, lang):
    if value is None or value == "":
        return ""
    if isinstance(value, str):
        cleaned = value.replace("€", "").replace(".", "").replace(",", ".").strip()
        try:
            value = float(cleaned)
        except ValueError:
            return value
    if lang == "en":
        return f"€ {value:,.0f}"
    return "€ " + f"{value:,.0f}".replace(",", ".")


def f_digits(value):
    return re.sub(r"\D", "", str(value or ""))


# ----------------------------------------------------------------- hoofdprogramma

def main():
    site = json.loads((ROOT / "data" / "site.json").read_text(encoding="utf-8"))
    base_url = site.get("url", "").rstrip("/")
    if not site.get("email"):
        warn("geen e-mailadres ingevuld (data/site.json): de contactpagina blijft leeg")

    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "img").mkdir(parents=True)
    if (ROOT / "static").is_dir():
        shutil.copytree(ROOT / "static", OUT, dirs_exist_ok=True)
    host = urlparse(base_url).netloc
    if host:
        (OUT / "CNAME").write_text(host + "\n", encoding="utf-8")
    (OUT / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\n\nSitemap: {base_url}/sitemap.xml\n", encoding="utf-8")

    env = Environment(loader=FileSystemLoader(ROOT / "templates"),
                      autoescape=select_autoescape(["html", "xml"]),
                      trim_blocks=True, lstrip_blocks=True)

    # Functies in de templates die weten welke taal er op de pagina staat
    @pass_context
    def t_link(ctx, path):
        return lang_url(path, ctx["lang"])

    @pass_context
    def t_loc(ctx, obj, key):
        return localized(obj, key, ctx["lang"])

    @pass_context
    def t_body(ctx, entry):
        return body_html(entry, ctx["lang"])

    @pass_context
    def t_body_fallback(ctx, entry):
        return body_is_fallback(entry, ctx["lang"])

    @pass_context
    def t_img(ctx, *args, **kwargs):
        return img(*args, lang=ctx["lang"], **kwargs)

    @pass_context
    def t_date(ctx, value):
        return format_date(value, ctx["lang"])

    @pass_context
    def t_euro(ctx, value):
        return format_euro(value, ctx["lang"])

    @pass_context
    def t_excerpt(ctx, entry):
        return excerpt_text(entry, ctx["lang"])

    @pass_context
    def t_excerpt_lang(ctx, entry):
        return excerpt_lang(entry, ctx["lang"])

    env.filters.update(date_fmt=t_date, euro=t_euro, digits=f_digits, excerpt=t_excerpt)
    env.globals.update(L=t_link, loc=t_loc, body_of=t_body, body_fallback=t_body_fallback,
                       img=t_img, excerpt_lang=t_excerpt_lang, social_image=social_image,
                       site=site, year=datetime.date.today().year)

    # inhoud
    paintings = sorted(read_folder("schilderijen"), key=lambda p: (p["date"], p["title"]), reverse=True)
    posts = sorted(read_folder("nieuws"), key=lambda p: (p["date"], p["title"]), reverse=True)
    pages = {p["slug"]: p for p in read_folder("pagina")}

    def capital(value):
        value = clean(value)
        return value[:1].upper() + value[1:]

    cat_map = {}
    for i, p in enumerate(paintings):
        p["eager"] = i < 3
        p["status"] = clean(p.get("status")) or "Te koop"
        p["categorie"] = capital(p.get("categorie"))
        p["categorie_en"] = capital(p.get("categorie_en"))
        if not p.get("image"):
            warn(f"schilderij zonder foto: {p['title']}")
        if p["categorie"]:
            entry = cat_map.setdefault(p["categorie"], {"key": p["categorie"], "en": ""})
            if p["categorie_en"] and not entry["en"]:
                entry["en"] = p["categorie_en"]
    categories = [cat_map[k] for k in sorted(cat_map)]
    any_for_sale = any(p["status"] == "Te koop" for p in paintings)

    written = []

    def render(template, url, page_title=None, description=None, languages=LANGS, **ctx):
        """Schrijft de pagina in elke taal weg."""
        for lang in languages:
            t = STRINGS[lang]
            if isinstance(page_title, dict):
                title_text = page_title[lang]
            else:
                title_text = page_title
            name = site["naam"]
            title = f"{title_text} – {name}" if title_text else f"{name} – {t['title_home']}"
            desc = description[lang] if isinstance(description, dict) else description
            if not desc:
                desc = localized(site, "beschrijving", lang)
            page_ctx = dict(ctx)
            page_ctx.update(
                lang=lang, t=t, url=url, title=title, description=desc,
                page_url=lang_url(url, lang),
                canonical=base_url + lang_url(url, lang),
                alternates={lg: base_url + lang_url(url, lg) for lg in LANGS},
                alt_url=lang_url(url, "en" if lang == "nl" else "nl") if len(languages) > 1 else None,
            )
            target = lang_url(url, lang)
            out_path = OUT / target.strip("/") / "index.html" if target != "/" else OUT / "index.html"
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(env.get_template(template).render(**page_ctx), encoding="utf-8")
            written.append(target)

    name = site["naam"]
    render("home.html", "/", recent=paintings[:9], latest_posts=posts[:2],
           og_image=social_image(paintings[0].get("image")) if paintings else "")

    render("gallery.html", "/schilderijen/",
           page_title={lg: STRINGS[lg]["nav_paintings"] for lg in LANGS},
           paintings=paintings, categories=categories, any_for_sale=any_for_sale,
           description={lg: STRINGS[lg]["gallery_desc"].format(name=name) for lg in LANGS})

    for i, p in enumerate(paintings):
        newer = paintings[i - 1] if i > 0 else None
        older = paintings[i + 1] if i + 1 < len(paintings) else None
        desc = {}
        for lg in LANGS:
            parts = [localized(p, "title", lg), clean(localized(p, "techniek", lg)), clean(p.get("formaat"))]
            desc[lg] = f"{' '.join(x for x in parts if x)} – {STRINGS[lg]['painting_desc'].format(name=name)}."
        render("painting.html", f"/schilderijen/{p['slug']}/", page_title=pair(p, "title"), p=p,
               newer=newer, older=older, og_image=social_image(p.get("image")), description=desc)

    render("news_list.html", "/nieuws/",
           page_title={lg: STRINGS[lg]["nav_news"] for lg in LANGS}, posts=posts,
           description={lg: STRINGS[lg]["news_desc"].format(name=name) for lg in LANGS})
    for p in posts:
        render("post.html", f"/nieuws/{p['slug']}/", page_title=pair(p, "title"), post=p,
               og_image=social_image(p.get("image")),
               description={lg: excerpt_text(p, lg, 150) for lg in LANGS})

    for slug in ("over", "contact"):
        page = pages.get(slug)
        if not page:
            warn(f"pagina ontbreekt: content/pagina/{slug}.md")
            continue
        render("page.html", f"/{slug}/", page_title=pair(page, "title"), page=page,
               og_image=social_image(page.get("foto")))

    # De foutpagina staat op een vaste plek en is dus in beide talen tegelijk
    render("404.html", "/404-page/", page_title="404", languages=("nl",))
    shutil.move(OUT / "404-page" / "index.html", OUT / "404.html")
    shutil.rmtree(OUT / "404-page")
    written.remove("/404-page/")

    sitemap = env.get_template("sitemap.xml").render(urls=[base_url + u for u in written])
    (OUT / "sitemap.xml").write_text(sitemap, encoding="utf-8")

    print(f"Klaar: {len(written)} pagina's (NL + EN), {len(paintings)} schilderijen, "
          f"{len(posts)} berichten, {len(list((OUT / 'img').glob('*')))} foto-bestanden.")
    if warnings:
        print(f"{len(warnings)} aandachtspunt(en), zie hierboven.")


if __name__ == "__main__":
    sys.exit(main())
