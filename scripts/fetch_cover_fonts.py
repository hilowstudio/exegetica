"""Download the cover font library from the Google Fonts repository (all OFL or Apache, commercial use OK).

    .venv\\Scripts\\python.exe scripts\\fetch_cover_fonts.py
Files land in assets/cover-fonts/; each family's license is saved beside it as <Family>-LICENSE.txt.
"""
from __future__ import annotations

import json
import pathlib
import re
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEST = ROOT / "assets" / "cover-fonts"
API = "https://api.github.com/repos/google/fonts/contents/{lic}/{fam}"
RAW = "https://github.com/google/fonts/raw/main/{lic}/{fam}/{file}"

# directory name in google/fonts -> regex for the file to take (first match, upright before italic)
FAMILIES = {
    "playfairdisplay": r"PlayfairDisplay\[",
    "greatvibes": r".", "fraunces": r"Fraunces\[", "cherryswash": r"Bold",
    "dmserifdisplay": r"Regular", "poppins": r"Poppins-Bold\.", "cinzel": r"Cinzel\[", "cinzeldecorative": r"Bold", "metamorphous": r".",
    "almendra": r"Almendra-Bold", "uncialantiqua": r".", "cormorantgaramond": r"CormorantGaramond-Italic\[",
    "italiana": r".", "bebasneue": r".", "anton": r".", "leaguegothic": r"LeagueGothic\[", "oswald": r"Oswald\[",
    "pirataone": r".", "unifrakturcook": r".", "michroma": r".", "oxanium": r"Oxanium\[", "syncopate": r"Bold",
    "spacegrotesk": r"SpaceGrotesk\[", "exo2": r"Exo2\[", "ebgaramond": r"EBGaramond\[",
    "librebaskerville": r"LibreBaskerville\[", "montserrat": r"Montserrat\[",
    "robotoslab": r"RobotoSlab\[", "librefranklin": r"LibreFranklin\[", "cormorant": r"Cormorant\[",
    "instrumentserif": r"Regular", "librecaslondisplay": r".", "jost": r"Jost\[", "josefinsans": r"JosefinSans\[",
    "lora": r"Lora\[", "inter": r"Inter\[", "raleway": r"Raleway\[",
    "robotocondensed": r"RobotoCondensed\[", "rajdhani": r"SemiBold", "roboto": r"Roboto\[",
}


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "exegetica-cover-fonts"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    got = {}
    for fam, pat in FAMILIES.items():
        for lic in ("ofl", "apache"):
            try:
                listing = json.loads(_get(API.format(lic=lic, fam=fam)))
            except Exception:  # noqa: BLE001
                continue
            ttfs = sorted((f["name"] for f in listing if f["name"].endswith(".ttf")), key=lambda n: ("Italic" in n, n))
            if fam == "cormorantgaramond":
                ttfs = sorted(ttfs, key=lambda n: ("Italic" not in n, n))
            pick = next((n for n in ttfs if re.search(pat, n)), None)
            if not pick:
                break
            local = re.sub(r"\[.*\]", "", pick)
            (DEST / local).write_bytes(_get(RAW.format(lic=lic, fam=fam, file=urllib.request.quote(pick))))
            lic_name = next((f["name"] for f in listing if f["name"] in ("OFL.txt", "LICENSE.txt")), None)
            if lic_name:
                (DEST / f"{fam}-LICENSE.txt").write_bytes(_get(RAW.format(lic=lic, fam=fam, file=lic_name)))
            got[fam] = local
            print(f"ok   {fam:20} {lic:6} {local}", flush=True)
            break
        else:
            print(f"MISS {fam}", flush=True)
    print(len(got), "of", len(FAMILIES))


if __name__ == "__main__":
    main()
