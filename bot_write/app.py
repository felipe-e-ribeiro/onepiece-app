import hashlib
import requests
from pathlib import Path
import re

OUTPUT = Path("static")
OUTPUT.mkdir(exist_ok=True)

BASE = "https://static.wikia.nocookie.net/onepiece/images"

def get_last_volume():
    url = "https://onepiece.fandom.com/api.php?action=query&list=categorymembers&cmtitle=Category:One%20Piece%20Volumes&cmsort=timestamp&cmdir=desc&cmlimit=1&format=json"
    result = requests.get(url)
    json_result = result.json()
    data_result = json_result["query"]["categorymembers"][0]["title"]
    data_info = re.search(r"\d+", data_result).group()
    return int(data_info)

def fandom_image_url(filename: str):
    md5 = hashlib.md5(filename.encode("utf-8")).hexdigest()
    h1 = md5[0]
    h2 = md5[:2]
    return f"{BASE}/{h1}/{h2}/{filename}/revision/latest/scale-to-width-down/1000?path-prefix=pt"

last_volume = get_last_volume()
for i in range(1, int(last_volume)):
    filename = f"Volume_{i}.png"
    url = fandom_image_url(filename)
    print(f"⬇️ {url}")
    r = requests.get(url)
    if r.status_code == 200:
        with open(OUTPUT / f"Volume_{i}.webp", "wb") as f:
            f.write(r.content)
        print(f"✅ Volume {i}")
    else:
        print(f"❌ Falhou {i}")
