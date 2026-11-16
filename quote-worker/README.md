# Chunklet quote Worker (free, no API key)

Picks a line from the western canon. Replaced the old AWS Lambda
(`chubby-chunklet-dev-chunklet`, deleted 2026-11-15) with the same request/response shape.

**Deployed:** `https://chunklet-quotes.kevin-murawinski.workers.dev`

Used by: this site (`index.html`, `airmail.html`), the heist newsletter
(`pigeon/heist/sources/chunklet.py`) and autococobolodesk (`channel.js`).

## The pool

`pool.json` is ~11.8k `[text, work, author]` rows from 65 public-domain Project Gutenberg
books by 44 authors, built in three steps:

1. **`mine.py`** cuts every book into passages of whole sentences (12 to 40 words) from ONE
   speech (Shakespeare, split into plays by heading) or ONE paragraph/stanza (everything
   else), scrubs stage directions, footnotes, dashes and broken quote marks, then keeps the
   most vivid third of each work by color score (~30k candidates).
2. **`audit.py`** has a LOCAL Ollama model (free, nothing leaves the Mac) read the candidates
   in shuffled batches of 20 and pick the ones worth hearing out loud on their own (~4 in 10).
   Resumable: re-run it and it only scores what's missing.
3. **`build_pool.py`** joins the picks into `pool.json`, with a last scrub (unbalanced quotes,
   leftover speaker tags and stage directions).

```bash
python3 mine.py TEXTS_DIR candidates.json        # TEXTS_DIR = the Gutenberg .txt files named in BOOKS
python3 audit.py candidates.json scores.jsonl     # ~1-4 hours on the M1 Max, qwen3:30b
python3 build_pool.py candidates.json scores.jsonl pool.json
```

The Gutenberg ids are the keys of `BOOKS` in `mine.py` (fetch `https://www.gutenberg.org/cache/epub/{id}/pg{id}.txt`).
The few named keys (`virgil`, `dante`, `proust`...) are the old Lambda's texts, backed up in
`~/Documents/chubby-chunklet-lambda-backup.zip` (not in git). Shakespeare is Gutenberg #100.

Each press in the Worker: weighted category (Shakespeare tragedy/comedy/history/romance/poetry,
ancient, philosophers, poets, satire, 19th c. novel, Russian, modern...) -> uniform author or
play -> uniform line, so a huge book can't crowd out a small one.

## Deploy / test

```bash
cd quote-worker && npx wrangler deploy
curl "https://chunklet-quotes.kevin-murawinski.workers.dev/?only_quote=1"
curl "https://chunklet-quotes.kevin-murawinski.workers.dev/?stats=1"
```
