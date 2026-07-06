# puz2anki

Pick interesting crossword clues and send them to Anki as flashcards
(clue on front, answer on back).

## Setup

- Install [uv](https://docs.astral.sh/uv/): `brew install uv`
- For `--push`: install the AnkiConnect add-on in Anki (**Tools → Add-ons → Get
  Add-ons**, code `2055492159`) and keep Anki open.

## Usage

```sh
./puz2anki.py nyt --push
```

Downloads today's NYT, lists every clue, you type the ones you want (`36A 24A`),
they go into Anki.

## Flags

- `--push` — send straight into a running Anki (otherwise writes `crosswords.apkg` to import).
- `--date 2026-07-04` — grab a past puzzle instead of today's.
