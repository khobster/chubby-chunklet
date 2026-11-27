# Pre-render every quote in quote-worker/pool.json in Kokoro's Lewis voice, so phones play the
# same neural voice as desktop without running the model (too big for an iPhone tab).
#
# Out:  OUT/a/<id>.m4a          one AAC file per pool row (id = row index in pool.json)
#       OUT/m/<id // 100>.json  mouth tracks for 100 ids: {"<id>": "0379..."}, one digit
#                               (0-9 loudness) per 40 ms, so the jaw follows the real audio
#
# Same text the page shows (worker's sanitizeOutgoing) and the same per-sentence split and
# pauses as kokoroGenerate() in index.html, so it sounds like the desktop voice.
#
#   python render.py POOL OUT [WORKERS]     # resumable: skips ids already rendered
#   python render.py POOL OUT --pack        # build OUT/m shards from the per-id tracks
import json, os, re, subprocess, sys
from multiprocessing import Pool

import numpy as np

VOICE, SPEED, SR, FPS = "bm_lewis", 1.0, 24000, 25
PAUSE = {".": 0.34, "!": 0.38, "?": 0.40, ";": 0.24, ":": 0.24, "…": 0.55}


def sanitize(t):
    t = re.sub(r"\s+", " ", re.sub(r"!+$", "", (t or "").strip()))
    return t if re.search(r"[.?!]$", t) else t + "."


def split_for_speech(text):
    parts = []
    for m in re.findall(r"[^.!?;:…]+(?:\.\.\.|[.!?;:…]+)?", text.replace("...", "…")):
        t = m.strip()
        if not t:
            continue
        if parts and len(t.split()) < 2:
            parts[-1][0] += " " + t
            continue
        parts.append([t, PAUSE.get(t[-1], 0.2)])
    return parts or [[text, 0]]


def mouth_track(audio):
    hop = SR // FPS
    n = -(-len(audio) // hop)
    rms = np.array([np.sqrt(np.mean(audio[i * hop:(i + 1) * hop] ** 2) + 1e-12) for i in range(n)])
    ref = np.percentile(rms[rms > 1e-3], 95) if (rms > 1e-3).any() else 1.0
    return "".join(str(int(round(v))) for v in np.clip(rms / ref * 9, 0, 9))


_pipe = None


def render(job):
    global _pipe
    i, text, out = job
    if _pipe is None:
        import torch
        torch.set_num_threads(2)
        from kokoro import KPipeline
        _pipe = KPipeline(lang_code="b", repo_id="hexgrad/Kokoro-82M", device="cpu")
    chunks = []
    for t, pause in split_for_speech(sanitize(text)):
        for r in _pipe(t, voice=VOICE, speed=SPEED):
            if r.audio is not None:
                chunks.append(r.audio.numpy())
        chunks.append(np.zeros(int(SR * pause), dtype=np.float32))
    audio = np.concatenate(chunks).astype(np.float32)
    tmp = f"{out}/a/{i}.tmp.m4a"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-",
                    "-c:a", "aac", "-b:a", "40k", "-movflags", "+faststart", tmp],
                   input=audio.tobytes(), check=True)
    os.replace(tmp, f"{out}/a/{i}.m4a")
    with open(f"{out}/mt/{i}.txt", "w") as f:
        f.write(mouth_track(audio))
    return i


def pack(out, total):
    shards = {}
    for i in range(total):
        p = f"{out}/mt/{i}.txt"
        if os.path.exists(p):
            shards.setdefault(i // 100, {})[str(i)] = open(p).read()
    for s, d in shards.items():
        with open(f"{out}/m/{s}.json", "w") as f:
            json.dump(d, f, separators=(",", ":"))
    print(f"packed {sum(len(d) for d in shards.values())}/{total} tracks into {len(shards)} shards")


if __name__ == "__main__":
    pool_path, out = sys.argv[1], sys.argv[2]
    pool = json.load(open(pool_path))
    for d in ("a", "m", "mt"):
        os.makedirs(f"{out}/{d}", exist_ok=True)
    if "--pack" in sys.argv:
        pack(out, len(pool))
        sys.exit()
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    jobs = [(i, row[0], out) for i, row in enumerate(pool) if not os.path.exists(f"{out}/a/{i}.m4a")]
    print(f"{len(jobs)} to render with {workers} workers", flush=True)
    with Pool(workers) as p:
        for n, _ in enumerate(p.imap_unordered(render, jobs, chunksize=4), 1):
            if n % 200 == 0:
                print(f"{n}/{len(jobs)}", flush=True)
    pack(out, len(pool))
