"""Unified extraction pass, keeping the one field the old passes threw away.

Nodes keyed by spelling alone merge every sense of a homograph, and that
produced chains that were confidently wrong: 高麗 is both Goryeo and (in
Taiwan, borrowed from Dutch kool) cabbage, so Korea's ancestry walked out of a
country and into a vegetable. Wiktionary already separates these -- each
"Etymology N" section is its own entry in the dump, tagged etymology_number --
but extract.py and extract_etym.py both discarded it.

One streaming pass, three outputs:

  registry.jsonl   every entry: lang, word, etymology_number, first gloss,
                   sense ids. This is what decides whether a spelling is a
                   homograph and which sense a reference means.
  source2.jsonl    entries carrying etymology templates or a descendants tree:
                   the edges, each anchored to its exact sense.
  langnames.json   lang_code -> display name.
"""
import gzip
import io
import json
import os
import sys
import time

SRC = r"C:\Projects\etymology-tree-viz\data\raw-wiktextract-data.jsonl.gz"
OUT = r"C:\Projects\etymology-tree-viz\data\extract"

WANTED = {
    "inh", "inherited", "der", "derived", "bor", "borrowed", "lbor",
    "learned borrowing", "slbor", "semi-learned borrowing", "obor",
    "orthographic borrowing", "calque", "cal", "partial calque", "psm",
    "semantic loan", "sl", "root", "etymon", "uder", "ety",
    "af", "affix", "compound", "com", "suffix", "suf", "prefix", "pre",
    "confix", "con", "blend", "univerbation",
}


def slim(nodes):
    """Descendants tree, keeping only what the graph needs."""
    out = []
    for n in nodes or []:
        if not isinstance(n, dict):
            continue
        o = {}
        for k in ("lang", "lang_code", "word", "sense"):
            v = n.get(k)
            if v:
                o[k] = v
        tags = (n.get("tags") or []) + (n.get("raw_tags") or [])
        joined = " ".join(t for t in tags if isinstance(t, str)).lower()
        if "borrow" in joined or "loan" in joined:
            o["b"] = 1
        kids = slim(n.get("descendants"))
        if kids:
            o["d"] = kids
        if o:
            out.append(o)
    return out


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    sys.setrecursionlimit(20000)
    if not os.path.isdir(OUT):
        os.makedirs(OUT)
    f_reg = io.open(os.path.join(OUT, "registry.jsonl"), "w", encoding="utf-8")
    f_src = io.open(os.path.join(OUT, "source2.jsonl"), "w", encoding="utf-8")
    langnames = {}

    n_lines = n_src = 0
    t0 = time.time()
    with gzip.open(SRC, "rt", encoding="utf-8") as fh:
        for line in fh:
            n_lines += 1
            try:
                e = json.loads(line)
            except ValueError:
                continue
            c, w = e.get("lang_code"), e.get("word")
            if not c or not w:
                continue
            w = w.lstrip("*").strip()
            if not w:
                continue
            if c not in langnames:
                langnames[c] = e.get("lang") or ""

            num = e.get("etymology_number") or 0
            gloss = ""
            for s in (e.get("senses") or []):
                for gl in (s.get("glosses") or []):
                    if gl:
                        gloss = gl[:90]
                        break
                if gloss:
                    break
            sids = []
            for s in (e.get("senses") or []):
                for k in ("senseid", "senseids"):
                    v = s.get(k)
                    if isinstance(v, str):
                        sids.append(v)
                    elif isinstance(v, list):
                        sids.extend(x for x in v if isinstance(x, str))

            reg = {"c": c, "w": w}
            if num:
                reg["n"] = num
            if gloss:
                reg["g"] = gloss
            if sids:
                reg["s"] = sids[:6]
            f_reg.write(json.dumps(reg, ensure_ascii=False) + "\n")

            tmpl = [{"n": t.get("name"), "a": t.get("args") or {}}
                    for t in (e.get("etymology_templates") or [])
                    if t.get("name") in WANTED]
            desc = slim(e.get("descendants"))
            if tmpl or desc:
                src = {"c": c, "w": w}
                if num:
                    src["n"] = num
                if tmpl:
                    src["t"] = tmpl
                if desc:
                    src["d"] = desc
                f_src.write(json.dumps(src, ensure_ascii=False) + "\n")
                n_src += 1

            if n_lines % 2000000 == 0:
                print("  {:>10,} lines   {:>9,} source entries   {:.0f}s".format(
                    n_lines, n_src, time.time() - t0), flush=True)

    f_reg.close()
    f_src.close()
    with io.open(os.path.join(OUT, "langnames.json"), "w", encoding="utf-8") as fh:
        json.dump(langnames, fh, ensure_ascii=False)

    print("\ndone in {:.0f}s".format(time.time() - t0))
    print("  lines read      {:,}".format(n_lines))
    print("  source entries  {:,}".format(n_src))
    for name in ("registry.jsonl", "source2.jsonl"):
        p = os.path.join(OUT, name)
        print("  {:<16} {:>8.1f} MB".format(name, os.path.getsize(p) / 1048576))


if __name__ == "__main__":
    main()
