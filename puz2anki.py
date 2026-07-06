#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "xword-dl",
#     "puzpy",
#     "genanki",
# ]
# ///
"""puz2anki — turn crossword clues you like into Anki flashcards.

Usage:
    puz2anki.py nyt                 download today's NYT puzzle, then pick clues
    puz2anki.py tny                 download the latest New Yorker puzzle
    puz2anki.py path/to/file.puz    use a local .puz file
    puz2anki.py nyt --reverse       put the answer on the front instead

Common outlet keywords: nyt (NY Times), nytm (NYT Mini), tny (New Yorker),
tnym (New Yorker Mini). Run `xword-dl --help` for the full list.

One-time NYT setup (talks only to nytimes.com, caches a token locally):
    xword-dl nyt --authenticate
"""

import argparse
import os
import subprocess
import sys
import tempfile
import zlib

import genanki
import puz

# Fixed IDs so re-imports update existing cards instead of duplicating them.
MODEL_ID = 1607392319
DECK_ID = 2059400110

MODEL = genanki.Model(
    MODEL_ID,
    "Crossword Clue",
    fields=[
        {"name": "Clue"},
        {"name": "Answer"},
        {"name": "Enumeration"},
        {"name": "Source"},
    ],
    templates=[
        {
            "name": "Clue -> Answer",
            "qfmt": '{{Clue}} <span class="enum">{{Enumeration}}</span>',
            "afmt": '{{FrontSide}}<hr id="answer">{{Answer}}'
            '<div class="src">{{Source}}</div>',
        },
    ],
    css=(
        ".card { font-family: georgia, serif; font-size: 22px; "
        "text-align: center; color: #222; }\n"
        ".enum { color: #888; }\n"
        ".src { margin-top: 1.5em; font-size: 13px; color: #aaa; }\n"
    ),
)

REVERSE_MODEL = genanki.Model(
    MODEL_ID + 1,
    "Crossword Clue (reversed)",
    fields=[
        {"name": "Clue"},
        {"name": "Answer"},
        {"name": "Enumeration"},
        {"name": "Source"},
    ],
    templates=[
        {
            "name": "Answer -> Clue",
            "qfmt": '{{Answer}} <span class="enum">{{Enumeration}}</span>',
            "afmt": '{{FrontSide}}<hr id="answer">{{Clue}}'
            '<div class="src">{{Source}}</div>',
        },
    ],
    css=MODEL.css,
)


def download(outlet, date=None):
    """Shell out to xword-dl for the given outlet. Returns the .puz path."""
    if not _have("xword-dl"):
        sys.exit(
            "xword-dl not found. Install it, then (for NYT) run:\n"
            "    xword-dl nyt --authenticate\n"
            "(one-time login, caches a token locally)"
        )
    # Let xword-dl name the file itself; we just give it an empty folder and
    # then grab whatever .puz it drops in there.
    tmpdir = tempfile.mkdtemp()
    cmd = ["xword-dl", outlet]
    if date:
        cmd += ["--date", date]
    try:
        subprocess.run(cmd, cwd=tmpdir, check=True)
    except subprocess.CalledProcessError:
        sys.exit(
            f"Download failed for '{outlet}'. If this is NYT and your first run:\n"
            "    xword-dl nyt --authenticate"
        )
    puzzles = [f for f in os.listdir(tmpdir) if f.endswith(".puz")]
    if not puzzles:
        sys.exit(f"xword-dl ran but produced no .puz file for '{outlet}'.")
    return os.path.join(tmpdir, puzzles[0])


def _have(cmd):
    from shutil import which

    return which(cmd) is not None


def extract_clues(path):
    """Return a list of clue dicts: key, label, clue, answer, enum."""
    p = puz.read(path)
    numbering = p.clue_numbering()
    out = []
    for direction, entries, step in (
        ("A", numbering.across, 1),
        ("D", numbering.down, p.width),
    ):
        for e in entries:
            cell, length = e["cell"], e["len"]
            answer = "".join(p.solution[cell + i * step] for i in range(length))
            out.append(
                {
                    "key": f"{e['num']}{direction}",
                    "label": f"{e['num']}-{direction}",
                    "clue": e["clue"],
                    "answer": answer,
                    "enum": f"({length})",
                }
            )
    return out, _title(p, path)


def _title(p, path):
    title = (p.title or "").strip()
    return title or os.path.basename(path)


def pick_clues(clues):
    """Print all clues, prompt for a selection, return the chosen subset."""
    by_key = {c["key"]: c for c in clues}
    for c in clues:
        print(f"  {c['label']:>6}  {c['clue']} {c['enum']}")
    print()
    raw = input("Pick clues (e.g. 6A 3D 42A), 'all', or blank to cancel: ")
    tokens = raw.replace(",", " ").upper().split()
    if not tokens:
        return []
    if tokens == ["ALL"]:
        return clues
    chosen, missing = [], []
    for t in tokens:
        k = t.replace("-", "")
        if k in by_key:
            chosen.append(by_key[k])
        else:
            missing.append(t)
    if missing:
        print(f"Skipped (not found): {', '.join(missing)}", file=sys.stderr)
    return chosen


def build_deck(chosen, source, reverse, outfile, deck_name):
    model = REVERSE_MODEL if reverse else MODEL
    # Derive a stable id from the deck name so different named decks don't
    # collide, but re-running the same name always targets the same deck.
    deck_id = DECK_ID + (zlib.crc32(deck_name.encode()) & 0xFFFFF)
    deck = genanki.Deck(deck_id, deck_name)
    for c in chosen:
        guid = genanki.guid_for(source, c["label"], c["answer"])
        deck.add_note(
            genanki.Note(
                model=model,
                fields=[c["clue"], c["answer"], c["enum"], source],
                guid=guid,
            )
        )
    genanki.Package(deck).write_to_file(outfile)


def push_to_anki(chosen, source, reverse, deck_name):
    """Send cards straight into a running Anki via the AnkiConnect add-on."""
    import json
    import urllib.request

    def call(action, **params):
        req = json.dumps({"action": action, "version": 6, "params": params})
        try:
            resp = urllib.request.urlopen(
                urllib.request.Request(
                    "http://127.0.0.1:8765",
                    data=req.encode(),
                    headers={"Content-Type": "application/json"},
                ),
                timeout=5,
            )
        except OSError:
            sys.exit(
                "Can't reach Anki. Make sure Anki is open and the AnkiConnect "
                "add-on is installed (Tools > Add-ons > code 2055492159)."
            )
        out = json.loads(resp.read())
        if out.get("error"):
            raise RuntimeError(out["error"])
        return out["result"]

    call("createDeck", deck=deck_name)
    added, dupes = 0, 0
    for c in chosen:
        front = f"{c['answer']}" if reverse else f"{c['clue']} {c['enum']}"
        back = f"{c['clue']} {c['enum']}" if reverse else c["answer"]
        note = {
            "deckName": deck_name,
            "modelName": "Basic",
            "fields": {"Front": front, "Back": back},
            "tags": ["crossword", source.replace(" ", "_")],
            "options": {"allowDuplicate": False},
        }
        try:
            call("addNote", note=note)
            added += 1
        except RuntimeError as e:
            if "duplicate" in str(e).lower():
                dupes += 1
            else:
                raise
    print(f"\nAdded {added} card(s) to '{deck_name}' in Anki", end="")
    print(f" ({dupes} already there)" if dupes else "")


def main():
    ap = argparse.ArgumentParser(description="Crossword clues -> Anki cards.")
    ap.add_argument(
        "source", help="an outlet keyword (nyt, tny, ...) or a path to a .puz file"
    )
    ap.add_argument("-o", "--out", default="crosswords.apkg", help="output file")
    ap.add_argument(
        "--deck", default="NYT", help="Anki deck to import into (default: NYT)"
    )
    ap.add_argument(
        "--date", help="fetch a past puzzle, e.g. 2026-07-04 or 'last friday'"
    )
    ap.add_argument(
        "--reverse", action="store_true", help="put the answer on the front"
    )
    ap.add_argument(
        "--push",
        action="store_true",
        help="send straight into a running Anki (needs AnkiConnect add-on)",
    )
    args = ap.parse_args()

    # A source that points at an existing file is a local .puz; otherwise it's
    # an outlet keyword we hand to xword-dl.
    if os.path.exists(args.source):
        path = args.source
        cleanup = None
    else:
        path = download(args.source, args.date)
        cleanup = path

    try:
        clues, title = extract_clues(path)
    finally:
        if cleanup:
            os.unlink(cleanup)

    print(f"\n{title} — {len(clues)} clues\n")
    chosen = pick_clues(clues)
    if not chosen:
        sys.exit("Nothing selected.")

    if args.push:
        push_to_anki(chosen, title, args.reverse, args.deck)
    else:
        build_deck(chosen, title, args.reverse, args.out, args.deck)
        print(f"\nWrote {len(chosen)} card(s) to {args.out} (deck: {args.deck})")


if __name__ == "__main__":
    main()
