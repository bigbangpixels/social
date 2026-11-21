"""Builds index.html (the link-in-bio page of social.bigbangpixels.store) from the shop's live Etsy sections.

    python build.py            refresh the section list and counts from Etsy's public API, write index.html

Empty sections are left out. Etsy credentials: the Pinterest Scheduler's etsy.py (ETSY_KEYSTRING, read-only, public
data). privacy.html and terms.html are written by hand (they back the Big Bang Pixels TikTok app).
"""
import html
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, r"C:\BigBangPixels\Claude Code\Pinterest Scheduler")
import etsy  # noqa: E402

SHOP = "https://www.etsy.com/shop/BigBangPixelsShop"
SOCIAL = [
    ("Instagram", "https://www.instagram.com/bigbangpixels/"),
    ("Pinterest", "https://www.pinterest.com/bigbangpixels/"),
    ("YouTube", "https://www.youtube.com/channel/UCW3EMFFRzCJnyKkC5wH3Jdw"),
]
# grouping of the shop sections on the page (anything new lands under "More")
GROUPS = [
    ("Gifts", ["Mom, Dad & Grandparents", "Wedding Party Hats"]),
    ("Hats", ["Embroidered Dad Hats", "Embroidered Beanies", "Chess Beanies", "Drummer Beanies",
              "Bass Player Beanies", "Music Lovers Beanies"]),
    ("Tees, bags & desk", ["Chess Opening Tees", "Music Tees & Mugs", "Makeup Bags & Pouches",
                           "Men's Toiletry Bags", "Tote Bags", "Desk Mats"]),
]

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Big Bang Pixels</title>
<meta name="description" content="Minimalist embroidered dad hats, beanies and graphic tees with a bold sense of humor. Shop Big Bang Pixels on Etsy.">
<link rel="icon" href="assets/logo.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Anybody:wdth,wght@75,900&family=Montserrat:wght@600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="assets/style.css">
</head>
<body>
<main>
<img class="logo" src="assets/logo.png" alt="Big Bang Pixels" width="600" height="126">
<p class="tagline">Minimalist embroidered hats and tees. Bold lines, never boring.</p>
<ul class="links"><li class="main"><a href="{shop}">Shop everything on Etsy <span class="count">{total} items</span></a></li></ul>
{groups}
<nav class="social" aria-label="Follow Big Bang Pixels">{social}</nav>
<footer><a href="privacy.html">Privacy</a> &middot; <a href="terms.html">Terms</a> &middot; &copy; Big Bang Pixels</footer>
</main>
</body>
</html>
"""


def main():
    shop = etsy._get("/shops", shop_name=etsy.SHOP_NAME)["results"][0]
    sections = {html.unescape(s["title"]): s for s in etsy._get(f"/shops/{shop['shop_id']}/sections")["results"]
                if s["active_listing_count"] > 0}
    seen, blocks = set(), []
    groups = GROUPS + [("More", sorted(set(sections) - {t for _, ts in GROUPS for t in ts}))]
    for name, titles in groups:
        items = []
        for t in titles:
            s = sections.get(t)
            if not s:
                continue
            seen.add(t)
            items.append(f'<li><a href="{SHOP}?section_id={s["shop_section_id"]}">{html.escape(t)} '
                         f'<span class="count">{s["active_listing_count"]}</span></a></li>')
        if items:
            blocks.append(f"<h1>{html.escape(name)}</h1>\n<ul class=\"links\">{''.join(items)}</ul>")
    social = "".join(f'<a href="{u}">{n}</a>' for n, u in SOCIAL)
    out = PAGE.format(shop=SHOP, total=shop["listing_active_count"], groups="\n".join(blocks), social=social)
    (HERE / "index.html").write_text(out, encoding="utf-8")
    print(f"index.html: {len(seen)} sections, {shop['listing_active_count']} items")


if __name__ == "__main__":
    main()
