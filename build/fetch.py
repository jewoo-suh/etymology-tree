"""Download the kaikki per-language extracts we need for the proto backbone.

kaikki URL convention: /dictionary/<Language Name>/kaikki.org-dictionary-<NameNoPunct>.jsonl
"""
import io
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

OUT = r"C:\Projects\etymology-tree-viz\data\kaikki"

# lang_code -> Wiktionary language name. Ordered roughly by importance.
PROTOS = {
    "ine-pro": "Proto-Indo-European",
    "gem-pro": "Proto-Germanic",
    "gmw-pro": "Proto-West Germanic",
    "iir-pro": "Proto-Indo-Iranian",
    "itc-pro": "Proto-Italic",
    "grk-pro": "Proto-Hellenic",
    "inc-pro": "Proto-Indo-Aryan",
    "ine-bsl-pro": "Proto-Balto-Slavic",
    "cel-pro": "Proto-Celtic",
    "sla-pro": "Proto-Slavic",
    "ira-pro": "Proto-Iranian",
    "sqj-pro": "Proto-Albanian",
    "ine-toc-pro": "Proto-Tocharian",
    "ine-ana-pro": "Proto-Anatolian",
    "cel-bry-pro": "Proto-Brythonic",
    "hyx-pro": "Proto-Armenian",
    "gmq-pro": "Proto-Norse",
    "urj-fin-pro": "Proto-Finnic",
    "urj-pro": "Proto-Uralic",
    "smi-pro": "Proto-Samic",
    "bat-pro": "Proto-Baltic",
    "cel-gae-pro": "Proto-Goidelic",
    "ira-mpr-pro": "Proto-Medo-Parthian",
    "xsc-pro": "Proto-Scythian",
}


def slug(name):
    """kaikki strips spaces and hyphens from the filename component."""
    return name.replace("-", "").replace(" ", "")


def fetch(name, dest):
    url = "https://kaikki.org/dictionary/{}/kaikki.org-dictionary-{}.jsonl".format(
        urllib.parse.quote(name), slug(name))
    req = urllib.request.Request(url, headers={"User-Agent": "etymology-tree-viz/0.1"})
    with urllib.request.urlopen(req, timeout=300) as r, io.open(dest, "wb") as fh:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            fh.write(chunk)
    return os.path.getsize(dest)


def main():
    if not os.path.isdir(OUT):
        os.makedirs(OUT)
    ok, bad = [], []
    for code, name in PROTOS.items():
        dest = os.path.join(OUT, slug(name) + ".jsonl")
        if os.path.exists(dest) and os.path.getsize(dest) > 0:
            print("  {:<14} {:<24} cached  {:>8.1f} MB".format(
                code, name, os.path.getsize(dest) / 1048576))
            ok.append(code)
            continue
        try:
            n = fetch(name, dest)
            print("  {:<14} {:<24} OK      {:>8.1f} MB".format(code, name, n / 1048576))
            ok.append(code)
        except urllib.error.HTTPError as e:
            print("  {:<14} {:<24} HTTP {}".format(code, name, e.code))
            bad.append((code, name))
            if os.path.exists(dest):
                os.remove(dest)
        except Exception as e:
            print("  {:<14} {:<24} ERR {}".format(code, name, e))
            bad.append((code, name))
            if os.path.exists(dest):
                os.remove(dest)
        time.sleep(0.5)

    print("\nfetched {}/{}".format(len(ok), len(PROTOS)))
    if bad:
        print("failed: {}".format(", ".join(c for c, _ in bad)))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
