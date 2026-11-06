"""Draw the shelf motif library: eight motifs per Reading Room shelf (see docs/reading-room/covers/genre-motifs.md).

Each motif is drawn once by the image model in the house style (house_covers.MOTIF_PROMPT), checked,
cleaned to a black-and-white mask and filed in the shared motif library, where any book, shelf or the
whole library can use it:

    assets/cover-motifs/library/<shelf>/<motif>.png     the mask the covers use
    assets/cover-motifs/library.json                     manifest: key, shelf, subject, model
    .seed_cache/house_covers/library/<shelf>/<motif>.png the model's original drawing

    .venv\\Scripts\\python.exe scripts\\generate_motifs.py            # draws what's missing
    .venv\\Scripts\\python.exe scripts\\generate_motifs.py --shelf "Science Fiction"
    .venv\\Scripts\\python.exe scripts\\generate_motifs.py --redo science-fiction/orrery
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import house_covers as hc  # noqa: E402

LIB = hc.MOTIFS / "library"
MANIFEST = hc.MOTIFS / "library.json"
RAW = hc.CACHE / "library"

SHELVES: dict[str, dict[str, str]] = {
    "Science Fiction": {
        "orrery": "brass orrery with three small planets on curved arms",
        "crystals": "cluster of hexagonal crystals growing at angles",
        "diving-helmet": "brass deep-sea diving helmet with round portholes",
        "zeppelin": "zeppelin with tail fins and a small gondola underneath",
        "submarine": "submarine with a riveted hull and a short periscope",
        "fighting-machine": "three-legged fighting machine standing on long jointed legs, from The War of the Worlds",
        "crescent-moon": "crescent moon with a few round craters",
        "gyroscope": "gyroscope tilted on its stand",
    },
    "Literary & Classics": {
        "lily-of-the-valley": "sprig of lily of the valley with its bell flowers and one broad leaf",
        "oil-lamp": "oil lamp with a tall glass chimney",
        "ornate-key": "key with an ornate bow",
        "chess-knight": "chess knight",
        "birdcage": "birdcage with its door open",
        "weathervane": "weathervane cockerel on its arrow",
        "acorn": "acorn on an oak twig with two leaves",
        "candlestick": "candlestick with a half-burned taper and a small flame",
    },
    "Biography & Memoir": {
        "pen-nib": "fountain pen nib",
        "swallow": "swallow in flight with a forked tail",
        "rocking-chair": "rocking chair",
        "medal": "medal hanging from a ribbon",
        "forget-me-not": "sprig of forget-me-not flowers",
        "oak-roots": "oak tree with spreading roots",
        "rosemary": "sprig of rosemary",
        "hourglass": "hourglass in a turned wooden frame",
    },
    "Christianity": {
        "vine": "grapevine branch with a cluster of grapes and one leaf",
        "wheat": "sheaf of wheat bound with a cord",
        "fish": "single fish in profile, drawn in plain early-Christian style",
        "clay-lamp": "clay oil lamp with a small flame",
        "lamb": "lamb standing in profile",
        "dove": "small gentle dove in flight, seen from the side, wings raised, holding an olive sprig in its beak",
        "pomegranate": "pomegranate split open",
        "anchor": "anchor with a crossbar",
    },
    "History": {
        "fleur-de-lis": "fleur-de-lis",
        "galleon": "three-masted galleon under sail",
        "capital": "Corinthian column capital",
        "amphora": "amphora",
        "helmet": "medieval helmet with a nose guard",
        "tricorn": "tricorn hat",
        "longship": "Viking longship with a dragon prow",
        "spinning-wheel": "spinning wheel",
    },
    "Children's": {
        "kite": "kite with a ribboned tail",
        "paper-boat": "folded paper boat",
        "spinning-top": "spinning top",
        "rocking-horse": "rocking horse",
        "squirrel": "squirrel holding a nut",
        "hedgehog": "hedgehog",
        "snail": "snail with a spiral shell",
        "penny-farthing": "penny-farthing bicycle",
    },
    "Adventure": {
        "ships-wheel": "ship's wheel",
        "palm-tree": "palm tree leaning over",
        "canoe": "canoe with a paddle laid across it",
        "tent": "canvas tent with its door flap tied open",
        "peak": "snow-capped mountain peak",
        "hawk": "hawk in flight",
        "storm-lantern": "storm lantern",
        "galloping-horse": "galloping horse",
    },
    "Science & Nature": {
        "fiddlehead": "fern fiddlehead unfurling",
        "ammonite": "ammonite fossil",
        "stag-beetle": "stag beetle",
        "moth": "moth with patterned wings",
        "dragonfly": "dragonfly",
        "nautilus": "nautilus shell cut in half to show its chambers",
        "ginkgo": "ginkgo leaf",
        "honeybee": "honeybee",
    },
    "Poetry": {
        "nightingale": "nightingale on a branch",
        "lyre": "lyre",
        "swan": "swan gliding",
        "dandelion": "dandelion clock",
        "maple-leaf": "falling maple leaf",
        "cherry-blossom": "cherry blossom twig",
        "daffodil": "daffodil",
        "hare": "leaping hare",
    },
    "Mystery & Crime": {
        "escutcheon": "ornate keyhole escutcheon",
        "thorned-rose": "cut rose with thorns on its stem",
        "streetlamp": "gas streetlamp",
        "black-cat": "black cat sitting, seen from behind",
        "bowler-hat": "bowler hat",
        "dark-lantern": "dark lantern with its shutter half closed",
        "locomotive": "steam locomotive seen head-on",
        "key-ring": "ring of old keys",
    },
    "Fantasy": {
        "dragon": "dragon curled in a ring",
        "sword-stone": "sword set in a stone",
        "griffin": "griffin, rampant",
        "raven": "raven with wings half open",
        "winged-key": "winged key",
        "phoenix": "phoenix rising",
        "sea-serpent": "sea serpent coiled in loops above the waves",
        "hawthorn": "hawthorn sprig with berries",
    },
    "Short Stories": {
        "teapot": "round-bellied teapot with a curved spout",
        "crane": "origami crane",
        "ship-bottle": "ship in a bottle",
        "fleuron": "printer's fleuron: the hedera ivy-leaf ornament printed between stories in old books, a heart-shaped leaf with a curling stem",
        "carousel-horse": "carousel horse on its pole",
        "wishbone": "wishbone",
        "door-knocker": "door knocker",
        "paper-lantern": "paper lantern",
    },
    "Humor & Satire": {
        "pig": "pig standing in profile",
        "goose": "goose waddling",
        "dodo": "dodo",
        "cuckoo-clock": "cuckoo clock",
        "hen": "hen standing in profile",
        "umbrella": "umbrella blown inside out",
        "frog-hat": "frog wearing a top hat",
        "donkey": "donkey standing in profile",
    },
    "Travel & Places": {
        "suitcase": "leather suitcase with straps",
        "steamship": "steamship with two funnels",
        "lighthouse": "lighthouse",
        "camel": "camel with a saddle",
        "windmill": "Dutch windmill",
        "gondola": "Venetian gondola",
        "globe": "globe on a stand",
        "balloon": "hot-air balloon with a wicker basket",
    },
    "Plays & Drama": {
        "curtain": "swagged stage curtain",
        "laurel-crown": "laurel crown",
        "fan": "folding fan, half open",
        "ruff": "Elizabethan ruff collar",
        "lute": "lute",
        "herald-trumpet": "herald's trumpet with a hanging banner",
        "masquerade-mask": "masquerade eye mask held on a stick",
        "feathered-cap": "Renaissance cap with a long feather",
    },
    "Philosophy": {
        "owl": "little owl perched",
        "column": "Greek column",
        "scales": "set of balance scales",
        "diogenes-lantern": "old hand lantern, like Diogenes' lantern",
        "labyrinth": "round spiral labyrinth",
        "tortoise": "tortoise",
        "hemlock": "sprig of hemlock",
        "sphere-cube": "sphere resting on a cube",
    },
    "World Religions & Spirituality": {
        "lotus": "lotus flower",
        "bodhi-leaf": "bodhi leaf",
        "temple-bell": "temple bell",
        "torii": "torii gate",
        "shofar": "shofar",
        "mosque-lamp": "hanging glass mosque lamp",
        "conch": "conch shell",
        "crane-flight": "crane in flight",
    },
    "Society, Politics & Economics": {
        "beehive": "straw beehive skep",
        "anvil": "anvil with a hammer",
        "cogwheel": "cogwheel",
        "cracked-bell": "cracked bell",
        "pick-shovel": "a miner's pick and a shovel crossed",
        "steelyard": "merchant's steelyard balance",
        "water-pump": "village water pump",
        "factory": "factory with a smoking chimney",
    },
    "Romance": {
        "honeysuckle": "sprig of honeysuckle",
        "lace-glove": "lace glove",
        "locket": "locket on a chain",
        "garden-gate": "wrought-iron garden gate",
        "parasol": "open parasol",
        "turtle-dove": "turtle dove",
        "atomizer": "perfume bottle with an atomizer bulb",
        "wisteria": "wisteria spray",
    },
    "Horror & Gothic": {
        "crow": "crow perched, head turned",
        "candelabra": "candelabra with dripping candles",
        "bare-tree": "gnarled bare tree",
        "hawkmoth": "death's-head hawkmoth",
        "wolf-head": "wolf's head in profile",
        "gothic-window": "Gothic arched window",
        "bat": "bat in flight with wings spread wide, seen from below, scalloped wing edges",
        "nightshade": "sprig of nightshade with berries",
    },
    "Health & Medicine": {
        "mortar-pestle": "mortar and pestle",
        "garlic": "garlic bulb",
        "apothecary-bottle": "apothecary bottle with a stopper",
        "foxglove": "foxglove stem",
        "chamomile": "chamomile flower",
        "lavender": "lavender sprig",
        "nightingale-lamp": "Florence Nightingale's hand lamp",
        "poppy-head": "poppy seed head",
    },
    "Art, Music & Performance": {
        "violin": "violin",
        "french-horn": "French horn",
        "metronome": "metronome",
        "ballet-slippers": "pair of ballet slippers",
        "harp": "harp",
        "gramophone": "gramophone with a horn",
        "grand-piano": "grand piano",
        "easel": "painter's easel",
    },
    "Christmas Reading": {
        "holly": "sprig of holly with berries",
        "manger": "manger with straw",
        "pinecone": "frosted pinecone on a short sprig of pine",
        "star": "eight-pointed star",
        "robin": "robin",
        "wreath": "evergreen wreath with a ribbon bow at the bottom",
        "plum-pudding": "plum pudding with a sprig of holly",
        "carol-lantern": "carol singer's lantern on a pole",
    },
    "Language & Reference": {
        "lectern": "open book on a wooden lectern",
        "dip-pen": "dip pen nib",
        "globe": "globe on a stand",
        "scroll": "rolled scroll tied with a ribbon",
        "magpie": "magpie perched",
        "parrot": "parrot",
        "ear-trumpet": "ear trumpet",
        "telegraph-key": "telegraph key",
    },
}


def _draw(shelf: str, key: str, subject: str, tries: int = 3) -> tuple[str, dict]:
    sk = hc._key(shelf)
    last = {}
    for attempt in range(tries):
        try:
            raw = hc.draw_motif(subject)
        except urllib.error.HTTPError as e:
            last = {"error": f"HTTP {e.code}"}
            continue
        except Exception as e:  # noqa: BLE001
            last = {"error": str(e)[:120]}
            continue
        mask, st = hc.to_mask(raw)
        last = st | {"attempt": attempt + 1}
        if st["ok"] or attempt == tries - 1:
            (RAW / sk).mkdir(parents=True, exist_ok=True)
            (LIB / sk).mkdir(parents=True, exist_ok=True)
            raw.save(RAW / sk / f"{key}.png")
            mask.save(LIB / sk / f"{key}.png")
            return f"{sk}/{key}", last
    return f"{sk}/{key}", last


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shelf")
    ap.add_argument("--redo", action="append", default=[], help="shelf-key/motif-key to draw again")
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}
    jobs = []
    for shelf, motifs in SHELVES.items():
        if args.shelf and shelf != args.shelf:
            continue
        for key, subject in motifs.items():
            mk = f"{hc._key(shelf)}/{key}"
            if mk in manifest and mk not in args.redo and (LIB / f"{mk}.png").exists():
                continue
            jobs.append((shelf, key, subject))
    print(f"drawing {len(jobs)} motifs with {hc.MOTIF_MODEL}", flush=True)
    with ThreadPoolExecutor(args.workers) as ex:
        futs = {ex.submit(_draw, *j): j for j in jobs}
        for f in as_completed(futs):
            shelf, key, subject = futs[f]
            mk, st = f.result()
            if (LIB / f"{mk}.png").exists():
                manifest[mk] = {"shelf": shelf, "subject": subject, "model": hc.MOTIF_MODEL, "check": st}
            print(f"  {mk}: {st}", flush=True)
            MANIFEST.write_text(json.dumps(manifest, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"library: {len(manifest)} motifs")


if __name__ == "__main__":
    main()
