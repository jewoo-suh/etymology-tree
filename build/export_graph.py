"""Export a compact graph slice for the single-file front end.

Slice definition, and why it is what it is:

An earlier version seeded from proto-forms and closed *downward*, which sounds
reasonable and silently lost most of English's abstract vocabulary. 'grammar'
climbs to Latin grammatica and stops -- Latin's own PIE ancestry is not recorded
for that word -- so it never descended from any proto node and fell outside the
slice entirely. Same for nation, justice, library.

So: seed from the best-covered LANGUAGES and close *upward*. Every word kept
keeps its complete chain of ancestors, because a word whose lineage is truncated
is worse than a word that is simply absent.

The page ships as one file under a 16 MB cap. Glosses are the expensive part
(222k of them cost 4.8 MB), so they are kept only for reconstructed forms, where
the reader cannot possibly guess the meaning from the form.
"""
import base64
import re
import collections
import io
import json
import os
import sys

G = r"C:\Projects\etymology-tree-viz\data\graph"
OUT = r"C:\Projects\etymology-tree-viz\web"
NODE_TARGET = 830000   # tuned to land the bundled page under the 16 MB cap
STRUCT_SHARE = 0.78    # of that, the share reserved for words other than compound leaves
LEAF_FLOOR = 40        # compounds every language keeps, however small it is
GLOSS_MAX = 44
DIGITS = "0123456789abcdefghijklmnopqrstuvwxyz"


def b36(n):
    if n == 0:
        return "0"
    s = ""
    while n:
        s = DIGITS[n % 36] + s
        n //= 36
    return s


def frontcode(strings):
    """Sorted forms share long prefixes (enm:gramer / gramere / grammer), so
    store a shared-prefix length plus the tail rather than the whole word.
    Cuts the word blob by roughly a third.

    Prefix lengths are counted in UTF-16 code units, not Python code points,
    because the browser reconstructs these with String.slice which is UTF-16.
    Counting code points corrupts every word outside the BMP -- Gothic, Avestan,
    Old Italic, Modi -- and a split surrogate pair is never re-joinable, so the
    prefix is also backed off whenever it would end mid-pair.
    """
    def is_high(pair):
        v = pair[0] | (pair[1] << 8)
        return 0xD800 <= v <= 0xDBFF

    out, prev = [], b""
    for s in strings:
        cur = s.encode("utf-16-le")
        n, m = 0, min(len(prev), len(cur), 35 * 2)
        while n < m and prev[n:n + 2] == cur[n:n + 2]:
            n += 2
        while n >= 2 and is_high(prev[n - 2:n]):
            n -= 2
        out.append(DIGITS[n // 2] + cur[n:].decode("utf-16-le"))
        prev = cur
    return "\n".join(out)


def main():
    """--full drops the node budget and defines every word.

    The 16 MB ceiling belongs to the shareable artifact link, not to HTML. A
    local file has no such limit, so there is no reason for the offline build to
    inherit a constraint that exists only for sharing.
    """
    FULL = "--full" in sys.argv
    # --target N sizes a build for somewhere between the two extremes: the
    # shareable artifact is capped at 16 MB, the offline build has no ceiling,
    # and a page served over the network wants something in between.
    GLOSS_ALL = FULL or "--glossall" in sys.argv
    TAG = "full" if FULL else "web" if "--glossall" in sys.argv else None
    target = NODE_TARGET
    if "--target" in sys.argv:
        target = int(sys.argv[sys.argv.index("--target") + 1])
    sys.setrecursionlimit(20000)
    with io.open(os.path.join(G, "nodes2.json"), encoding="utf-8") as fh:
        nodes = json.load(fh)
    with io.open(os.path.join(G, "edges2.json"), encoding="utf-8") as fh:
        edges = json.load(fh)

    # Four slots, and `der` must not share one with `inh`. "Derived from" is
    # used loosely for "ultimately from", so a Middle English page citing PIE
    # directly produces a two-hop shortcut past Old English and Proto-Germanic.
    # The page walks these in order of trustworthiness, so they must stay apart.
    # `form` shares a slot with `der`: both mean "built from" rather than
    # "descended from", and the page tells them apart without extra bits by
    # comparing the two languages -- word-formation is always same-language.
    KIND2 = {"inh": 0, "bor": 1, "cal": 1, "root": 2, "der": 3, "form": 3}

    up = collections.defaultdict(list)
    for p, c, _k in edges:
        up[c].append(p)

    # Strip entries nobody comes here for. Wiktionary indexes every surname,
    # hamlet and inflected form, so "a Finnish surname" appears 2,639 times and
    # crowds out real vocabulary. A junk node is still kept when something real
    # descends from it, because dropping it would sever a chain -- Latin place
    # names really are the ancestors of ordinary modern words.
    ANYWHERE = "|".join([
        r"surname", r"given name", r"patronymic", r"family name",
        r"transferred from the place name", r"a placename",
    ])
    ATSTART = "|".join([
        r"a (?:village|town|city|hamlet|suburb|river|lake|mountain|district)",
        r"a (?:parish|county|province|municipality|commune|locality|region)",
        r"a (?:state|island|census-designated place|unincorporated community)",
        r"a (?:neighborhood|neighbourhood|nickname)",
        r"(?:plural|singular|genitive|dative|accusative|nominative|vocative)",
        r"(?:instrumental|locative|ablative|comparative|superlative)",
        r"(?:past|present|future|perfect|imperfect|participle|gerund)",
        r"(?:infinitive|imperative|subjunctive|feminine|masculine|neuter)",
        r"(?:definite|indefinite|diminutive|augmentative|inflection)",
        r"(?:conjugation|declension|misspelling|eye dialect)",
        r"(?:alternative|obsolete|archaic|dated|nonstandard) (?:form|spelling)",
        r"(?:synonym|abbreviation|initialism|acronym|romanization) of",
        r"(?:transliteration|form|inflection) of",
        r"(?:a )?taxonomic (?:genus|species|family|order)",
    ])
    JUNK = re.compile("(?:" + ANYWHERE + r")|^(?:" + ATSTART + ")", re.I)

    down_all = collections.defaultdict(list)
    for p, c, _k in edges:
        down_all[p].append(c)
    junk = set()
    for k, v in nodes.items():
        g = (v.get("gloss") or "").strip()
        if g and JUNK.search(g):
            junk.add(k)
    keepers = {k for k in junk if any(c not in junk for c in down_all.get(k, ()))}
    junk -= keepers
    print("dropping {:,} name / inflection / taxonomy entries "
          "({:,} kept because real words descend from them)".format(len(junk), len(keepers)))
    for k in junk:
        nodes.pop(k, None)
    edges = [e for e in edges if e[0] not in junk and e[1] not in junk]
    up = collections.defaultdict(list)
    for p, c, _k in edges:
        up[c].append(p)
    print("nodes now {:,}, edges {:,}".format(len(nodes), len(edges)))

    # Once template edges are merged, ancestor closure dominates the size:
    # dropping 215 seed languages to 85 barely moved the payload, because every
    # word cites etymons that drag in long tails of other languages. So pack to a
    # node budget instead of guessing a language count -- take languages in order
    # of coverage, close each one's ancestry, and keep it only if it still fits.
    buckets = collections.defaultdict(list)
    for k, v in nodes.items():
        buckets[v.get("lang_code", "?")].append(k)
    bylang = collections.Counter({c: len(v) for c, v in buckets.items()})

    # Compounds are so numerous in some languages that taking whole languages in
    # size order collapses the breadth this project exists for: English alone is
    # 419,419 nodes, 663,620 once closed, which is 82% of the budget and left
    # nine seed languages standing. So split the work.
    #
    # A compound leaf -- every parent a word-formation edge, no descendants of
    # its own -- can be dropped without breaking anybody's chain, because
    # nothing hangs below it. Everything else is structural and gets packed
    # first, preserving reach across languages. The leaves then fill the
    # remaining budget under a per-language quota, so English cannot crowd out
    # Welsh.
    down_deg = collections.Counter()
    nonform_up = collections.Counter()
    for p, c, k in edges:
        down_deg[p] += 1
        if k != "form":
            nonform_up[c] += 1
    leaf = set()
    for k in nodes:
        if not down_deg.get(k) and not nonform_up.get(k) and up.get(k):
            leaf.add(k)
    print("compound leaves (safely truncatable): {:,} of {:,}".format(len(leaf), len(nodes)))

    # Reserve a share up front, or the structural pass simply spends everything
    # and the compounds we set out to include never get in.
    struct_cap = int(target * STRUCT_SHARE)

    # Take whole languages in size order and English swallows the budget: it
    # alone closes to 663,620 nodes, leaving seventeen languages standing and
    # Spanish cut to 4,431 words. Since the premise of this thing is that any
    # language is a valid way in, cap what each may contribute and give the
    # slots to its best-connected words -- the ones other words hang off.
    deg = {}
    for k in nodes:
        deg[k] = down_deg.get(k, 0) + len(up.get(k, ()))
    ranked = {}
    for c, ks in buckets.items():
        own = [k for k in ks if k not in leaf]
        own.sort(key=lambda k: (-deg.get(k, 0), k))
        ranked[c] = own

    # A flat quota is too blunt: 760 apiece covered 4,473 languages but cost
    # English robot, piano and notebook, because English has far more to say.
    # Scale by the square root of what a language actually has, so big languages
    # get more without the largest taking everything.
    def quota_for(c, m):
        n = len(ranked[c])
        return min(n, max(LEAF_FLOOR, int(m * (n ** 0.5))))

    def pack(m):
        keep = set()
        for c, _n in bylang.most_common():
            fresh = [k for k in ranked[c][:quota_for(c, m)] if k not in keep]
            if not fresh:
                continue
            trial, frontier = set(fresh), list(fresh)
            while frontier:
                nxt = []
                for x in frontier:
                    for p in up.get(x, ()):
                        if p not in keep and p not in trial:
                            trial.add(p)
                            nxt.append(p)
                frontier = nxt
            keep |= trial
            if len(keep) > struct_cap:
                return None
        return keep

    keep = None
    if FULL:
        keep = set(nodes)
        print("full build: every node kept, {:,}".format(len(keep)))
    lo, hi, best, bestm = 1, 3000, None, 1
    while keep is None and lo <= hi:
        mid = (lo + hi) // 2
        got = pack(mid)
        if got is None:
            hi = mid - 1
        else:
            best, bestm = got, mid
            lo = mid + 1
    if keep is None:
        keep = best if best is not None else (pack(1) or set())
    seeded = sum(1 for c in ranked if ranked[c] and
                 any(k in keep for k in ranked[c][:1]))
    print("structural pass: {:,} nodes, {} languages contributing".format(
        len(keep), seeded))
    for c in ("en", "de", "fi", "es", "ru", "ja", "cy"):
        if c in ranked and ranked[c]:
            print("    {:<4} quota {:>7,} of {:>7,} own words".format(
                c, quota_for(c, bestm), len(ranked[c])))

    # Spend what is left on compound leaves, in proportion to how many each
    # language actually has, but with a floor so a language with a handful still
    # gets them all. English has the most compounds and gets the largest share
    # without being allowed to take the lot.
    spare = 0 if FULL else target - len(keep)
    pool = collections.defaultdict(list)
    for k in leaf:
        if k not in keep:
            pool[nodes[k].get("lang_code", "?")].append(k)
    for c in pool:
        pool[c].sort()
    total_leaves = sum(len(v) for v in pool.values())
    added = 0
    if total_leaves and spare > 0:
        quotas = {}
        for c, v in pool.items():
            share = int(spare * len(v) / total_leaves)
            quotas[c] = min(len(v), max(LEAF_FLOOR, share))
        over = sum(quotas.values()) - spare
        if over > 0:                       # trim the biggest holders back
            for c in sorted(quotas, key=lambda x: -quotas[x]):
                if over <= 0:
                    break
                cut = min(over, max(0, quotas[c] - LEAF_FLOOR))
                quotas[c] -= cut
                over -= cut
        for c, v in pool.items():
            for k in v[:quotas[c]]:
                keep.add(k)
                added += 1
    print("compound pass: {:,} leaves added across {} languages".format(
        added, sum(1 for v in pool.values() if v)))
    print("nodes total: {:,}".format(len(keep)))

    order = sorted(keep)
    ids = {k: i for i, k in enumerate(order)}

    codes, code_id, lang_name = [], {}, {}

    def cid(code, name):
        if code not in code_id:
            code_id[code] = len(codes)
            codes.append(code)
        if name and code not in lang_name:
            lang_name[code] = name
        return code_id[code]

    words, wlang = [], []
    gids, gtexts = [], []
    dirty = 0
    for i, k in enumerate(order):
        v = nodes[k]
        w = v.get("word", "")
        if "\n" in w or "\r" in w:
            dirty += 1
            w = w.replace("\r", " ").replace("\n", " ")
        words.append(w)
        c = v.get("lang_code") or "?"
        wlang.append(cid(c, v.get("lang") or ""))
        if GLOSS_ALL or "-pro" in c:
            g = (v.get("gloss") or "")[:GLOSS_MAX].replace("\r", " ").replace("\n", " ")
            if g:
                gids.append(i)
                gtexts.append(g)
    if dirty:
        print("flattened {} word(s) containing newlines".format(dirty))

    # nodes are keyed "code:word" and sorted, so each language is one run
    runs, prev, count = [], None, 0
    for x in wlang:
        if x == prev:
            count += 1
        else:
            if prev is not None:
                runs.append((prev, count))
            prev, count = x, 1
    if prev is not None:
        runs.append((prev, count))

    adj = collections.defaultdict(list)
    n_edges = 0
    for p, c, k in edges:
        if p in ids and c in ids:
            adj[ids[p]].append((ids[c], KIND2[k]))
            n_edges += 1

    # two bits per edge over the flattened child order: inherited / borrowed /
    # root-shortcut / variant. A per-edge byte or an index list would both cost
    # several times as much across 2.4M edges.
    chunks, flat = [], 0
    kind_bits = bytearray((n_edges + 3) // 4)
    kcount = collections.Counter()
    for p in sorted(adj):
        cs = sorted(adj[p])
        chunks.append(b36(p) + ">" + ",".join(b36(c) for c, _ in cs))
        for c, k in cs:
            kind_bits[flat >> 2] |= (k & 3) << ((flat & 3) * 2)
            kcount[k] += 1
            flat += 1

    out = {
        "codes": codes,
        "names": [lang_name.get(c, "") for c in codes],
        "words": frontcode(words),
        "wrle": ",".join(b36(a) + ":" + b36(b) for a, b in runs),
        "gids": ",".join(b36(i) for i in gids),
        "gtexts": "\n".join(gtexts),
        "adj": ";".join(chunks),
        "kinds": base64.b64encode(bytes(kind_bits)).decode("ascii"),
    }

    dest = os.path.join(OUT, "graph-{}.json".format(TAG) if TAG else "graph.json")
    payload = json.dumps(out, ensure_ascii=False, separators=(",", ":"))
    with io.open(dest, "w", encoding="utf-8") as fh:
        fh.write(payload)

    names4 = {0: "inherited", 1: "borrowed", 2: "root-shortcut", 3: "variant"}
    print("\nnodes {:,}   edges {:,}   languages {:,}".format(
        len(order), n_edges, len(codes)))
    print("  " + "   ".join("{} {:,}".format(names4[k], v)
                            for k, v in sorted(kcount.items())))
    print("glossed: {:,} ({})".format(len(gids),
          "every word" if GLOSS_ALL else "reconstructed forms only"))
    print("\n-- payload breakdown --")
    for k in sorted(out, key=lambda k: -len(json.dumps(out[k], ensure_ascii=False))):
        b = len(json.dumps(out[k], ensure_ascii=False).encode("utf-8"))
        print("  {:<8} {:>7.2f} MB".format(k, b / 1048576))
    print("\nwrote {} ({:.1f} MB)".format(dest, os.path.getsize(dest) / 1048576))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
