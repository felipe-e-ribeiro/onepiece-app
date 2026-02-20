import requests
import hashlib
import re
import sqlite3
import shutil

from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup

from owned import Owned


# =========================================================
# CONFIG
# =========================================================

BASE_API = "https://onepiece.fandom.com/api.php"
OUTPUT = Path("static")
OUTPUT.mkdir(exist_ok=True)

collection = Owned("data/collection.yaml")

session = requests.Session()


# =========================================================
# DATABASE
# =========================================================

conn = sqlite3.connect("my_database.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS editions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    arc TEXT NOT NULL,
    volume_number INT,
    is_owned BOOLEAN
)
""")

# performance tuning sqlite
cursor.execute("PRAGMA journal_mode=WAL;")
cursor.execute("PRAGMA synchronous=NORMAL;")


# =========================================================
# IMAGE URL
# =========================================================

def fandom_image_url(filename: str):
    base = "https://static.wikia.nocookie.net/onepiece/images"
    md5 = hashlib.md5(filename.encode()).hexdigest()
    return f"{base}/{md5[0]}/{md5[:2]}/{filename}/revision/latest/scale-to-width-down/1000?path-prefix=pt"


# =========================================================
# API HELPERS
# =========================================================

def get_last_volume():
    params = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": "Category:One Piece Volumes",
        "cmsort": "timestamp",
        "cmdir": "desc",
        "cmlimit": 1,
        "format": "json",
    }

    r = session.get(BASE_API, params=params).json()
    title = r["query"]["categorymembers"][0]["title"]

    return int(re.search(r"\d+", title).group())


# ---------------------------------------------------------

def get_story_arcs():
    params = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": "Category:Story_Arcs",
        "cmlimit": 500,
        "cmsort": "timestamp",
        "cmdir": "asc",
        "format": "json",
    }

    r = session.get(BASE_API, params=params).json()
    return r["query"]["categorymembers"]


# ---------------------------------------------------------

def parse_volume_range(text, last_volume):
    """
    Aceita:
      100-140
      150-
      61
    """

    match = re.search(r"\d+\s*[-–—]\s*\d*", text)

    if match:
        start, end = match.group(0).replace(" ", "").split("-")

        start = int(start)
        end = int(end) if end else last_volume

        return list(range(start, end + 1))

    single = re.search(r"\d+", text)
    return [int(single.group())]


# ---------------------------------------------------------

def get_arc_volumes(title, last_volume):

    params = {
        "action": "parse",
        "page": title,
        "prop": "text",
        "format": "json",
    }

    html = session.get(BASE_API, params=params).json()["parse"]["text"]["*"]

    match = re.search(
        r'data-source="vol".*?<div[^>]*>(.*?)</div>',
        html,
        re.S,
    )

    if not match:
        return []

    text = BeautifulSoup(match.group(1), "html.parser").text

    return parse_volume_range(text, last_volume)


# =========================================================
# DOWNLOAD (THREAD SAFE)
# =========================================================

def download_volume(volume, volume_arc):

    owned = collection[volume]
    arc = volume_arc.get(volume)

    filename = f"Volume_{volume}.png"
    url = fandom_image_url(filename)

    dest = OUTPUT / f"Volume_{volume}.webp"

    try:
        r = session.get(url, timeout=15)

        if r.status_code == 200:
            dest.write_bytes(r.content)
        else:
            raise Exception()

    except Exception:
        shutil.copy(
            OUTPUT / "NoPicAvailable.webp",
            dest,
        )

    if arc:
        return (arc, volume, owned)

    return None


# =========================================================
# MAIN PIPELINE
# =========================================================

def main():

    print("🔎 Descobrindo último volume...")
    last_volume = get_last_volume()
    print(f"✅ Último volume: {last_volume}")

    print("📚 Coletando arcos...")
    arcs = get_story_arcs()

    data = {}

    for arc in arcs:

        title = arc["title"]

        if title in ("Story Arcs", "Category:Filler Arcs"):
            continue

        safe_title = title.replace(" ", "_")

        print(f"➡️ {safe_title}")

        volumes = get_arc_volumes(safe_title, last_volume)

        if volumes:
            data[safe_title] = volumes

    # -----------------------------------------------------
    # cria mapa volume -> arc
    # -----------------------------------------------------

    volume_arc = {}

    for arc, vols in data.items():
        for v in vols:
            volume_arc.setdefault(v, arc)

    # -----------------------------------------------------
    # DOWNLOADS PARALELOS
    # -----------------------------------------------------

    print("⬇️ Baixando capas...")

    results = []

    with ThreadPoolExecutor(max_workers=8) as executor:
        for result in executor.map(
            lambda v: download_volume(v, volume_arc),
            range(1, last_volume + 1),
        ):
            if result:
                results.append(result)

    # -----------------------------------------------------
    # INSERT SINGLE THREAD (SEM RACE CONDITION)
    # -----------------------------------------------------

    print("💾 Gravando SQLite...")

    cursor.executemany(
        "INSERT INTO editions (arc, volume_number, is_owned) VALUES (?, ?, ?)",
        results
    )

    conn.commit()

    cursor.close()
    conn.close()

    print("✅ Finalizado!")


# =========================================================

if __name__ == "__main__":
    main()