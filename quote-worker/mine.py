"""Mine candidate quotes from Project Gutenberg texts for the chunklet-quotes Worker.

    python3 mine.py TEXTS_DIR candidates.json

TEXTS_DIR holds pg{id}.txt / {id}.txt files named in BOOKS below. Every passage is 1+ whole
sentences from ONE speech (Shakespeare) or ONE paragraph/stanza (everything else), so lines
never get glued across speakers or scenes. Output rows: [text, work, author, colorScore],
keeping the most vivid slice of each work for the taste audit (audit.py).
"""
import json, re, sys
from pathlib import Path

# id -> (author, work). Shakespeare (100) splits into plays by heading.
BOOKS = {
    "100": ("Shakespeare", None),
    # ancient
    "1727": ("Homer", "The Odyssey"), "2199": ("Homer", "The Iliad"),
    "sophocles_oedipus": ("Sophocles", "Oedipus Rex"), "sophocles_antigone": ("Sophocles", "Antigone"),
    "virgil": ("Virgil", "Eclogues"), "2680": ("Marcus Aurelius", "Meditations"),
    "216": ("Lao Tzu", "Tao Te Ching"),
    # medieval / renaissance / enlightenment
    "dante": ("Dante", "Inferno"), "chaucer": ("Chaucer", "Canterbury Tales"),
    "montaigne": ("Montaigne", "Essays"), "cervantes": ("Cervantes", "Don Quixote"),
    "milton": ("John Milton", "Paradise Lost"), "voltaire": ("Voltaire", "Candide"),
    "829": ("Jonathan Swift", "Gulliver's Travels"),
    # romantic
    "1934": ("William Blake", "Songs of Innocence and of Experience"),
    "151": ("Samuel Taylor Coleridge", "The Rime of the Ancient Mariner"),
    "23684": ("John Keats", "Poems"), "1279": ("Robert Burns", "Poems and Songs"),
    "84": ("Mary Shelley", "Frankenstein"),
    "10031": ("Edgar Allan Poe", "Poems"), "2148": ("Edgar Allan Poe", "Tales"),
    "2149": ("Edgar Allan Poe", "Tales"), "2150": ("Edgar Allan Poe", "Tales"),
    "whitman": ("Walt Whitman", "Leaves of Grass"), "dickinson": ("Emily Dickinson", "Poems"),
    "205": ("Henry David Thoreau", "Walden"), "2944": ("Ralph Waldo Emerson", "Essays"),
    # victorian / 19th c. novel
    "98": ("Charles Dickens", "A Tale of Two Cities"), "1400": ("Charles Dickens", "Great Expectations"),
    "46": ("Charles Dickens", "A Christmas Carol"), "766": ("Charles Dickens", "David Copperfield"),
    "1342": ("Jane Austen", "Pride and Prejudice"), "158": ("Jane Austen", "Emma"),
    "105": ("Jane Austen", "Persuasion"),
    "1260": ("Charlotte Brontë", "Jane Eyre"), "768": ("Emily Brontë", "Wuthering Heights"),
    "2701": ("Herman Melville", "Moby-Dick"), "11231": ("Herman Melville", "Bartleby, the Scrivener"),
    "76": ("Mark Twain", "Adventures of Huckleberry Finn"), "74": ("Mark Twain", "The Adventures of Tom Sawyer"),
    "102": ("Mark Twain", "Pudd'nhead Wilson"),
    "11": ("Lewis Carroll", "Alice's Adventures in Wonderland"), "12": ("Lewis Carroll", "Through the Looking-Glass"),
    "43": ("Robert Louis Stevenson", "Dr. Jekyll and Mr. Hyde"), "120": ("Robert Louis Stevenson", "Treasure Island"),
    "1661": ("Arthur Conan Doyle", "The Adventures of Sherlock Holmes"),
    "wilde": ("Oscar Wilde", "The Picture of Dorian Gray"), "844": ("Oscar Wilde", "The Importance of Being Earnest"),
    # russian
    "2554": ("Fyodor Dostoevsky", "Crime and Punishment"), "28054": ("Fyodor Dostoevsky", "The Brothers Karamazov"),
    "1399": ("Leo Tolstoy", "Anna Karenina"),
    # modern
    "kafka": ("Kafka", "The Metamorphosis"), "proust": ("Marcel Proust", "In Search of Lost Time"),
    "joyce": ("James Joyce", "Ulysses"), "2814": ("James Joyce", "Dubliners"),
    "1998": ("Friedrich Nietzsche", "Thus Spake Zarathustra"), "58585": ("Kahlil Gibran", "The Prophet"),
    "32233": ("W. B. Yeats", "The Wind Among the Reeds"), "38877": ("W. B. Yeats", "Poems"),
    "64317": ("F. Scott Fitzgerald", "The Great Gatsby"), "805": ("F. Scott Fitzgerald", "This Side of Paradise"),
    "5670": ("Virginia Woolf", "Jacob's Room"), "63107": ("Virginia Woolf", "Mrs Dalloway in Bond Street"),
    "67138": ("Ernest Hemingway", "The Sun Also Rises"),
}

PLAYS = {
    "THE SONNETS": "Sonnets", "ALL’S WELL THAT ENDS WELL": "All's Well That Ends Well",
    "THE TRAGEDY OF ANTONY AND CLEOPATRA": "Antony and Cleopatra", "AS YOU LIKE IT": "As You Like It",
    "THE COMEDY OF ERRORS": "The Comedy of Errors", "THE TRAGEDY OF CORIOLANUS": "Coriolanus",
    "CYMBELINE": "Cymbeline", "THE TRAGEDY OF HAMLET, PRINCE OF DENMARK": "Hamlet",
    "THE FIRST PART OF KING HENRY THE FOURTH": "Henry IV Part 1",
    "THE SECOND PART OF KING HENRY THE FOURTH": "Henry IV Part 2",
    "THE LIFE OF KING HENRY THE FIFTH": "Henry V", "THE FIRST PART OF HENRY THE SIXTH": "Henry VI Part 1",
    "THE SECOND PART OF KING HENRY THE SIXTH": "Henry VI Part 2",
    "THE THIRD PART OF KING HENRY THE SIXTH": "Henry VI Part 3", "KING HENRY THE EIGHTH": "Henry VIII",
    "THE LIFE AND DEATH OF KING JOHN": "King John", "THE TRAGEDY OF JULIUS CAESAR": "Julius Caesar",
    "THE TRAGEDY OF KING LEAR": "King Lear", "LOVE’S LABOUR’S LOST": "Love's Labour's Lost",
    "THE TRAGEDY OF MACBETH": "Macbeth", "MEASURE FOR MEASURE": "Measure for Measure",
    "THE MERCHANT OF VENICE": "The Merchant of Venice", "THE MERRY WIVES OF WINDSOR": "The Merry Wives of Windsor",
    "A MIDSUMMER NIGHT’S DREAM": "A Midsummer Night's Dream", "MUCH ADO ABOUT NOTHING": "Much Ado About Nothing",
    "THE TRAGEDY OF OTHELLO, THE MOOR OF VENICE": "Othello", "PERICLES, PRINCE OF TYRE": "Pericles",
    "KING RICHARD THE SECOND": "Richard II", "KING RICHARD THE THIRD": "Richard III",
    "THE TRAGEDY OF ROMEO AND JULIET": "Romeo and Juliet", "THE TAMING OF THE SHREW": "The Taming of the Shrew",
    "THE TEMPEST": "The Tempest", "THE LIFE OF TIMON OF ATHENS": "Timon of Athens",
    "THE TRAGEDY OF TITUS ANDRONICUS": "Titus Andronicus", "TROILUS AND CRESSIDA": "Troilus and Cressida",
    "TWELFTH NIGHT; OR, WHAT YOU WILL": "Twelfth Night", "THE TWO GENTLEMEN OF VERONA": "The Two Gentlemen of Verona",
    "THE TWO NOBLE KINSMEN": "The Two Noble Kinsmen", "THE WINTER’S TALE": "The Winter's Tale",
    "A LOVER’S COMPLAINT": "A Lover's Complaint", "THE PASSIONATE PILGRIM": "The Passionate Pilgrim",
    "THE PHOENIX AND THE TURTLE": "The Phoenix and the Turtle", "THE RAPE OF LUCRECE": "The Rape of Lucrece",
    "VENUS AND ADONIS": "Venus and Adonis",
}

MIN_W, MAX_W = 12, 40

COLOR = set("""light dark shadow moon sun star night dawn sea storm fire blood rose thorns stone sky wind
dream ghost heart hand eyes tongue mercy grief rage joy love hope fear bitter sweet wild tender gold
silence music dance snow rain bone hunger thirst honey salt""".split())

def color_score(s):
    low = s.lower(); sc = sum(2 for w in COLOR if w in low)
    if re.search(r"[,:;]", s): sc += 1
    if re.search(r"\b(never|always|nothing|everything)\b", s, re.I): sc += 1
    if re.search(r"\b(I|you|we|they|he|she)\b", s, re.I): sc += 0.5
    if len(s) < 40: sc -= 0.5
    return sc

BAD_END = re.compile(r"\b(with|of|to|from|for|and|or|but|if|when|where|that|which|who|than|as|at|by|in|on|a|an|the|my|your|his|her|its|our|their)[.?!]?$", re.I)
BAD_START = re.compile(r"^(and|or|nor|but|for|yet|so|with|of|to|from)\b", re.I)

def body(raw):
    raw = raw.replace("\r", "")
    m = re.search(r"\*\*\* ?START OF.*?\*\*\*", raw)
    if m: raw = raw[m.end():]
    m = re.search(r"\*\*\* ?END OF", raw)
    if m: raw = raw[:m.start()]
    return raw

def tidy(s):
    s = re.sub(r"\[[^\]]*\]|\{[^}]*\}", " ", s)          # [stage directions] / [footnotes]
    s = s.replace("_", "").replace("*", "")
    s = re.sub(r"\s*(--|—|–)\s*", ", ", s)               # no dashes, ever
    s = s.replace("‘", "'").replace("’", "'").replace("`", "'")
    s = s.replace("“", '"').replace("”", '"')
    s = re.sub(r"\s+", " ", s).strip()
    if s.count('"') % 2: s = s.replace('"', "")          # unbalanced quote marks: drop them all
    s = re.sub(r"^[\s,;:.'\"!?)]+", "", s)
    s = re.sub(r"\s+([,;:.!?])", r"\1", s)
    s = re.sub(r"([,;:])(?=[.!?])", "", s)
    s = re.sub(r",\s*,", ",", s).strip(" ,;:")
    s = re.sub(r"([!?]),", r"\1", s)
    if s and s[-1] not in ".?!\"'": s += "."
    return s

SENT = re.compile(r'(?<!\bMr\.)(?<!\bMrs\.)(?<!\bDr\.)(?<!\bSt\.)(?<!\bMs\.)(?<=[.?!])["\']?\s+(?=["\'(]?[A-Z])')

def windows(text, work, author, out):
    """Whole-sentence passages of MIN_W..MAX_W words from one speech/paragraph."""
    sents = [x.strip() for x in SENT.split(re.sub(r"\s+", " ", text)) if x.strip()]
    i = 0
    while i < len(sents):
        acc, j = [], i
        while j < len(sents) and len(" ".join(acc).split()) < MIN_W:
            acc.append(sents[j]); j += 1
        cand = tidy(" ".join(acc))
        n = len(cand.split())
        if MIN_W <= n <= MAX_W and not BAD_END.search(cand.rstrip("\"'")) and not BAD_START.search(cand) \
           and not re.search(r"\d|[A-Z]{4,}", cand) \
           and not re.search(r"https?:|gutenberg|chapter|footnote|\bibid\b|\bp\. |translat|\bedition\b", cand, re.I) \
           and cand[0].isupper():
            out.append([cand, work, author, color_score(cand)])
            i = j
        else:
            i += 1

def mine_shakespeare(raw, out):
    lines = body(raw).split("\n")
    # skip the table of contents: the real plays start at the 2nd "THE SONNETS"
    starts = [k for k, l in enumerate(lines) if l.strip() == "THE SONNETS"]
    work, speech = None, []
    def flush():
        if work and speech: windows(" ".join(speech), work, "Shakespeare", out)
        speech.clear()
    for l in lines[starts[1] if len(starts) > 1 else 0:]:
        t = l.strip()
        if t in PLAYS: flush(); work = PLAYS[t]; continue
        if not t:
            if work == "Sonnets" or work in ("Venus and Adonis", "The Rape of Lucrece"): flush()
            continue
        if re.match(r"^([A-Z][A-Z’' ,&]+)\.$", t) or re.match(r"^(ACT|SCENE|Scene|PROLOGUE|EPILOGUE|Dramatis|DRAMATIS)\b", t):
            flush(); continue                                        # speaker tag / scene heading
        if re.match(r"^\[?_?(Enter|Exit|Exeunt|Re-enter|Flourish|Alarum|Sennet|Trumpets|Music)", t):
            continue                                                 # stage direction
        if re.fullmatch(r"[ivxlcdmIVXLCDM\d.]+", t): flush(); continue  # sonnet numbers
        speech.append(t)
    flush()

def mine_book(raw, work, author, out):
    for para in re.split(r"\n\s*\n", body(raw)):
        p = para.strip()
        if not p or p.isupper() or re.match(r"^(CHAPTER|BOOK|PART|CANTO|STAVE|LETTER|VOLUME|ACT|SCENE)\b", p, re.I):
            continue
        windows(p.replace("\n", " "), work, author, out)

def main(src, dst):
    src = Path(src); out = []
    for key, (author, work) in BOOKS.items():
        f = next((p for p in (src / f"{key}.txt", src / f"pg{key}.txt") if p.exists()), None)
        if not f: print("missing", key, file=sys.stderr); continue
        raw = f.read_text(encoding="utf-8", errors="ignore")
        before = len(out)
        if key == "100": mine_shakespeare(raw, out)
        else: mine_book(raw, work, author, out)
        print(f"{author:24} {work or 'plays':36} {len(out)-before:6}", file=sys.stderr)
    # dedupe, then keep the most vivid slice of each work for the audit
    seen, groups = set(), {}
    for r in out:
        if r[0] in seen: continue
        seen.add(r[0]); groups.setdefault((r[2], r[1]), []).append(r)
    keep = []
    for rows in groups.values():
        rows.sort(key=lambda r: -r[3])
        keep += rows[:max(40, min(450, len(rows) // 3))]
    json.dump(keep, open(dst, "w"), ensure_ascii=False)
    print("candidates", len(keep), "of", len(seen), file=sys.stderr)

if __name__ == "__main__":
    main(*sys.argv[1:3])
