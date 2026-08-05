// Chubby Chunklet — snippet context Worker (Cloudflare Workers AI, free tier).
// Explains the SPECIFIC line being featured, not a broad summary of the source.
// Deploy: `wrangler deploy` from this folder. Then paste the deployed URL into
// index.html's CONTEXT_ENDPOINT.

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
  'Access-Control-Allow-Headers': 'content-type',
};

export default {
  async fetch(req, env) {
    if (req.method === 'OPTIONS') return new Response(null, { headers: CORS });
    const url = new URL(req.url);
    const q = (url.searchParams.get('q') || '').slice(0, 600);
    const work = (url.searchParams.get('work') || '').slice(0, 160);
    const author = (url.searchParams.get('author') || '').slice(0, 160);

    const json = (obj) =>
      new Response(JSON.stringify(obj), { headers: { ...CORS, 'content-type': 'application/json' } });

    if (!q) return json({ context: '' });

    const src = [work && `from “${work}”`, author && `by ${author}`].filter(Boolean).join(' ');
    const prompt =
      `You explain a single quoted line for a general audience. In 1–2 short sentences, ` +
      `say what THIS specific line means and the moment/idea behind it — be specific to the line, ` +
      `not a general summary of the work. No preamble, no quotes around your answer.\n\n` +
      `Line: "${q}"${src ? ' (' + src + ')' : ''}.`;

    try {
      const r = await env.AI.run('@cf/meta/llama-3.3-70b-instruct-fp8-fast', {
        messages: [{ role: 'user', content: prompt }],
        max_tokens: 140,
        temperature: 0.6,
      });
      return json({ context: (r.response || '').trim() });
    } catch (e) {
      return json({ context: '', error: String(e) });
    }
  },
};
