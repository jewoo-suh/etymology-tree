"""Build the merged graph with homograph senses kept apart.

Supersedes assemble.py + etym_edges.py + merge_graph.py.

Why: nodes keyed by spelling alone merge every sense of a homograph, and the
merge invents history. 高麗 is Goryeo in one etymology section and, in Taiwan,
cabbage borrowed from Dutch kool in another; one node for both let Korea's
ancestry climb into the vegetable and on to a PIE root for "to swallow". Every
edge was real; the node was a lie.

Node identity is now (lang, word, etymology_number): a spelling with one
etymology keeps its plain "lang:word" key, a homograph becomes "lang:word#1",
"lang:word#2", ... Each edge is anchored on the entry it came from, so its
sense there is exact. The other end is a reference by spelling, resolved to a
sense in this order:

  1. only one sense exists            -> that one
  2. a sense-id hint matches          -> that sense       ({{bor|...|id=...}})
  3. gloss hints overlap a sense's    -> best overlap     (t=, <t:...>, the
     gloss                                                 descendants "sense"
                                                           field, and the
                                                           anchored entry's own
                                                           gloss as context)
  4. otherwise                        -> the first etymology, which is the
                                         primary one on the page

So an unhinted reference to 高麗 lands on Goryeo (etymology 1), not cabbage.
Wrong only when Wiktionary's own ordering would be wrong, and never silently
merged.
"""
import collections
import io
import json
import os
import re
import sys
import unicodedata
import zlib

EX = r"C:\Projects\etymology-tree-viz\data\extract"
OUT = r"C:\Projects\etymology-tree-viz\data\graph"
SEP = "\x00"

KIND = {
    "inh": "inh", "inherited": "inh",
    "der": "der", "derived": "der", "uder": "der",
    "bor": "bor", "borrowed": "bor",
    "lbor": "bor", "learned borrowing": "bor",
    "slbor": "bor", "semi-learned borrowing": "bor",
    "obor": "bor", "orthographic borrowing": "bor",
    "calque": "cal", "cal": "cal", "partial calque": "cal",
    "psm": "cal", "semantic loan": "cal", "sl": "cal",
    "root": "root",
    "af": "form", "affix": "form", "compound": "form", "com": "form",
    "suffix": "form", "suf": "form", "prefix": "form", "pre": "form",
    "confix": "form", "con": "form", "blend": "form", "univerbation": "form",
}
FORMATION = {"af", "affix", "compound", "com", "suffix", "suf", "prefix",
             "pre", "confix", "con", "blend", "univerbation"}
CALQUE = {"calque", "cal", "partial calque", "psm", "semantic loan", "sl"}
RANK = {"inh": 5, "bor": 4, "cal": 4, "der": 3, "form": 2, "root": 0}

def norm_n(v):
    """etymology_number is usually an int, sometimes a numeric string, and
    occasionally free text; senses must sort, so coerce deterministically."""
    if isinstance(v, int):
        return v
    if isinstance(v, str) and v.isdigit():
        return int(v)
    if not v:
        return 0
    return 1000 + (zlib.adler32(str(v).encode("utf-8")) % 8999)


def own_etymon_ids(tmpls):
    """Ids declared by argless etymon templates: on pages that never number
    their etymology sections (reconstruction pages especially), each section
    still announces its identity as {{etymon|xx|id=...}} with no parent arg.
    Two distinct ids on one page = two homographs sharing a key."""
    ids = set()
    for t in tmpls or []:
        if t.get("n") != "etymon":
            continue
        a = t.get("a") or {}
        if a.get("id"):
            ids.add(a["id"])
    return ids


MOD = re.compile(r"<([a-z0-9]+):([^<>]*)>")
TOK = re.compile(r"[^\W\d_]{2,}", re.UNICODE)
STOP = {"the", "of", "and", "to", "in", "an", "or", "for", "with", "from",
        "by", "on", "at", "as", "is", "was", "be", "form", "plural",
        "genitive", "singular", "used", "any", "one", "that", "who"}


def tokens(s):
    return {t for t in TOK.findall((s or "").lower()) if t not in STOP} \
        if s else set()


def split_mods(raw):
    """'mūniō<t:to fortify>' -> ('mūniō', {'t': 'to fortify'})"""
    if not raw or "<" not in raw:
        return raw or "", {}
    mods = {m.group(1): m.group(2) for m in MOD.finditer(raw)}
    return raw.split("<")[0], mods


def defold(s2):
    """Diacritic-blind lowercase, for matching parts against their word."""
    return "".join(ch for ch in unicodedata.normalize("NFD", s2)
                   if not unicodedata.combining(ch)).lower()


def ety_subs(raw, host_lang):
    """Parse <ety:rel<lang:term>...> tree mods inside an etymon argument:
    the citing page's own statement of the cited stage's ancestry. One
    level deep is all the data uses; bare terms take the host's language."""
    subs = []
    i = 0
    while True:
        j = raw.find("<ety:", i)
        if j < 0:
            break
        k, depth = j + 1, 1
        while k < len(raw) and depth:
            if raw[k] == "<":
                depth += 1
            elif raw[k] == ">":
                depth -= 1
            k += 1
        body = raw[j + 5:k - 1]
        i = k
        # the body holds colon-separated segments, each rel<part><part>...;
        # admirālis reads af<ar:amir><-ālis>:influence<la:admīror>, and the
        # influence segment is commentary, not ancestry
        segs, d2, cur = [], 0, ""
        for ch in body:
            if ch == "<":
                d2 += 1
            elif ch == ">":
                d2 -= 1
            if ch == ":" and d2 == 0:
                segs.append(cur)
                cur = ""
                continue
            cur += ch
        if cur:
            segs.append(cur)
        for seg in segs:
            rel = ""
            for ch in seg:
                if not ch.isalpha():
                    break
                rel += ch
            kind = {"inh": "inh", "bor": "bor", "der": "der", "af": "form",
                    "cal": "cal", "calque": "cal", "lbor": "bor",
                    "from": "der"}.get(rel)
            if not kind:
                continue
            parts, d3, buf = [], 0, ""
            for ch in seg[len(rel):]:
                if ch == "<":
                    d3 += 1
                    if d3 == 1:
                        buf = ""
                        continue
                elif ch == ">":
                    d3 -= 1
                    if d3 == 0:
                        parts.append(buf)
                        continue
                if d3 >= 1:
                    buf += ch
            for pt in parts:
                core = pt.split("<")[0]
                if ":" in core:
                    lg2, t2 = core.split(":", 1)
                else:
                    lg2, t2 = host_lang, core
                t2 = clean_term(t2)
                if lg2.strip() and t2:
                    subs.append((kind, lg2.strip(), t2))
    return subs


PARENNOTE = re.compile(r"\([^()]*\)")


def clean_term(t):
    if not t:
        return ""
    t = t.split("<")[0].strip()
    if "(" in t or ")" in t:
        # "(persica) praecocia" keeps its word; "(cut off)" has nothing left
        t = PARENNOTE.sub("", t).strip()
        if "(" in t or ")" in t:
            return ""
    t = t.lstrip("*").strip()
    if t in ("", "-", "--", "?"):
        return ""
    return t


def is_affix_term(t):
    return t.startswith(("-", "−")) or t.endswith(("-", "−"))


def parse_templates(tmpls, own_lang, own_word=""):
    """Yield (kind, lang, term, gloss_hints, id_hints, uncertain, subs)."""
    out = []
    for t in tmpls:
        name, args = t.get("n"), t.get("a") or {}
        base_gloss = set()
        base_ids = set()
        for k in ("t", "t1", "t2", "gloss", "5"):
            v = args.get(k)
            if isinstance(v, str) and v and "=" not in v:
                base_gloss |= tokens(v)
        for k in ("id", "id1", "id2"):
            v = args.get(k)
            if isinstance(v, str) and v:
                base_ids.add(v)

        if name == "ety":
            ETYRELS = {"af": "form", "affix": "form", "inh": "inh",
                       "bor": "bor", "der": "der", "cal": "cal",
                       "calque": "cal", "root": "root", "lbor": "bor",
                       "psm": "cal", "sl": "cal"}
            rel = (args.get("2") or "").split("<")[0].strip().lstrip(":")
            kind = ETYRELS.get(rel)
            if not kind:
                continue
            i = 3
            while i <= 10:
                raw = args.get(str(i))
                i += 1
                if raw is None:
                    break
                if raw.startswith(":"):
                    # a chain may switch relations mid-run: {{ety|ar|:sl|
                    # sa:sunya|:root|s-f-r}} -- the root marker is a new
                    # relation, not a term
                    kind = ETYRELS.get(raw.split("<")[0].strip().lstrip(":"))
                    if not kind:
                        break
                    continue
                core, mods = split_mods(raw)
                gh = set(base_gloss)
                ih = set(base_ids)
                if "t" in mods:
                    gh |= tokens(mods["t"])
                if "id" in mods:
                    ih.add(mods["id"])
                if kind != "form" and ":" in core:
                    lg, term = core.split(":", 1)
                    lg, term = lg.strip(), clean_term(term)
                else:
                    lg, term = own_lang, clean_term(core)
                if lg and term:
                    out.append((kind, lg, term, gh, ih,
                                bool(mods.get("unc")), ()))
            continue

        if name == "etymon":
            # Positional args from 2 up hold groups of [:rel, term, term...];
            # a group with no leading :rel is derivation, and a bare term
            # (no "lang:" prefix) belongs to the entry's own language --
            # {{etymon|cs|id=Q11012|robota}} is how robot cites robota. For
            # :af the terms are the parts a word was built from, all real;
            # for any other relation the extra terms are rival theories, so
            # only the first is the page's citation.
            RELS = {"inh": "inh", "bor": "bor", "der": "der", "af": "form",
                    "cal": "cal", "calq": "cal", "calque": "cal",
                    "lbor": "bor", "psm": "cal", "sl": "cal", "from": "der"}
            groups = []
            cur_rel, cur_terms = "der", []
            gi = 2
            while gi <= 12:
                raw = args.get(str(gi))
                gi += 1
                if raw is None:
                    break
                if raw.startswith(":"):
                    if cur_terms and cur_rel:
                        groups.append((cur_rel, cur_terms))
                    # an unrecognised relation (:influence, :cognate...) is
                    # not ancestry; its terms must not become parents
                    cur_rel = RELS.get(raw.split("<")[0].strip().lstrip(":"))
                    cur_terms = []
                    continue
                if raw.strip() and cur_rel:
                    cur_terms.append(raw)
            if cur_terms and cur_rel:
                groups.append((cur_rel, cur_terms))
            def gpri(g):
                grel2, terms2 = g
                unc0 = bool(split_mods(terms2[0])[1].get("unc"))
                if grel2 != "form" and not unc0:
                    return 0
                return 1 if grel2 == "form" else 2

            groups.sort(key=gpri)
            wf = defold(own_word)

            def esc(raw):
                t = defold(clean_term(split_mods(raw)[0])).strip("-\u2212")
                return -len(t) if t and t in wf else 0

            for grel, terms in groups:
                # Which part is the thread of a compound? The one the word
                # carries: melarancia continues through arancia (the orange),
                # not mela (the apple); teacher through teach, not -er.
                # Contained parts win by length, page order breaks ties.
                for raw in (sorted(terms, key=esc)
                            if grel == "form" else terms[:1]):
                    core, mods = split_mods(raw)
                    if ":" in core:
                        lg, term = core.split(":", 1)
                        lg = lg.strip()
                    else:
                        lg, term = own_lang, core
                    term = clean_term(term)
                    ih = set(base_ids)
                    if "id" in mods:
                        ih.add(mods["id"])
                    if lg and term:
                        out.append((grel, lg, term,
                                    base_gloss | tokens(mods.get("t", "")),
                                    ih, bool(mods.get("unc")),
                                    tuple(ety_subs(raw, lg))))
            continue

        kind = KIND.get(name)
        if not kind:
            continue

        if name in FORMATION:
            # the template names the language the word was formed in;
            # umbrella's page carries {{af|la|umbra|-lus}}, Latin parts
            form_lang = (args.get("1") or "").strip() or own_lang
            vals = []
            i = 2
            while i <= 9:
                raw = args.get(str(i))
                i += 1
                if raw is None:
                    break
                core, mods = split_mods(raw)
                term = clean_term(core)
                if term:
                    vals.append((term, mods, len(vals) + 1))
            if not vals:
                continue

            def sfx(x):
                return x if x.startswith(("-", "−")) else "-" + x

            def pfx(x):
                return x if x.endswith(("-", "−")) else x + "-"

            emit = []
            for term, mods, pos in vals:
                if name in ("suffix", "suf") and pos > 1:
                    term = sfx(term)
                elif name in ("prefix", "pre") and pos < len(vals):
                    term = pfx(term)
                elif name in ("confix", "con"):
                    if pos == 1:
                        term = pfx(term)
                    elif pos == len(vals):
                        term = sfx(term)
                gh = set(base_gloss)
                ih = set()
                tv = args.get("t" + str(pos))
                if isinstance(tv, str):
                    gh |= tokens(tv)
                iv = args.get("id" + str(pos))
                if isinstance(iv, str) and iv:
                    ih.add(iv)
                if "t" in mods:
                    gh |= tokens(mods["t"])
                if "id" in mods:
                    ih.add(mods["id"])
                emit.append((term, gh, ih, bool(mods.get("unc"))))
            wf2 = defold(own_word)

            def fsc(t4):
                t = defold(t4[0]).strip("-\u2212")
                return -len(t) if t and t in wf2 else 0

            for term, gh, ih, unc in sorted(emit, key=fsc):
                out.append(("form", form_lang, term, gh, ih, unc, ()))
            continue

        lg = (args.get("2") or "").strip()
        raw3 = args.get("3")
        core, mods = split_mods(raw3 or "")
        term = clean_term(core)
        if not term and name in CALQUE:
            core4, mods4 = split_mods(args.get("4") or "")
            term = clean_term(core4)
            mods = mods4 or mods
        gh = set(base_gloss)
        ih = set(base_ids)
        if "t" in mods:
            gh |= tokens(mods["t"])
        if "id" in mods:
            ih.add(mods["id"])
        if lg and term:
            out.append((kind, lg, term, gh, ih,
                        bool(mods.get("unc") or args.get("unc")), ()))
    return out


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    sys.setrecursionlimit(20000)
    intern = sys.intern

    # ---- pass 1: which spellings does the graph touch at all? -------------
    print("pass 1: collecting referenced spellings", flush=True)
    cand = set()
    page_ids = collections.defaultdict(set)

    def note_ref(lg, term):
        cand.add(intern(lg + SEP + term.lstrip("*").strip()))

    def walk_refs(nodes):
        for nd in nodes:
            w = nd.get("word")
            if nd.get("lang_code") and w:
                note_ref(nd["lang_code"], w)
            if nd.get("d"):
                walk_refs(nd["d"])

    n_src = 0
    with io.open(os.path.join(EX, "source2.jsonl"), encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            e = json.loads(line)
            n_src += 1
            note_ref(e["c"], e["w"])
            for _id in own_etymon_ids(e.get("t")):
                page_ids[e["c"] + SEP + e["w"]].add(_id)
            for kind, lg, term, _g, _i, _u, _subs in parse_templates(
                    e.get("t") or [], e["c"], e["w"]):
                note_ref(lg, term)
                for _k2, lg2, t2 in _subs:
                    note_ref(lg2, t2)
            if e.get("d"):
                walk_refs(e["d"])
    split_sid = {sk: ids for sk, ids in page_ids.items() if len(ids) > 1}
    page_ids = None
    print("  {:,} source entries, {:,} distinct spellings touched".format(
        n_src, len(cand)), flush=True)
    print("  {:,} unnumbered homograph pages split by etymon id".format(
        len(split_sid)), flush=True)

    # ---- pass 2: sense registry for those spellings ------------------------
    print("pass 2: sense registry", flush=True)
    sense_ns = {}                    # "c\0w" -> sorted list of etym numbers
    glosses = {}                     # "c\0w\0n" -> gloss
    sidmap = {}                      # "c\0w\0sid" -> n
    raw_ns = collections.defaultdict(set)
    with io.open(os.path.join(EX, "registry.jsonl"), encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            sk = r["c"] + SEP + r["w"]
            if sk not in cand:
                continue
            n = norm_n(r.get("n", 0))
            pref = r["c"] + ":"
            bare = {x[len(pref):] if x.startswith(pref) else x
                    for x in r.get("s") or []}
            if n == 0 and sk in split_sid:
                hit = bare & split_sid[sk]
                if hit:
                    n = norm_n("sid:" + min(hit))
            raw_ns[sk].add(n)
            gk = sk + SEP + str(n)
            if r.get("g") and gk not in glosses:
                glosses[gk] = r["g"]
            # senseids arrive lang-prefixed here but bare in <id:...> hints
            for sid in set(r.get("s") or []) | bare:
                sidmap.setdefault(sk + SEP + sid, n)

    multi = 0
    for sk, ns in raw_ns.items():
        ns = sorted(ns)
        # a stray unnumbered line on a numbered page folds into the primary
        if 0 in ns and len(ns) > 1:
            pos = [x for x in ns if x > 0]
            gk0, gk1 = sk + SEP + "0", sk + SEP + str(pos[0])
            if gk0 in glosses and gk1 not in glosses:
                glosses[gk1] = glosses[gk0]
            ns = pos
        sense_ns[sk] = ns
        if len(ns) > 1:
            multi += 1
    del raw_ns
    print("  {:,} spellings with entries, {:,} homographs split".format(
        len(sense_ns), multi), flush=True)

    # ---- resolution ---------------------------------------------------------
    stats = collections.Counter()

    def defold(s2):
        return "".join(ch for ch in unicodedata.normalize("NFD", s2)
                       if not unicodedata.combining(ch)).lower()

    def kf(sk, n, ns):
        c, w = sk.split(SEP, 1)
        return intern(c + ":" + w + ("#" + str(n) if len(ns) > 1 else ""))

    def strip_marks(s3):
        """Accent-like marks only (combining class 220+): the Old English
        dot and the Vedic anudatta go, but a Devanagari virama (class 9)
        is structure, and stripping it corrupts every conjunct."""
        return "".join(ch for ch in unicodedata.normalize("NFD", s3)
                       if unicodedata.combining(ch) < 220)

    def resolve(lg, term, gloss_hints, id_hints, ctx, cword=""):
        term = term.lstrip("*").strip()
        sk = lg + SEP + term
        ns = sense_ns.get(sk)
        if not ns:
            # pages cite Old English with dots (anġel) that the registry
            # spells plain (angel); retry with combining marks stripped so
            # the citation reaches the real senses instead of a phantom
            t2 = strip_marks(term)
            if t2 != term:
                sk2 = lg + SEP + t2
                if sk2 in sense_ns:
                    sk, term, ns = sk2, t2, sense_ns[sk2]
        if not ns:
            # Arabic and Hebrew citations arrive pointed, registries are
            # unpointed; classes 10-35 are vocalisation, class 7-9 (nukta,
            # virama) are structure and stay
            t3 = "".join(ch for ch in unicodedata.normalize("NFD", term)
                         if not (10 <= unicodedata.combining(ch) <= 35
                                 or unicodedata.combining(ch) >= 220))
            if t3 != term:
                sk3 = lg + SEP + t3
                if sk3 in sense_ns:
                    sk, term, ns = sk3, t3, sense_ns[sk3]
        if not ns:
            stats["phantom"] += 1
            return intern(lg + ":" + term), False, "phantom", True
        ns_all = ns
        if cword and len(ns) > 1:
            # "genitive/accusative singular of robot" is an inflection OF the
            # word being resolved for, not its ancestor; robot must land on
            # robota "serfdom", never on its own declension
            cw = " of " + defold(cword)
            ns = [n for n in ns
                  if not defold(glosses.get(sk + SEP + str(n), ""))
                         .rstrip(" .").endswith(cw)] or ns_all
        # Two different questions, two different evidence sets. WHICH sense may
        # use the reference's own spelling (picking the sense of bred glossed
        # "bread"). WHETHER to trust the landing may not: a gloss that names its
        # own headword -- "The eye; the organ used for sight" -- would vouch for
        # itself, and that is how the egg tree kept hold of the organ.
        own = wtok(term)
        want_trust = gloss_hints | ctx
        want_sel = want_trust | own

        def prefix5(a):
            """A long shared prefix between the target's own spelling and any
            context word is evidence of the same lexeme: communisme earns the
            trust of communism through nine shared letters, where the gloss
            comparison ("any collectivism" vs a truncated ideology gloss) sees
            nothing. None of the known bridges come close -- ster/star share
            two letters, dag/day two, senn/sunne one."""
            for t in want_trust:
                n2 = 0
                m = min(len(a), len(t))
                while n2 < m and a[n2] == t[n2]:
                    n2 += 1
                if n2 >= 4:
                    # chery/cherry share four letters; no known fiction
                    # pair (dag/day, ster/star, mone/moon) shares more
                    # than three
                    return True
            return False

        own_fold = "".join(ch for ch in unicodedata.normalize("NFD", term)
                           if not unicodedata.combining(ch)).lower()
        cw_fold = defold(cword) if cword else ""

        def tok_sub():
            """A multiword target vouches through its tokens: eschec mat is
            the parent of chekmat because "mat" sits inside the child's
            word. No known fiction shares three such letters."""
            if not cw_fold:
                return False
            for t2 in own_fold.replace("-", " ").split():
                if len(t2) >= 3 and t2 in cw_fold:
                    return True
            return False

        def trust_of(n):
            g = glosses.get(sk + SEP + str(n), "")
            return (not g) or (not want_trust) or bool(tokens(g) & want_trust)                 or prefix5(own_fold) or tok_sub()

        if len(ns) == 1:
            trusted = trust_of(ns[0])
            stats["unique" if trusted else "unique untrusted"] += 1
            return kf(sk, ns[0], ns_all), True, "unique", trusted
        for sid in id_hints:
            n = sidmap.get(sk + SEP + sid)
            if n is not None and n in ns:
                stats["senseid"] += 1
                return kf(sk, n, ns_all), True, "senseid", True
        if want_sel:
            best_n, best_s = None, 0
            for n in ns:
                sc = len(tokens(glosses.get(sk + SEP + str(n), "")) & want_sel)
                if sc > best_s:
                    best_s, best_n = sc, n
            if best_n is not None:
                trusted = trust_of(best_n)
                stats["gloss" if trusted else "gloss untrusted"] += 1
                return kf(sk, best_n, ns_all), True, "gloss", trusted
        stats["first"] += 1
        return kf(sk, ns[0], ns_all), True, "first", False

    def wtok(w):
        return tokens("".join(ch for ch in unicodedata.normalize("NFD", w)
                              if not unicodedata.combining(ch)))

    def anchored_key(c, w, n):
        sk = c + SEP + w
        ns = sense_ns.get(sk) or [0]
        if n == 0 and len(ns) > 1:
            n = ns[0]
        if n not in ns:
            n = ns[0]
        return kf(sk, n, ns), sk, n

    # ---- pass 3: edges ------------------------------------------------------
    print("pass 3: building edges", flush=True)
    with io.open(os.path.join(EX, "langnames.json"), encoding="utf-8") as fh:
        langnames = json.load(fh)
    edges = {}
    node_word = {}
    node_entry = set()
    # Each entry's first surviving lineage citation, in the order the page
    # wrote them, names the nearest ancestor first. Chains follow these page
    # links verbatim instead of re-deriving a path through the glued graph --
    # gluing between pages is where every invented lineage came from.
    primary = set()
    primary_of = set()
    # Wiktionary marks disputed derivations machine-readably (<unc:1> in
    # etymon/ety templates); penguin's Welsh "white head" is a perhaps, and
    # the display should say so rather than assert it.
    uncertain = set()

    def note_node(key, word, entry, force=False):
        # citation spellings may reach an entry first (an accented вода́
        # resolving onto ru:вода) but the page's own word is authoritative
        if force or key not in node_word:
            node_word[key] = word
        if entry:
            node_entry.add(key)

    def add_edge(p, c, kind):
        if p == c:
            return
        cur = edges.get((p, c))
        if cur is None or RANK[kind] > RANK[cur]:
            edges[(p, c)] = kind

    def walk_desc(nodes, parent_key, parent_ctx):
        for nd in nodes:
            code, w = nd.get("lang_code"), nd.get("word")
            if not code or not w:
                if nd.get("d"):
                    walk_desc(nd["d"], parent_key, parent_ctx)
                continue
            if code not in langnames and nd.get("lang"):
                langnames[code] = nd["lang"]
            hint = tokens(nd.get("sense", ""))
            ckey, entry, _how, trusted = resolve(code, w, hint, set(), parent_ctx)
            note_node(ckey, w.lstrip("*").strip(), entry)
            # An untrusted landing is demoted to a root-kind edge: still on
            # record, still in the rail, but never a step the chain walks
            # unless nothing else exists. This is what severs sin from sun
            # and dough from day without deleting anything.
            kind = "bor" if nd.get("b") else "inh"
            if not trusted:
                stats["demoted"] += 1
                kind = "root"
            add_edge(parent_key, ckey, kind)
            if nd.get("d"):
                # A doubtful landing must not anchor what hangs below it. The
                # moon tree's ME ref once fell to mone "lamentation"; the edge
                # was rightly demoted, but the subtree stayed attached, so
                # lamentation acquired moon as a trusted child. Children of an
                # untrusted node climb over it to the last trusted ancestor.
                walk_desc(nd["d"], ckey if trusted else parent_key,
                          (hint or parent_ctx) | wtok(w))

    def scriptclass(w):
        for ch in w:
            o = ord(ch)
            if o > 64:
                return o >> 8
        return 0

    def ladder_ok(deep_term, shallow_key):
        """A ladder edge asserts descent between two spellings the citing
        page lines up. Different scripts may look arbitrarily unalike
        (oryza -> riso), but within one script the words should share a
        prefix: rif -> ris (2 letters) is the reef lexeme colliding with
        the rice phantom, not a descent."""
        a = defold(deep_term).lstrip("*")
        b = defold(shallow_key.split(":", 1)[1]).lstrip("*")
        if not a or not b:
            return False
        if scriptclass(a) != scriptclass(b):
            return True
        n = 0
        m = min(len(a), len(b))
        while n < m and a[n] == b[n]:
            n += 1
        if n >= 3:
            return True
        # zingiberi/gingiber share no prefix but seven interior letters;
        # rif/ris share two letters however you slice them
        best = 0
        for i2 in range(len(a)):
            for j2 in range(len(b)):
                k2 = 0
                while (i2 + k2 < len(a) and j2 + k2 < len(b)
                       and a[i2 + k2] == b[j2 + k2]):
                    k2 += 1
                if k2 > best:
                    best = k2
        return best >= 4

    pending_ladder = []
    done = 0
    with io.open(os.path.join(EX, "source2.jsonl"), encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            e = json.loads(line)
            n_ent = norm_n(e.get("n", 0))
            if n_ent == 0 and (e["c"] + SEP + e["w"]) in split_sid:
                hit = own_etymon_ids(e.get("t")) & split_sid[e["c"] + SEP + e["w"]]
                if hit:
                    n_ent = norm_n("sid:" + min(hit))
            akey, ask, an = anchored_key(e["c"], e["w"], n_ent)
            note_node(akey, e["w"], True, force=True)
            ctx = tokens(glosses.get(ask + SEP + str(an), "")) | wtok(e["w"])
            have_primary = akey in primary_of
            # "From Middle English concurrent, from Old French concurrent,
            # from Latin concurrens": when a cited stage has no page of its
            # own, the citing page's ladder is the only ancestry it has, so
            # consecutive citations chain -- but only onto phantoms; a real
            # entry defines its own ancestry.
            prev_key, prev_entry, prev_kind = None, True, None
            open_pending = None
            cited_seen = set()
            for kind, lg, term, gh, ih, unc, subs in parse_templates(
                    e.get("t") or [], e["c"], e["w"]):
                pkey, entry, how, trusted = resolve(lg, term, gh, ih, ctx,
                                                    e["w"])
                if not trusted and kind in ("inh", "bor", "der", "cal"):
                    stats["demoted"] += 1
                    kind = "root"
                # A formation part that resolves only by guessing among senses is
                # dropped rather than attached. The guess is what made Korea a
                # child of Core, the birth name of Persephone: {{af|en|Core|-ia}}
                # meant the old name for Korea, the resolver had no hint, and
                # sense 1 happened to be the goddess. A wrong component rewrites
                # the whole lineage, so no edge beats a guessed one. Affixes are
                # exempt: they are barred from lineage anyway, and their sense
                # only labels the formation view.
                if kind == "form" and how == "first" and not is_affix_term(term)                         and defold(term) not in defold(e["w"]):
                    # Substring is the tell. teach sits inside teacher, Baby
                    # inside Antibabypille -- when the part appears in the word
                    # it formed, the spelling is right and sense 1 is almost
                    # always the base sense, so the guess is safe. Core does not
                    # sit inside Korea; there the guess picked Persephone.
                    stats["form guess dropped"] += 1
                    continue
                note_node(pkey, term.lstrip("*").strip(), entry)
                add_edge(pkey, akey, kind)
                if unc and pkey != akey:
                    uncertain.add((pkey, akey))
                if (open_pending is not None and open_pending[2] is None
                        and pkey not in (open_pending[0], open_pending[1])):
                    open_pending[2] = pkey
                    open_pending = None
                # "borrowed from X; displaced native Y": an inherited
                # citation after a borrowing starts a new run, it is not a
                # deeper rung of the borrowed line
                if kind == "inh" and prev_kind in ("der", "bor", "cal"):
                    prev_key, prev_entry = None, True
                if (prev_key is not None and not prev_entry and not entry
                        and kind not in ("root", "form") and trusted
                        and pkey != prev_key and not is_affix_term(term)
                        and pkey not in cited_seen
                        and ladder_ok(term, prev_key)):
                    # both ends phantom: a real entry ends the "from X, from
                    # Y" run -- pages also write "compare French ontologie"
                    # after a coinage, and that is parallelism, not descent
                    add_edge(pkey, prev_key, kind)
                    stats["phantom ladder"] += 1
                elif (prev_key is not None and not prev_entry and entry
                        and kind not in ("root", "form") and trusted
                        and pkey != prev_key and not is_affix_term(term)
                        and pkey not in cited_seen):
                    # phantom-then-entry is ambiguous (salaire continues the
                    # salary ladder; ontologie is a mere parallel); hold it
                    # until the page's NEXT citation can vouch that it names
                    # one of the entry's own recorded parents
                    open_pending = [pkey, prev_key, None]
                    pending_ladder.append(open_pending)
                cited_seen.add(pkey)
                prev_key, prev_entry = (None, True) if kind in ("root", "form")                     else (pkey, entry)
                prev_kind = None if kind in ("root", "form") else kind
                for k2, lg2, t2 in subs:
                    if is_affix_term(t2):
                        continue
                    skey, sentry, _show, strust = resolve(
                        lg2, t2, set(), set(), ctx, e["w"])
                    if not strust and k2 in ("inh", "bor", "der", "cal"):
                        k2 = "root"
                    note_node(skey, t2.lstrip("*").strip(), sentry)
                    if skey != pkey:
                        add_edge(skey, pkey, k2)
                        stats["ety tree"] += 1
                if (not have_primary and kind != "root" and pkey != akey
                        and (not is_affix_term(term)
                             or is_affix_term(e["w"]))):
                    # an affix never anchors a word's lineage, but an affix
                    # PAGE has an affix lineage of its own: -er descends from
                    # Old English -ere and Proto-Germanic *-ārijaz
                    primary.add((pkey, akey))
                    primary_of.add(akey)
                    have_primary = True
            if e.get("d"):
                walk_desc(e["d"], akey, ctx)
            done += 1
            if done % 500000 == 0:
                print("  {:>9,} entries   {:>9,} edges".format(done, len(edges)),
                      flush=True)

    print("  resolution: " + "   ".join(
        "{} {:,}".format(k, v) for k, v in stats.most_common()), flush=True)

    # An alternative-form entry has no templates of its own; its gloss is
    # the link. "alternative form of gingivere" hands gingere the lemma
    # whose page carries the whole spice-trade ladder.
    ALTGLOSS = re.compile(
        r"^(?:(?:alternative|alternate|obsolete|archaic|dialectal|rare|"
        r"nonstandard|dated|early|later|medieval|informal|poetic|humorous|"
        r"eye dialect|misspelling|misconstruction|pre-reform|post-reform|"
        r"superseded|uncommon)\s+)*"
        r"(?:form|spelling|typography|romanization|romanisation)\s+of\s+"
        r"([^,;:.()]+?)\s*(?:\([^()]*\))?[\s.]*$", re.I)
    n_alt = 0
    for sk_a, ns_a in sense_ns.items():
        c_a, w_a = sk_a.split(SEP, 1)
        for n_a in ns_a:
            g_a = glosses.get(sk_a + SEP + str(n_a), "")
            m_a = ALTGLOSS.match(g_a)
            if not m_a:
                continue
            tail = m_a.group(1).strip()
            if not tail or len(tail.split()) > 3:
                continue
            if strip_marks(tail) == strip_marks(w_a):
                # a true self-reference; but Kaiser/kaiser differ by case
                # and that alternative-form link is real
                continue
            vkey = kf(sk_a, n_a, ns_a)
            if vkey not in node_word:
                continue
            lkey, lentry, _how, _lt = resolve(
                c_a, tail, set(), set(), tokens(g_a) | wtok(w_a), w_a)
            if not lentry:
                # the page spells the lemma enġel; the registry holds engel
                tail2 = strip_marks(tail)
                if tail2 != tail:
                    lkey, lentry, _how, _lt = resolve(
                        c_a, tail2, set(), set(),
                        tokens(g_a) | wtok(w_a), w_a)
            if not lentry or lkey == vkey:
                continue
            if (vkey, lkey) in edges:
                # the variant is already cited as the lemma's own parent
                # (apricot lists apricock); a back-link would be a cycle
                continue
            if is_affix_term(tail) != is_affix_term(w_a):
                continue
            note_node(lkey, tail.lstrip("*").strip(), True)
            add_edge(lkey, vkey, "der")
            # the lemma IS the variant page's stated origin; if nothing else
            # claims the primary slot, this link is the page walk
            if vkey not in primary_of:
                primary.add((lkey, vkey))
                primary_of.add(vkey)
            n_alt += 1
    print("alt-form lemma links: {:,}".format(n_alt), flush=True)

    # A held phantom-then-entry pair joins the ladder only if the citation
    # after the entry names one of the entry's own recorded parents: the
    # salary page's next stop (salarium) is exactly what salaire's page
    # cites, while nothing after ontologie matches its parents.
    def bridge_ok(entry_key, ph_key):
        """A bridge through an entry needs more evidence than a plain
        ladder: every genuine one (salaire/salarie, gingifer/gingiber,
        quarantina/quarenteine, concurrens/concurrent) shares five or
        more letters; cocco/coche share three, and that was a coconut
        grafted onto a coach."""
        a = defold(node_word.get(entry_key, "")).lstrip("*")
        b = defold(node_word.get(ph_key) or ph_key.split(":", 1)[1]).lstrip("*")
        if not a or not b:
            return False
        if scriptclass(a) != scriptclass(b):
            return True
        n = 0
        m = min(len(a), len(b))
        while n < m and a[n] == b[n]:
            n += 1
        if n >= 5:
            return True
        best = 0
        for i2 in range(len(a)):
            for j2 in range(len(b)):
                k2 = 0
                while (i2 + k2 < len(a) and j2 + k2 < len(b)
                       and a[i2 + k2] == b[j2 + k2]):
                    k2 += 1
                if k2 > best:
                    best = k2
        return best >= 5

    if pending_ladder:
        childmap = collections.defaultdict(set)
        for (pp, cc) in edges:
            childmap[cc].add(pp)
        n_bridge = 0
        for entry_key, ph_key, nxt in pending_ladder:
            if not nxt:
                # the run ends at this entry; with no next citation to vouch,
                # accept only a parentless entry (nothing to contradict) that
                # is word-plausible against the phantom: concurrens closes
                # concurrent's run, while ontologie (whose page has parents,
                # among them the very phantom) stays a parallel
                if childmap.get(entry_key):
                    continue
                if not bridge_ok(entry_key, ph_key):
                    continue
                if (entry_key, ph_key) not in edges:
                    add_edge(entry_key, ph_key, "der")
                    n_bridge += 1
                if ph_key not in primary_of:
                    primary.add((entry_key, ph_key))
                    primary_of.add(ph_key)
                continue
            nf = defold(node_word.get(nxt) or nxt.split(":", 1)[1])
            nl = nxt.split(":", 1)[0]
            for par in childmap.get(entry_key, ()):
                # the vouching match must be the same word in the same
                # language: es:coco naming pt:coco vouched the coconut as
                # a parent of Middle French coche, and coach grew a palm
                pl2 = par.split(":", 1)[0]
                if pl2 != nl:
                    continue
                pw = defold(node_word.get(par) or par.split(":", 1)[1])
                if pw == nf or (len(pw) >= 5 and len(nf) >= 5
                                and pw[:5] == nf[:5]):
                    if (entry_key, ph_key) not in edges:
                        add_edge(entry_key, ph_key, "der")
                        n_bridge += 1
                    # a vouched bridge is corroborated by the citing page
                    # naming the entry's own parent next; that makes it the
                    # phantom's primary, and the monopoly bars colliding
                    # spellings (the coconut tree's coche stays out of the
                    # coach's lineage)
                    if ph_key not in primary_of:
                        primary.add((entry_key, ph_key))
                        primary_of.add(ph_key)
                    break
        print("ladder bridges through entries: {:,}".format(n_bridge),
              flush=True)

    # ---- diacritic phantoms (case preserved) --------------------------------
    def fold(s):
        return "".join(ch for ch in unicodedata.normalize("NFD", s)
                       if not unicodedata.combining(ch))

    real = {}
    for key in sorted(node_entry):
        c = key.split(":", 1)[0]
        real.setdefault((c, fold(node_word[key])), key)
    # A participle page with no templates and no descendants never reaches
    # source2, yet concurrens is a real entry; registry spellings make
    # legitimate redirect targets too (single-sense only -- a homograph
    # would need sense evidence a phantom cannot offer).
    for sk2, ns2 in sense_ns.items():
        if len(ns2) != 1:
            continue
        c2, w2 = sk2.split(SEP, 1)
        real.setdefault((c2, fold(w2)), intern(c2 + ":" + w2))

    def gloss_of_key(key):
        c, rest = key.split(":", 1)
        base = rest.split("#")[0]
        n = rest[len(base) + 1:] if "#" in rest else "0"
        return glosses.get(c + SEP + base + SEP + n, "")

    def soft_match(a, b):
        for ta in a:
            for tb in b:
                if ta == tb:
                    return True
                if len(ta) >= 4 and len(tb) >= 4 and                         (ta.startswith(tb) or tb.startswith(ta)):
                    return True
        return False

    # Wiktionary files medieval and new Latin under plain Latin entries, so
    # a la-med or la-new citation may fold onto the la page (influentia).
    LANGVAR = {"la-med": "la", "la-new": "la", "la-vul": "la",
               "la-ecc": "la", "la-lat": "la",
               "LL.": "la", "ML.": "la", "NL.": "la", "VL.": "la",
               "EL.": "la"}
    cand = {}
    for key in node_word:
        if key in node_entry:
            continue
        c = key.split(":", 1)[0]
        tgt = real.get((c, fold(node_word[key])))
        if not tgt and c in LANGVAR:
            tgt = real.get((LANGVAR[c], fold(node_word[key])))
        if tgt and tgt != key:
            cand[key] = tgt

    # The redirect must prove the target is the same word, or stay a phantom.
    # Old English daġ (a variant of dæġ, "day") folded into dag, an entry that
    # means dough, and the whole day lineage inherited a kitchen. Neighbours
    # know better: compare the target's gloss against the words and glosses
    # around the phantom, prefix-leniently, since "defend" must match
    # "defending" or mūnītiō never reaches mūniō.
    neigh = collections.defaultdict(set)
    for (pp, cc) in edges:
        if pp in cand:
            neigh[pp] |= wtok(node_word.get(cc, "")) | tokens(gloss_of_key(cc))
        if cc in cand:
            neigh[cc] |= wtok(node_word.get(pp, "")) | tokens(gloss_of_key(pp))
    def word_prefix_ok(tgt, nb):
        """Gloss evidence fails for participles: concurrēns must reach the
        entry concurrens although "running with others" shares nothing with
        "simultaneous". The words themselves are evidence -- a neighbour
        sharing a 5-letter prefix with the target (concurrent/concurrens: 8)
        vouches for the fold; dag/day share two and stay apart."""
        w = fold(node_word.get(tgt, "")).lower()
        for t in nb:
            n2 = 0
            m = min(len(w), len(t))
            while n2 < m and w[n2] == t[n2]:
                n2 += 1
            if n2 >= 5:
                return True
        return False

    alias, skipped = {}, 0
    for key, tgt in cand.items():
        g = tokens(gloss_of_key(tgt))
        nb = neigh.get(key)
        if g and nb and not soft_match(g, nb) and not word_prefix_ok(tgt, nb):
            skipped += 1
            continue
        alias[key] = tgt
    # medieval, new and late Latin phantoms of one spelling are one word;
    # unfolded they keep ladders apart (la-med:gingiber vs la-lat:gingiber)
    n_lvar = 0
    for key in list(node_word):
        if key in node_entry or key in alias:
            continue
        c_v = key.split(":", 1)[0]
        if c_v in LANGVAR:
            tgt2 = LANGVAR[c_v] + ":" + key.split(":", 1)[1]
            if tgt2 != key:
                if tgt2 not in node_word:
                    node_word[tgt2] = node_word[key]
                alias[key] = tgt2
                n_lvar += 1
    print("latin-variant phantoms folded: {:,}".format(n_lvar), flush=True)
    for key, tgt in alias.items():
        if tgt not in node_word:
            node_word[tgt] = tgt.split(":", 1)[1]
            node_entry.add(tgt)
    print("diacritic phantoms redirected: {:,}   kept as phantoms: {:,}".format(
        len(alias), skipped), flush=True)
    if alias:
        def unalias(k):
            # folding can chain: la-med:-alis -> la:-alis -> the entry
            hops = 0
            while k in alias and hops < 6:
                k = alias[k]
                hops += 1
            return k
        remapped = {}
        reprim = set()
        reunc = set()
        for (p, c), kind in edges.items():
            p2, c2 = unalias(p), unalias(c)
            if p2 == c2:
                continue
            if (p, c) in primary:
                reprim.add((p2, c2))
            if (p, c) in uncertain:
                reunc.add((p2, c2))
            cur = remapped.get((p2, c2))
            if cur is None or RANK[kind] > RANK[cur]:
                remapped[(p2, c2)] = kind
        edges = remapped
        primary = reprim
        uncertain = reunc
        for k in alias:
            node_word.pop(k, None)

    # ---- write --------------------------------------------------------------
    nodes_out = {}
    for key, word in node_word.items():
        c, rest = key.split(":", 1)
        base = rest.split("#")[0]
        n = rest[len(base) + 1:] if "#" in rest else "0"
        g = glosses.get(c + SEP + base + SEP + n, "") if key in node_entry else ""
        nodes_out[key] = {"lang_code": c, "lang": langnames.get(c, ""),
                          "word": word, "gloss": g, "entry": key in node_entry}

    kinds = collections.Counter(edges.values())
    print("\nnodes {:,}   edges {:,}".format(len(nodes_out), len(edges)))
    for k, v in kinds.most_common():
        print("  {:<6} {:>9,}".format(k, v))

    with io.open(os.path.join(OUT, "nodes2.json"), "w", encoding="utf-8") as fh:
        json.dump(nodes_out, fh, ensure_ascii=False)
    n_prim = sum(1 for pc in edges if pc in primary)
    n_unc = sum(1 for pc in edges if pc in uncertain)
    print("primary page-links: {:,}   uncertain: {:,}".format(n_prim, n_unc))
    with io.open(os.path.join(OUT, "edges2.json"), "w", encoding="utf-8") as fh:
        json.dump([[p, c, ("P" if (p, c) in primary else "")
                    + ("?" if (p, c) in uncertain else "") + k]
                   for (p, c), k in sorted(edges.items())],
                  fh, ensure_ascii=False)
    up = collections.Counter()
    for (p, c) in edges:
        up[c] += 1
    orphans = sum(1 for k in nodes_out if not up.get(k))
    print("nodes with no parent: {:,} ({:.0%})".format(
        orphans, orphans / len(nodes_out)))
    print("wrote nodes2.json / edges2.json")


if __name__ == "__main__":
    main()
