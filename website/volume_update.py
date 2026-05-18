import os
import requests
import hashlib
import re
import shutil
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader

from owned import Owned

SCRIPT_DIR = Path(__file__).parent
OUTPUT = SCRIPT_DIR.parent / "output"

DRY_RUN = os.environ.get("DRY_RUN", "false").lower() == "true"
BUCKET = os.environ.get("BUCKET_NAME", "")

BASE_API = "https://onepiece.fandom.com/api.php"
collection = Owned(str(SCRIPT_DIR / "data" / "collection.yaml"))
session = requests.Session()


def fandom_image_url(filename: str) -> str:
    base = "https://static.wikia.nocookie.net/onepiece/images"
    md5 = hashlib.md5(filename.encode()).hexdigest()
    return f"{base}/{md5[0]}/{md5[:2]}/{filename}/revision/latest/scale-to-width-down/1000?path-prefix=pt"


def get_existing_s3_images() -> set:
    if DRY_RUN or not BUCKET:
        return set()
    import boto3
    s3 = boto3.client("s3")
    paginator = s3.get_paginator("list_objects_v2")
    existing = set()
    for page in paginator.paginate(Bucket=BUCKET, Prefix="static/Volume_"):
        for obj in page.get("Contents", []):
            existing.add(Path(obj["Key"]).name)
    return existing


def get_last_volume() -> int:
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


def get_story_arcs() -> list:
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


def parse_volume_range(text: str, last_volume: int) -> list:
    match = re.search(r"\d+\s*[-–—]\s*\d*", text)
    if match:
        start, end = match.group(0).replace(" ", "").split("-")
        start = int(start)
        end = int(end) if end else last_volume
        return list(range(start, end + 1))
    single = re.search(r"\d+", text)
    return [int(single.group())]


def get_arc_volumes(title: str, last_volume: int) -> list:
    params = {
        "action": "parse",
        "page": title,
        "prop": "text",
        "format": "json",
    }
    html = session.get(BASE_API, params=params).json()["parse"]["text"]["*"]
    match = re.search(r'data-source="vol".*?<div[^>]*>(.*?)</div>', html, re.S)
    if not match:
        return []
    text = BeautifulSoup(match.group(1), "html.parser").text
    return parse_volume_range(text, last_volume)


def download_volume(volume: int, volume_arc: dict, existing_s3: set):
    webp_name = f"Volume_{volume}.webp"
    dest = OUTPUT / "static" / webp_name

    if webp_name in existing_s3:
        print(f"⏭️  Volume {volume} já existe no S3, pulando download")
        return

    url = fandom_image_url(f"Volume_{volume}.png")
    try:
        r = session.get(url, timeout=15)
        if r.status_code == 200:
            dest.write_bytes(r.content)
        else:
            raise Exception()
    except Exception:
        fallback = SCRIPT_DIR / "static" / "NoPicAvailable.webp"
        if fallback.exists():
            shutil.copy(fallback, dest)


def render_html(data: dict, volume_arc: dict, last_volume: int):
    # Inverte volume_arc (vol→arc) para arc→[vols], garantindo que cada volume
    # apareça em exatamente um arco (o mesmo mapeamento autoritativo usado no download).
    arc_volumes: dict[str, list[int]] = {}
    for vol, arc in volume_arc.items():
        arc_volumes.setdefault(arc, []).append(vol)

    arc_min_vol = {arc: min(vols) for arc, vols in arc_volumes.items()}

    editions = []
    for arc, volumes in sorted(arc_volumes.items(), key=lambda item: arc_min_vol[item[0]]):
        vols_sorted = sorted(volumes)
        clean_arc = arc.removesuffix("_Arc").replace("_", " ")
        vols_csv = ",".join(str(v) for v in vols_sorted)
        total = len(vols_sorted)
        owned_count = sum(1 for v in vols_sorted if collection[v])
        editions.append((clean_arc, vols_csv, total, owned_count))

    owned_dict = {v: collection[v] for v in range(1, last_volume + 1)}

    env = Environment(loader=FileSystemLoader(str(SCRIPT_DIR / "templates")))
    template = env.get_template("index.html")
    html = template.render(editions=editions, owned=owned_dict)

    out = OUTPUT / "index.html"
    out.write_text(html, encoding="utf-8")
    print(f"✅ index.html gerado → {out}")


def main():
    (OUTPUT / "static").mkdir(parents=True, exist_ok=True)

    for f in (SCRIPT_DIR / "static").iterdir():
        if f.is_file() and not f.name.startswith("Volume_"):
            shutil.copy(f, OUTPUT / "static" / f.name)

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
        print(f"➡️  {safe_title}")
        volumes = get_arc_volumes(safe_title, last_volume)
        if volumes:
            data[safe_title] = volumes

    # Arcos menores (menos volumes) têm prioridade em volumes disputados,
    # replicando o comportamento do ORDER BY MIN(id) do SQLite antigo.
    volume_arc = {}
    for arc, vols in sorted(data.items(), key=lambda item: (min(item[1]), len(item[1]))):
        for v in vols:
            volume_arc.setdefault(v, arc)

    if 111 in volume_arc:
        print("⚠️  Aplicando exceção: Movendo Volume 111 para Elbaph_Arc")
        volume_arc[111] = "Elbaph_Arc"

    print("☁️  Verificando imagens existentes no S3...")
    existing_s3 = get_existing_s3_images()
    if existing_s3:
        print(f"   {len(existing_s3)} imagens já no S3")

    print("⬇️  Baixando capas...")
    with ThreadPoolExecutor(max_workers=8) as executor:
        executor.map(
            lambda v: download_volume(v, volume_arc, existing_s3),
            range(1, last_volume + 1),
        )

    print("🖼️  Gerando index.html...")
    render_html(data, volume_arc, last_volume)

    print("✅ Finalizado!")


if __name__ == "__main__":
    main()
