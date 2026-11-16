// Chunklet quote Worker (free, no API key). Replaces the old AWS Lambda
// (chubby-chunklet-dev-chunklet) with the same request/response shape, so callers only
// swap the URL.
//
// pool.json = [text, work, author] rows pre-mined from the Lambda's own public-domain texts
// with its own cleaning + scoring: only the top 25% of each Shakespeare play / other author,
// which is all the Lambda's pickLine ever drew from. Rebuild it with mine.js (see README).
import POOL from "./pool.json";

const CATEGORY_WEIGHTS = {
  shakespeare_tragedy: 18, shakespeare_comedy: 16, shakespeare_history: 8,
  shakespeare_romance: 5, shakespeare_poetry: 5,
  ancient_greek: 6, ancient_roman: 2, medieval: 2, renaissance: 6,
  enlightenment: 4, romantic: 8, modern_fiction: 20,
};
const AUTHOR_CATEGORIES = {
  ancient_greek: ["Sophocles"],
  ancient_roman: ["Virgil"],
  medieval: ["Dante", "Chaucer"],
  renaissance: ["Montaigne", "Cervantes", "John Milton"],
  enlightenment: ["Voltaire"],
  romantic: ["Walt Whitman", "Emily Dickinson", "Oscar Wilde"],
  modern_fiction: ["Kafka", "Marcel Proust", "James Joyce", "Oscar Wilde", "Emily Dickinson", "Walt Whitman"],
};
const SHAKESPEARE_CATEGORIES = {
  tragedy: ["Hamlet", "Macbeth", "Othello", "King Lear", "Romeo and Juliet", "Julius Caesar",
    "Antony and Cleopatra", "Coriolanus", "Timon of Athens", "Titus Andronicus", "Troilus and Cressida"],
  comedy: ["The Comedy of Errors", "The Taming of the Shrew", "The Two Gentlemen of Verona",
    "Love's Labour's Lost", "A Midsummer Night's Dream", "The Merchant of Venice",
    "The Merry Wives of Windsor", "Much Ado About Nothing", "As You Like It", "Twelfth Night",
    "All's Well That Ends Well", "Measure for Measure"],
  history: ["King John", "Richard II", "Richard III", "Henry IV Part 1", "Henry IV Part 2", "Henry V",
    "Henry VI Part 1", "Henry VI Part 2", "Henry VI Part 3", "Henry VIII"],
  romance: ["The Winter's Tale", "The Tempest", "Pericles", "Cymbeline", "The Two Noble Kinsmen"],
  poetry: ["Sonnets"],
};

// Index once per isolate: Shakespeare by work, everyone else by author.
const BY_WORK = {}, BY_AUTHOR = {};
for (const [text, work, author] of POOL) {
  const e = { text, work, author };
  if (author === "Shakespeare") (BY_WORK[work] ||= []).push(e);
  else (BY_AUTHOR[author] ||= []).push(e);
}
const rand = (arr) => arr[(Math.random() * arr.length) | 0];

function selectByWeight() {
  const r = Math.random() * 100;
  let c = 0;
  for (const [cat, w] of Object.entries(CATEGORY_WEIGHTS)) { c += w; if (r < c) return cat; }
  return "shakespeare_tragedy";
}

// Same draw as the Lambda: weighted category, then a work (Shakespeare) or author (others),
// then a line from that group. The Lambda's round-robin lived in /tmp and reset on every cold
// start anyway, so a uniform pick of the work/author is equivalent.
function pickLine(authorQ) {
  if (authorQ) {
    const rows = POOL.filter((r) => r[2].toLowerCase().includes(authorQ));
    if (!rows.length) return { text: "Nothing from that author today.", work: "Unknown", author: authorQ };
    const [text, work, author] = rand(rows);
    return { text, work, author };
  }
  const cat = selectByWeight();
  if (cat.startsWith("shakespeare_")) {
    const works = SHAKESPEARE_CATEGORIES[cat.slice(12)].filter((w) => BY_WORK[w]);
    if (works.length) return rand(BY_WORK[rand(works)]);
  } else {
    const authors = AUTHOR_CATEGORIES[cat].filter((a) => BY_AUTHOR[a]);
    if (authors.length) return rand(BY_AUTHOR[rand(authors)]);
  }
  const [text, work, author] = rand(POOL);
  return { text, work, author };
}

function sanitizeOutgoing(t) {
  t = (t || "").trim().replace(/!+$/, "").replace(/\s+/g, " ");
  return /[.?!]$/.test(t) ? t : t + ".";
}

// Fake lip-sync track (t in seconds + open 0..1), same recipe as the Lambda. The page only uses
// it for the mouth when the browser's built-in voice is talking (phones).
function fabricateTimingsFor(text) {
  const base = Math.min(10, Math.max(2.5, text.length * 0.05));
  const frames = Math.max(32, Math.round(base * 16));
  const arr = [];
  for (let i = 0; i <= frames; i++) {
    const ch = text[Math.floor((i / frames) * text.length)] || " ";
    let open;
    if (/\s/.test(ch)) open = Math.random() * 0.25;
    else if (/[aeiouy]/i.test(ch)) open = 0.65 + Math.random() * 0.35;
    else open = 0.35 + Math.random() * 0.4;
    if (Math.random() < 0.05) open = 1;
    arr.push({ t: (i / frames) * base, open });
  }
  return arr;
}

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET,OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
};
const json = (obj) => new Response(JSON.stringify(obj), {
  headers: { ...CORS, "Content-Type": "application/json", "Cache-Control": "no-store" },
});

export default {
  async fetch(req) {
    if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: CORS });
    const qs = new URL(req.url).searchParams;

    if (qs.get("health") === "1") return json({ ok: true, lines: POOL.length });
    if (qs.get("stats") === "1") {
      const by = {};
      for (const r of POOL) by[r[2]] = (by[r[2]] || 0) + 1;
      return json({ total: POOL.length, by_author: by });
    }
    // TTS moved into the browser (Kokoro); keep the old phase answering so callers fall back cleanly.
    if (qs.get("only_tts") === "1") return json({ audioBase64: null, diag: { phase: "tts", returned: false } });

    const { text: raw, work, author } = pickLine((qs.get("author") || "").toLowerCase());
    const text = sanitizeOutgoing(raw);
    return json({
      text,
      audioBase64: null,
      timings: fabricateTimingsFor(text),
      work, author,
      context: null, // the page fetches line-specific context from chunklet-context
      idleMouth: false,
      diag: { phase: qs.get("only_quote") === "1" ? "quote" : "legacy", source: "cf-worker" },
    });
  },
};
