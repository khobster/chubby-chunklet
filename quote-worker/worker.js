// Chunklet quote Worker (free, no API key). Replaces the old AWS Lambda
// (chubby-chunklet-dev-chunklet) with the same request/response shape, so callers only
// swap the URL.
//
// pool.json = [text, work, author] rows mined from Project Gutenberg texts (mine.py) and kept
// by a taste audit (audit.py, local Ollama). See README for the rebuild steps.
import POOL from "./pool.json";

// Each press: weighted category -> uniform author (or play) -> uniform line, so a huge book
// (Proust, Dickens) can't crowd out a small one (Blake, Gibran). Weights needn't sum to 100.
const CATEGORY_WEIGHTS = {
  shakespeare_tragedy: 14, shakespeare_comedy: 12, shakespeare_history: 6,
  shakespeare_romance: 4, shakespeare_poetry: 4,
  ancient: 5, philosophers: 7, medieval_renaissance: 4, satire: 7, poets: 9,
  gothic_adventure: 5, novel_19c: 7, russian: 3, modern: 7,
};
const AUTHOR_CATEGORIES = {
  ancient: ["Homer", "Sophocles", "Virgil"],
  philosophers: ["Marcus Aurelius", "Lao Tzu", "Montaigne", "Henry David Thoreau", "Ralph Waldo Emerson",
    "Friedrich Nietzsche", "Kahlil Gibran"],
  medieval_renaissance: ["Dante", "Chaucer", "Cervantes", "John Milton"],
  satire: ["Voltaire", "Jonathan Swift", "Mark Twain", "Oscar Wilde", "Lewis Carroll"],
  poets: ["William Blake", "Samuel Taylor Coleridge", "John Keats", "Robert Burns", "Walt Whitman",
    "Emily Dickinson", "W. B. Yeats", "Edgar Allan Poe"],
  gothic_adventure: ["Mary Shelley", "Edgar Allan Poe", "Robert Louis Stevenson", "Arthur Conan Doyle", "Herman Melville"],
  novel_19c: ["Charles Dickens", "Jane Austen", "Charlotte Brontë", "Emily Brontë"],
  russian: ["Fyodor Dostoevsky", "Leo Tolstoy"],
  modern: ["Kafka", "Marcel Proust", "James Joyce", "F. Scott Fitzgerald", "Virginia Woolf", "Ernest Hemingway"],
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
  poetry: ["Sonnets", "Venus and Adonis", "The Rape of Lucrece", "A Lover's Complaint",
    "The Passionate Pilgrim", "The Phoenix and the Turtle"],
};

// Index once per isolate: Shakespeare by work, everyone else by author.
const BY_WORK = {}, BY_AUTHOR = {};
POOL.forEach(([text, work, author], id) => {
  const e = { text, work, author, id };
  if (author === "Shakespeare") (BY_WORK[work] ||= []).push(e);
  else (BY_AUTHOR[author] ||= []).push(e);
});
const rand = (arr) => arr[(Math.random() * arr.length) | 0];

const WEIGHT_TOTAL = Object.values(CATEGORY_WEIGHTS).reduce((a, b) => a + b, 0);
function selectByWeight() {
  const r = Math.random() * WEIGHT_TOTAL;
  let c = 0;
  for (const [cat, w] of Object.entries(CATEGORY_WEIGHTS)) { c += w; if (r < c) return cat; }
  return "shakespeare_tragedy";
}

// Same draw as the Lambda: weighted category, then a work (Shakespeare) or author (others),
// then a line from that group. The Lambda's round-robin lived in /tmp and reset on every cold
// start anyway, so a uniform pick of the work/author is equivalent.
function pickLine(authorQ) {
  if (authorQ) {
    const ids = [];
    POOL.forEach((r, i) => { if (r[2].toLowerCase().includes(authorQ)) ids.push(i); });
    if (!ids.length) return { text: "Nothing from that author today.", work: "Unknown", author: authorQ, id: null };
    const id = rand(ids), [text, work, author] = POOL[id];
    return { text, work, author, id };
  }
  const cat = selectByWeight();
  if (cat.startsWith("shakespeare_")) {
    const works = SHAKESPEARE_CATEGORIES[cat.slice(12)].filter((w) => BY_WORK[w]);
    if (works.length) return rand(BY_WORK[rand(works)]);
  } else {
    const authors = AUTHOR_CATEGORIES[cat].filter((a) => BY_AUTHOR[a]);
    if (authors.length) return rand(BY_AUTHOR[rand(authors)]);
  }
  const id = (Math.random() * POOL.length) | 0, [text, work, author] = POOL[id];
  return { text, work, author, id };
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

    const { text: raw, work, author, id } = pickLine((qs.get("author") || "").toLowerCase());
    const text = sanitizeOutgoing(raw);
    return json({
      text,
      audioBase64: null,
      timings: fabricateTimingsFor(text),
      work, author,
      id, // pool row; the phone voice plays chunklet-voice.pages.dev/a/<id>.m4a (voice/render.py)
      context: null, // the page fetches line-specific context from chunklet-context
      idleMouth: false,
      diag: { phase: qs.get("only_quote") === "1" ? "quote" : "legacy", source: "cf-worker" },
    });
  },
};
