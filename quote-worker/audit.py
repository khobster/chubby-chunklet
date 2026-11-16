"""Taste audit: score every candidate with a LOCAL Ollama model (free), resumable.

    python3 audit.py candidates.json scores.jsonl [model]

Each output line: {"i": index, "s": 2 keep / 1 meh / 0 garbage}. Re-running skips indexes already scored.
"""
import json, random, sys, time, urllib.request
from pathlib import Path

PROMPT = """You curate lines for Chubby Chunklet, a little puppet in a cuckoo clock who pops out
and recites ONE line of classic literature aloud to strangers, with no other context.
You get 20 numbered candidate lines. Be picky.
"keep": the numbers of the lines that are genuinely good to hear on their own: quotable, vivid,
wise, funny or haunting, a complete thought a stranger gets without knowing the plot. Usually 4 to 8
of the 20. Skip lines that are plot logistics, need unknown names/context, or are merely fine.
"garbage": the numbers of lines that are broken: garbled or cut-off text, an editor's or
translator's note, a chapter summary, a footnote, or not literature at all.
Reply ONLY with JSON: {"keep":[...], "garbage":[...]}"""

def ask(model, lines):
    body = "\n".join(f"{k+1}. {t}" for k, t in enumerate(lines))
    req = {"model": model, "stream": False, "think": False, "format": "json",
           "options": {"temperature": 0, "num_ctx": 8192},
           "messages": [{"role": "system", "content": PROMPT}, {"role": "user", "content": body}]}
    r = urllib.request.urlopen(urllib.request.Request("http://localhost:11434/api/chat",
        data=json.dumps(req).encode(), headers={"Content-Type": "application/json"}), timeout=300)
    j = json.loads(json.loads(r.read())["message"]["content"])
    keep, junk = {int(x) for x in j.get("keep", [])}, {int(x) for x in j.get("garbage", [])}
    # 2 = keep, 0 = garbage, 1 = neither
    return [2 if k+1 in keep and k+1 not in junk else 0 if k+1 in junk else 1 for k in range(len(lines))]

def main(src, dst, model="qwen3:30b", batch=20):
    rows = json.load(open(src)); out = Path(dst)
    done = {json.loads(l)["i"] for l in out.read_text().splitlines()} if out.exists() else set()
    todo = [i for i in range(len(rows)) if i not in done]
    random.Random(42).shuffle(todo)   # mix authors in every batch so "best of 20" is fair
    t0 = time.time()
    with out.open("a") as f:
        for b in range(0, len(todo), batch):
            idx = todo[b:b+batch]
            try: scores = ask(model, [rows[i][0] for i in idx])
            except Exception as e: print("batch failed, will retry next run:", e, flush=True); continue
            for i, s in zip(idx, scores): f.write(json.dumps({"i": i, "s": s}) + "\n")
            f.flush()
            n = b + len(idx); rate = n / (time.time() - t0)
            if (b // batch) % 25 == 0: print(f"{n}/{len(todo)}  {rate:.1f}/s  eta {(len(todo)-n)/rate/60:.0f} min", flush=True)

if __name__ == "__main__":
    main(*sys.argv[1:])
