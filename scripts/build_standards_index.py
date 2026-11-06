#!/usr/bin/env python3
"""
Distill quill-standards into a compact index the generator app can consume.

quill-standards/ left the repo on 2026-11-06 (webapp/standards/ is the source of truth now). To rerun
this, unpack _backups/quill-standards.pre-fanout.tar.gz or restore it from git history, and pass --src.

The raw spine is 2,092 JSON files (~20 MB, heavily denormalized). This produces
two lean, bundled files under webapp/standards/:

  standards-tree.json        Navigable skeleton for the menu:
                             Subject -> SubSubject -> Topic -> SubTopic
                             (ids + names + objective_count + grade span).
                             No objectives -> small, fast to load.

  standards-objectives.json  Objectives keyed by sub_topic id:
                             {sub_topic_id: [{id, t(ext), g(rade), c(omplexity), u(uid)}]}
                             Only the selected objectives get injected into the
                             model at generation time.

Source of truth: the leaf files at subjects/**/sub_topics/*.json already join
objective text + grade + complexity + uuid. Level names are taken from the
objective records (which are internally consistent) with a fallback to the
sub_topic block.
"""

import json
import sys
from pathlib import Path

import click
from rich.console import Console

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

console = Console(legacy_windows=False)


@click.command()
@click.option("--src", type=click.Path(), help="quill-standards directory")
@click.option("--out", type=click.Path(), help="output directory")
def main(src: str | None, out: str | None):
    project = Path(__file__).parent.parent
    src_dir = Path(src) if src else (project / "quill-standards")
    out_dir = Path(out) if out else (project / "webapp" / "standards")
    subjects_dir = src_dir / "subjects"
    if not subjects_dir.exists():
        console.print(f"[red]Not found:[/red] {subjects_dir}")
        sys.exit(1)
    out_dir.mkdir(parents=True, exist_ok=True)

    # tree[subj] = {name, order, sub[ss] = {name, order, top[t] = {name, order,
    #               st[stid] = {name, order, count, grades:set}}}}
    tree: dict = {}
    objectives: dict[str, list] = {}
    total_obj = 0
    leaf_files = sorted(subjects_dir.glob("**/sub_topics/*.json"))

    def order_key(dotted: str) -> list[int]:
        out_k = []
        for part in dotted.split("."):
            out_k.append(int(part) if part.isdigit() else 0)
        return out_k

    for path in leaf_files:
        data = json.loads(path.read_text(encoding="utf-8"))
        st = data.get("sub_topic", {})
        stid = st.get("id")
        if not stid:
            continue
        sid = st.get("subject_id")
        ssid = st.get("sub_subject_id")
        tid = st.get("topic_id")

        names = {"subject": st.get("subject_name"), "sub_subject": None,
                 "topic": st.get("topic_name"), "sub_topic": st.get("name")}

        objs = []
        grades: set[int] = set()
        for _grade_name, gb in (st.get("grade_levels") or {}).items():
            gnum = gb.get("grade_number")
            for o in (gb.get("objectives") or []):
                rec = {
                    "id": o.get("objective_id"),
                    "t": o.get("objective_text"),
                    "g": gnum,
                    "c": o.get("complexity"),
                    "u": o.get("objective_uuid"),
                }
                anc = o.get("anchors")
                if isinstance(anc, dict) and any(anc.get(k) for k in ("scripture", "confessions", "greek", "standards")):
                    # keep only non-empty anchor lists to hold the index size down
                    rec["a"] = {k: v for k, v in anc.items() if v}
                objs.append(rec)
                if isinstance(gnum, int):
                    grades.add(gnum)
                # objective-level names are the consistent ones
                names["subject"] = o.get("subject_name") or names["subject"]
                names["sub_subject"] = o.get("sub_subject_name") or names["sub_subject"]
                names["topic"] = o.get("topic_name") or names["topic"]

        objs.sort(key=lambda x: ((x["g"] if isinstance(x["g"], int) else 99), order_key(x["id"] or "")))
        objectives[stid] = objs
        total_obj += len(objs)

        subj = tree.setdefault(sid, {"name": names["subject"], "sub": {}})
        ss = subj["sub"].setdefault(ssid, {"name": names["sub_subject"], "top": {}})
        if not ss["name"]:
            ss["name"] = names["sub_subject"]
        top = ss["top"].setdefault(tid, {"name": names["topic"], "st": {}})
        top["st"][stid] = {
            "name": names["sub_topic"],
            "count": len(objs),
            "grades": sorted(grades),
        }

    # Serialize the tree as ordered nested lists.
    def sorted_items(d):
        return sorted(d.items(), key=lambda kv: order_key(kv[0]))

    tree_out = {"subjects": []}
    for sid, subj in sorted_items(tree):
        s_node = {"id": sid, "name": subj["name"], "sub_subjects": []}
        for ssid, ss in sorted_items(subj["sub"]):
            ss_node = {"id": ssid, "name": ss["name"], "topics": []}
            for tid, top in sorted_items(ss["top"]):
                t_node = {"id": tid, "name": top["name"], "sub_topics": []}
                for stid, stv in sorted_items(top["st"]):
                    t_node["sub_topics"].append({
                        "id": stid, "name": stv["name"],
                        "objective_count": stv["count"], "grades": stv["grades"],
                    })
                ss_node["topics"].append(t_node)
            s_node["sub_subjects"].append(ss_node)
        tree_out["subjects"].append(s_node)

    (out_dir / "standards-tree.json").write_text(
        json.dumps(tree_out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    (out_dir / "standards-objectives.json").write_text(
        json.dumps(objectives, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    n_subj = len(tree_out["subjects"])
    n_ss = sum(len(s["sub_subjects"]) for s in tree_out["subjects"])
    n_t = sum(len(t["topics"]) for s in tree_out["subjects"] for t in s["sub_subjects"])
    n_st = len(objectives)
    tree_kb = (out_dir / "standards-tree.json").stat().st_size / 1024
    obj_kb = (out_dir / "standards-objectives.json").stat().st_size / 1024
    console.print(f"[green]Distilled[/green] from {len(leaf_files):,} leaf files:")
    console.print(f"  subjects {n_subj} · sub_subjects {n_ss} · topics {n_t} · sub_topics {n_st:,}")
    console.print(f"  objectives [cyan]{total_obj:,}[/cyan]")
    console.print(f"  standards-tree.json {tree_kb:,.0f} KB · standards-objectives.json {obj_kb:,.0f} KB")


if __name__ == "__main__":
    main()
