# Chunklet quote Worker (free, no API key)

Picks a line from the western canon. Replaced the old AWS Lambda
(`chubby-chunklet-dev-chunklet`) on 2026-11-15 with the same request/response shape.

**Deployed:** `https://chunklet-quotes.kevin-murawinski.workers.dev`

Used by: this site (`index.html`, `airmail.html`), the heist newsletter
(`pigeon/heist/sources/chunklet.py`) and autococobolodesk (`channel.js`).

## The pool

`pool.json` is ~11k `[text, work, author]` rows, pre-mined once from the Lambda's
public-domain texts (all of Shakespeare + Virgil, Chaucer, Dante, Milton, Montaigne,
Cervantes, Voltaire, Sophocles, Whitman, Dickinson, Wilde, Proust, Joyce, Kafka) using
the Lambda's own cleaning and color scoring, keeping the top 25% of each play/author
(all the Lambda ever picked from). The source texts are still in the Lambda's deploy
package if the pool ever needs rebuilding.

## Deploy / test

```bash
cd quote-worker && npx wrangler deploy
curl "https://chunklet-quotes.kevin-murawinski.workers.dev/?only_quote=1"
curl "https://chunklet-quotes.kevin-murawinski.workers.dev/?stats=1"
```
