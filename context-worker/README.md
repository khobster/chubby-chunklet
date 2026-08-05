# Chunklet context Worker (free, no API key)

Generates a 1–2 sentence explanation of the *specific* featured line using
Cloudflare Workers AI (Llama 3.3 70B, `@cf/meta/llama-3.3-70b-instruct-fp8-fast`).
Free-tier neurons; no OpenAI, no key in the page.

**Deployed:** `https://chunklet-context.kevin-murawinski.workers.dev`
(already wired into `index.html`'s `CONTEXT_ENDPOINT`).

## Deploy / redeploy

```bash
cd context-worker
npm i -g wrangler        # if you don't have it
wrangler login           # opens browser, authorize
wrangler deploy
```

Wrangler prints the URL (e.g. `https://chunklet-context.<you>.workers.dev`). A
brand-new `workers.dev` route can return error 1042/1104 for a minute or two
while the edge provisions — just retry.

## Wire it up

Open `index.html`, find `const CONTEXT_ENDPOINT = ...` near the top of the script,
and paste your Worker URL:

```js
const CONTEXT_ENDPOINT = "https://chunklet-context.kevin-murawinski.workers.dev";
```

That's it. The glasses toggle now shows line-specific context. If the Worker is
empty/unreachable, it falls back to the Wikipedia blurb automatically.

## Test

```bash
curl "https://chunklet-context.kevin-murawinski.workers.dev/?q=Lord,%20what%20fools%20these%20mortals%20be&work=A%20Midsummer%20Night's%20Dream&author=Shakespeare"
```
