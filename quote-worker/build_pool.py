"""Join candidates + audit scores into pool.json (the lines the Worker serves).

    python3 build_pool.py candidates.json scores.jsonl pool.json
"""
import json, re, sys
from collections import Counter

cands, scores, dst = sys.argv[1:4]
rows = json.load(open(cands))
keep = {d["i"] for d in map(json.loads, open(scores)) if d["s"] == 2}
# Last scrub: unbalanced quote marks, and the Sophocles translation's inline speaker tags /
# stage directions ("Tiresias. ...", "Enter Tiresias led by...").
SPEAKER = re.compile(r"\b(Oedipus|Tiresias|Shepherd|Creon|Jocasta|Chorus|Messenger|Antigone|Ismene|Haemon|"
                     r"Guard|Eurydice|Priest|Attendant|Leader|Second Messenger)\. ")
pool = []
for i, r in enumerate(rows):
    if i not in keep: continue
    t = r[0]
    if re.search(r"\bEnter\b|\bExeunt\b|[\[\]]", t) or SPEAKER.search(t): continue
    if t.count('"') % 2: t = t.replace('"', "")
    pool.append([t, r[1], r[2]])
json.dump(pool, open(dst, "w"), ensure_ascii=False, separators=(",", ":"))
print(len(pool), "lines")
for a, n in Counter(r[2] for r in pool).most_common(): print(f"  {a:26} {n}")
