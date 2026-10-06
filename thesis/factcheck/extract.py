# -*- coding: utf-8 -*-
"""Deterministic numeric-claim extraction from the report's LaTeX.

Walks main.tex following \\input, strips comments, and emits every numeric
token in prose, captions and table cells with its file:line and the
surrounding sentence. TikZ/pgfplots drawing code is skipped (figure text is
outside the word count and is checked separately by the fact registry),
as are \\label/\\ref arguments, tabular column specs and lengths.
Output: claims.json  [{token, value, file, line, context, kind}]
"""
import io, os, re, json, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 04-dissertation
INPUT = re.compile(r"\\input\{([^}]+)\}")
COMMENT = re.compile(r"(?<!\\)%.*")
# a numeric token: optional sign, digits with optional thousands {,} or , and decimal part, or .95 style
NUM = re.compile(r"(?<![A-Za-z0-9\\_])[+\-\u2212]?(?:\d{1,3}(?:\{,\}\d{3})+|\d+)(?:\.\d+)?(?![A-Za-z]*\d*[a-z]{2,})|(?<![\w.])\.\d+")
SYMBOLS = re.compile(r"\\(pm|sim|approx|le|ge|leq|geq|times|to|cdot|setminus|cup|ldots|dots)\b")
SKIP_ENVS = ("tikzpicture", "axis", "lstlisting")
SKIP_CMDS = ("label", "ref", "cite", "input", "includegraphics", "vspace", "hspace",
             "setlength", "addbibresource", "usepackage", "begin", "end", "S")


def expand(rel, seen=None):
    seen = seen if seen is not None else set()
    p = os.path.join(ROOT, rel if rel.endswith(".tex") else rel + ".tex")
    if not os.path.exists(p):
        return []
    out = []
    for ln, line in enumerate(io.open(p, encoding="utf-8").read().splitlines(), 1):
        line = COMMENT.sub("", line)
        m = INPUT.search(line)
        if m:
            t = m.group(1)
            if t not in seen:
                seen.add(t)
                out.extend(expand(t, seen))
            continue
        out.append((os.path.relpath(p, ROOT).replace("\\", "/"), ln, line))
    return out


def strip_skips(lines):
    """Drop lines inside skipped environments and remove skipped command args."""
    depth = 0
    kept = []
    for f, ln, line in lines:
        opened = re.findall(r"\\begin\{(\w+)\}", line)
        closed = re.findall(r"\\end\{(\w+)\}", line)
        if depth == 0 and not any(e in SKIP_ENVS for e in opened):
            s = line
            for c in SKIP_CMDS:
                s = re.sub(r"\\" + c + r"\*?(\[[^\]]*\])?\{[^{}]*\}", " ", s)
            s = re.sub(r"\\begin\{tabular\*?\}\{[^}]*\}", " ", s)
            s = re.sub(r"\[[tbhp!]+\]", " ", s)              # float placement
            s = re.sub(r"\d+(\.\d+)?(pt|cm|mm|em|ex|in)\b", " ", s)  # lengths
            s = s.replace("--", " to ")                        # en-dash ranges are not minus signs
            s = SYMBOLS.sub(" ", s)                            # \pm0.38 -> 0.38, \sim88 -> 88
            s = re.sub(r"\\(text|math)?(bf|it|rm|tt|sf)\{", " {", s)  # \textbf{97.6} -> {97.6}
            kept.append((f, ln, s))
        depth += sum(1 for e in opened if e in SKIP_ENVS)
        depth -= sum(1 for e in closed if e in SKIP_ENVS)
        depth = max(depth, 0)
    return kept


def sentences(kept):
    """Yield (file, line, sentence) by joining lines and splitting on sentence ends."""
    buf, start = [], None
    for f, ln, s in kept:
        if not s.strip():
            if buf:
                yield start, " ".join(buf)
                buf, start = [], None
            continue
        if start is None:
            start = (f, ln)
        buf.append(s.strip())
    if buf:
        yield start, " ".join(buf)


def norm_value(tok):
    t = tok.replace("{,}", "").replace(",", "").replace("\u2212", "-")
    try:
        return float(t)
    except ValueError:
        return None


def main(out="claims.json"):
    lines = expand("main.tex")
    kept = strip_skips(lines)
    claims = []
    for (f, ln), sent in sentences(kept):
        kind = "table" if "&" in sent and "\\\\" in sent else "prose"
        for m in NUM.finditer(sent):
            tok = m.group(0)
            v = norm_value(tok)
            if v is None:
                continue
            ctx = sent[max(0, m.start() - 90): m.end() + 60].replace("\n", " ")
            claims.append({"token": tok, "value": v, "file": f, "line": ln,
                           "kind": kind, "context": ctx})
    here = os.path.dirname(os.path.abspath(__file__))
    json.dump(claims, io.open(os.path.join(here, out), "w", encoding="utf-8"), indent=0)
    print("claims extracted:", len(claims))
    return claims


if __name__ == "__main__":
    main()
