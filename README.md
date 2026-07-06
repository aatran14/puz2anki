# puz2anki

Turn crossword clues you liked into Anki flashcards.

You solve the NYT (or New Yorker) crossword. You spot a clue/answer pair worth
remembering. This tool downloads the puzzle, lists every clue, lets you pick the
ones you want, and drops them into your Anki deck — clue on the front, answer on
the back.

## How it works

1. Downloads the puzzle with [xword-dl](https://github.com/thisisparker/xword-dl).
2. Reads the clue → answer pairs out of the puzzle file (the answers ship inside it).
3. You type the clue numbers you want, like `36A 24A`.
4. Cards go into Anki — either as an importable `.apkg` file, or pushed straight
   in while Anki is running.

## Requirements

- [uv](https://docs.astral.sh/uv/) — runs the script and grabs its dependencies
  automatically (`brew install uv`).
- For pushing straight into Anki: the
  [AnkiConnect](https://ankiweb.net/shared/info/2055492159) add-on (code
  `2055492159`), and Anki open.

## Setup

The NYT requires a subscription, so `xword-dl` needs proof you're logged in. NYT's
password login is unreliable, so paste your browser's `NYT-S` cookie into the
config once instead:

1. Log into nytimes.com in your browser.
2. Open dev tools (`Cmd+Option+I`) → **Application** → **Cookies** →
   `https://www.nytimes.com` → copy the value of the **`NYT-S`** row.
3. Save it:

   ```sh
   mkdir -p ~/.config/xword-dl
   printf 'nyt:\n  NYT-S: "PASTE_TOKEN_HERE"\n' > ~/.config/xword-dl/xword-dl.yaml
   ```

The token lasts a long time (roughly a year); refresh it if downloads start
failing. The New Yorker (`tny`) needs no login.

## Usage

```sh
./puz2anki.py nyt                       # today's NYT
./puz2anki.py nyt --push                # push straight into Anki
./puz2anki.py nyt --date 2026-07-04     # a past puzzle (also: "last friday")
./puz2anki.py tny                       # latest New Yorker
./puz2anki.py path/to/puzzle.puz        # a local .puz file
```

Then type the clues you want at the prompt (`36A 24A`, or `all`).

### Flags

| Flag | Meaning |
|------|---------|
| `--push` | Send cards into a running Anki via AnkiConnect (no file to import). |
| `--deck NAME` | Anki deck to use (default: `NYT`). |
| `--date DATE` | Fetch a past puzzle, e.g. `2026-07-04` or `"last friday"`. |
| `--reverse` | Put the answer on the front instead of the clue. |
| `-o FILE` | Output `.apkg` path when not using `--push` (default: `crosswords.apkg`). |

Outlet keywords come from xword-dl — `nyt`, `nytm` (NYT Mini), `tny` (New Yorker),
and more. Run `xword-dl --help` for the full list.

## Without AnkiConnect

Leave off `--push` and it writes `crosswords.apkg`. Double-click it (or **File →
Import** in Anki) to load the cards. Re-importing updates existing cards instead
of duplicating them.
