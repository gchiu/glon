#!/usr/bin/env python3
"""Build the Glon language documentation from the pinned upstream Markdown.

Inputs (read-only):
  <upstream>/docs/language/*.md
  <upstream>/docs/grammar/glon-grammar.ebnf
  <upstream>/docs/grammar/index.html
  <upstream>/docs/grammar/railroad/*.svg

Outputs:
  <out>/language/<slug>.html       rendered documentation
  <out>/language/index.html        language reference hub
  <out>/language/style.css         shared documentation styling
  <out>/grammar/index.html         imported upstream railroad/grammar page
  <out>/grammar/glon-grammar.ebnf  stable public EBNF URL
  <out>/grammar/railroad/*.svg     railroad diagrams
  <out>/source/<original>.md       stable public original Markdown URLs
  <out>/source/glon-grammar.ebnf   stable public EBNF copy

The upstream checkout must already be at the commit recorded in interpreter.json.
Markdown is rendered with Python-Markdown; Mermaid blocks are rendered in the
browser by the locally vendored docs/assets/mermaid.min.js.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

import markdown as md

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = ROOT / "interpreter.json"
DEFAULT_OUT = ROOT / "docs"
UPSTREAM_LANGUAGE = Path("docs/language")
UPSTREAM_GRAMMAR = Path("docs/grammar")


@dataclass(frozen=True)
class Document:
    slug: str
    upstream: str
    original: str
    title: str
    summary: str


DOCUMENTS = [
    Document("laws", "laws.md", "GLON-ALPHA-LAWS.md", "Alpha Language Laws",
             "The normative Alpha language contract."),
    Document("spec", "spec.md", "GLON-LANGUAGE-SPEC.md", "Language Specification",
             "Complete descriptive reference: values, evaluation, vocabulary, errors and limits."),
    Document("evaluation", "evaluation.md", "GLON-EVALUATION-MODEL.md", "Evaluation Model",
             "Execution, binding, calls, result sets, closures, return, judge and tasks."),
    Document("syntax-diagrams", "syntax-diagrams.md", "GLON-SYNTAX-DIAGRAMS.md", "Syntax Diagrams",
             "Verified reader grammar, word forms and reader boundary notes."),
    Document("host-abi", "host-abi.md", "GLON-HOST-ABI.md", "Host ABI",
             "Native C session boundary, WASM operations and portable-vs-host responsibilities."),
    Document("wasm-abi", "wasm-abi.md", "GLON-WASM-ABI.md", "WASM ABI",
             "The detailed original WebAssembly binary interface contract."),
    Document("verification", "verification.md", "GLON-SPEC-VERIFICATION.md", "Specification Verification",
             "EBNF/diagram/ABI provenance audit, agreements and unresolved cases."),
    Document("implementer-guide", "implementer-guide.md", "GLON-IMPLEMENTER-GUIDE.md", "Implementer Guide",
             "Minimum reading path for an independent Glon implementer."),
    Document("ai-authoring", "ai-authoring.md", "GLON-AI-AUTHORING.md", "AI Authoring Guide",
             "Concise reading order, traps and validation guidance for AI coding agents."),
    Document("primer", "primer.md", "GLON-PRIMER.md", "Glon Primer",
             "Instructional Glon in five minutes; subordinate to the laws."),
]

LINK_MAP = {d.original: d.slug + ".html" for d in DOCUMENTS}
LINK_MAP.update({Path(d.original).stem + ".md": d.slug + ".html" for d in DOCUMENTS})

MERMAID_SCRIPT = """
<script src="../assets/mermaid.min.js"></script>
<script>
(function () {
  function render() {
    var blocks = document.querySelectorAll('pre > code.language-mermaid');
    if (!blocks.length || !window.mermaid) return;
    blocks.forEach(function (code) {
      var div = document.createElement('div');
      div.className = 'mermaid';
      div.textContent = code.textContent;
      code.parentElement.replaceWith(div);
    });
    var dark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    window.mermaid.initialize({ startOnLoad: false, securityLevel: 'strict', theme: dark ? 'dark' : 'default' });
    window.mermaid.run({ querySelector: '.mermaid' }).catch(function (err) {
      console.error('Mermaid render failed', err);
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', render);
  else render();
})();
</script>
"""

DOC_CSS = """
:root { --fg:#171a1f; --muted:#5d6573; --bg:#fdfdfc; --panel:#f3f5f7; --line:#d9dee4;
        --accent:#2456a6; --code:#20262e; --ok:#1b6b42; }
@media (prefers-color-scheme: dark) {
  :root { --fg:#e7e9ed; --muted:#a0a8b4; --bg:#15171b; --panel:#1e2229; --line:#343b46;
          --accent:#8db1f2; --code:#242a32; --ok:#7ad6a2; }
}
* { box-sizing:border-box; }
html { scroll-behavior:smooth; }
body { margin:0 auto; max-width:1040px; padding:0 16px 4rem; color:var(--fg); background:var(--bg);
       font:16px/1.65 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; overflow-wrap:anywhere; }
a { color:var(--accent); }
h1,h2,h3,h4 { line-height:1.2; letter-spacing:-.01em; }
h1 { font-size:clamp(2rem,5vw,3rem); margin:0 0 .4rem; }
h2 { font-size:clamp(1.25rem,3vw,1.55rem); margin:2.2rem 0 .6rem; }
h3 { font-size:1.1rem; margin:1.6rem 0 .4rem; }
p { margin:.55rem 0; }
code,pre { font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-size:.9rem; }
code { background:var(--code); color:#eef2f6; padding:.05rem .25rem; border-radius:3px; overflow-wrap:anywhere; }
pre { background:var(--code); color:#eef2f6; border-radius:8px; padding:.8rem 1rem; overflow:auto; line-height:1.45; }
pre code { background:none; padding:0; color:inherit; overflow-wrap:normal; }
.muted { color:var(--muted); }
.topnav { display:flex; flex-wrap:wrap; gap:.6rem 1rem; align-items:center; justify-content:space-between;
          padding:.75rem 0; border-bottom:1px solid var(--line); margin-bottom:1.4rem; }
.brand { font-weight:800; color:var(--fg); text-decoration:none; }
.navlinks { display:flex; flex-wrap:wrap; gap:.45rem 1rem; font-size:.9rem; }
.navlinks a { color:var(--muted); text-decoration:none; }
.navlinks a:hover, .navlinks a:focus-visible { color:var(--accent); text-decoration:underline; }
.pagelead { display:flex; flex-wrap:wrap; gap:.5rem 1rem; align-items:center; margin:0 0 1rem;
            font-size:.86rem; color:var(--muted); }
.pagelead a { font-weight:600; }
table { border-collapse:collapse; width:100%; margin:.8rem 0 1.2rem; font-size:.92rem; table-layout:fixed; }
th,td { border:1px solid var(--line); padding:.45rem .55rem; text-align:left; vertical-align:top; overflow-wrap:anywhere; }
th { background:var(--panel); }
blockquote { border-left:3px solid var(--line); margin:1rem 0; padding:.5rem 1rem; color:var(--muted); background:var(--panel); }
ul,ol { padding-left:1.4rem; }
li { margin:.2rem 0; }
.mermaid { overflow-x:auto; text-align:center; margin:1.2rem 0; }
.mermaid svg { max-width:100%; height:auto; }
.cards { display:grid; grid-template-columns:repeat(auto-fit,minmax(250px,1fr)); gap:.9rem; margin:1rem 0; }
.card { border:1px solid var(--line); border-radius:9px; background:var(--panel); padding:1rem; }
.card h3 { margin:.1rem 0 .35rem; }
.card p:last-child { margin-bottom:0; }
.source-list { font-size:.9rem; }
footer { margin-top:3rem; padding-top:1rem; border-top:1px solid var(--line); color:var(--muted); font-size:.85rem; }
@media (max-width:560px) {
  body { padding:0 14px 3rem; }
  .topnav { align-items:flex-start; }
  pre { white-space:pre-wrap; overflow-wrap:anywhere; }
}
"""


def die(msg: str) -> None:
    print(f"build-docs: {msg}", file=sys.stderr)
    raise SystemExit(1)


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        die(f"cannot read {path}: {exc}")


def upstream_head(upstream: Path) -> str:
    try:
        out = subprocess.check_output(
            ["git", "-C", str(upstream), "rev-parse", "HEAD"], text=True, stderr=subprocess.STDOUT
        )
        return out.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        die(f"cannot read upstream git HEAD: {exc}")


def rewrite_links(text: str) -> str:
    def repl(match: re.Match) -> str:
        target = match.group(1)
        if re.match(r"^[a-zA-Z]+:", target) or target.startswith("#") or target.startswith("/"):
            return match.group(0)
        path, sep, fragment = target.partition("#")
        name = Path(path).name
        replacement = LINK_MAP.get(name)
        if replacement:
            return "](" + replacement + (("#" + fragment) if sep else "") + ")"
        return match.group(0)

    return re.sub(r"\]\(([^)]+)\)", repl, text)


def render_markdown(text: str) -> str:
    text = rewrite_links(text)
    instance = md.Markdown(extensions=["extra", "toc", "sane_lists"], output_format="html5")
    return instance.convert(text)


def page_shell(title: str, body: str, *, root_href: str = "../", source_href: str = "", commit: str = "", language_href: str = "index.html") -> str:
    source = (
        f'<a href="{html.escape(source_href)}">View Markdown source</a>'
        if source_href else ""
    )
    lead = f'<div class="pagelead">{source} <span>Upstream commit <code>{html.escape(commit)}</code></span></div>' if source else ""
    mermaid = MERMAID_SCRIPT if "language-mermaid" in body else ""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>{DOC_CSS}</style>
</head>
<body>
<nav class="topnav" aria-label="Site navigation">
  <a class="brand" href="{html.escape(root_href)}">Glon</a>
  <div class="navlinks">
    <a href="{html.escape(root_href)}">Home</a>
    <a href="{html.escape(language_href)}">Language</a>
    <a href="../grammar/">Grammar</a>
    <a href="{html.escape(root_href)}#challenges">Challenges</a>
  </div>
</nav>
<main>
{lead}
{body}
</main>
<footer>Generated from the pinned upstream Markdown at <code>{html.escape(commit)}</code>. The original Markdown is preserved under <a href="{html.escape(root_href)}source/">source/</a>.</footer>
{mermaid}
</body>
</html>
"""


def build_language_index(out: Path, commit: str) -> str:
    cards = []
    for d in DOCUMENTS:
        cards.append(
            f'<div class="card"><h3><a href="{d.slug}.html">{html.escape(d.title)}</a></h3>'
            f'<p>{html.escape(d.summary)}</p>'
            f'<p class="source-list"><a href="{d.slug}.html">Read rendered HTML</a> · '
            f'<a href="../source/{html.escape(d.original)}">Markdown source</a></p></div>'
        )
    body = f"""
<header>
  <h1>Glon Language Reference</h1>
  <p class="muted">Canonical public documentation for the Glon Alpha language, generated from the pinned engineering Markdown. Development and source specifications remain authoritative in <a href="https://github.com/gchiu/rebol-substrate-experiment">gchiu/rebol-substrate-experiment</a>.</p>
  <p class="muted">Upstream commit: <code>{html.escape(commit)}</code></p>
</header>
<section>
  <h2>Documents</h2>
  <div class="cards">{''.join(cards)}</div>
</section>
<section>
  <h2>Grammar and railroad diagrams</h2>
  <p>The verified reader grammar, all productions and generated railroad diagrams are in the
     <a href="../grammar/">grammar reference</a>. The machine-readable EBNF is available at
     <a href="../source/glon-grammar.ebnf">source/glon-grammar.ebnf</a>.</p>
</section>
<section>
  <h2>Raw sources for AI agents</h2>
  <p>Every document is also preserved with its original Markdown filename under
     <a href="../source/">source/</a>. Use these stable URLs instead of scraping rendered HTML.</p>
</section>
"""
    return page_shell("Glon Language Reference", body, source_href="", commit=commit)


def patch_grammar_page(text: str) -> str:
    for d in DOCUMENTS:
        text = text.replace(f"../language/{Path(d.upstream).name}", f"../language/{d.slug}.html")
        text = text.replace(f"../language/{d.original}", f"../language/{d.slug}.html")
    css = """
.site-nav{display:flex;flex-wrap:wrap;gap:.5rem 1rem;align-items:center;padding:.75rem 0;border-bottom:1px solid #d7dde3;margin-bottom:1.2rem;font-size:.9rem}
.site-nav a{color:#2456a6;text-decoration:none}.site-nav a:hover{text-decoration:underline}.site-nav .brand{font-weight:800;color:#17202a}
"""
    text = text.replace("</style>", css + "</style>", 1)
    nav = '''<nav class="site-nav" aria-label="Site navigation">
  <a class="brand" href="../">Glon</a>
  <a href="../">Home</a>
  <a href="../language/">Language</a>
  <a href="../grammar/">Grammar</a>
  <a href="../#challenges">Challenges</a>
</nav>
'''
    text = text.replace("<body>\n", "<body>\n" + nav, 1)
    # Make the EBNF source link explicit in the breadcrumb/header.
    text = text.replace(
        '<a href="../language/">Language Reference</a> / Grammar',
        '<a href="../language/">Language Reference</a> / Grammar · <a href="../source/glon-grammar.ebnf">View EBNF source</a>',
        1,
    )
    text = text.replace(
        'The canonical grammar file is <a href="glon-grammar.ebnf">glon-grammar.ebnf</a>. Run <code>python3 generate.py</code> to regenerate this page and the SVG files; run <code>python3 verify.py</code> to verify them.',
        'The canonical grammar file is <a href="glon-grammar.ebnf">glon-grammar.ebnf</a>; the preserved upstream copy is <a href="../source/glon-grammar.ebnf">source/glon-grammar.ebnf</a>. The upstream engineering repository generates the page and SVG files with its own <code>docs/grammar/generate.py</code> and verifies them with <code>docs/grammar/verify.py</code>.',
    )
    return text


def check_links(out: Path) -> int:
    problems = []
    checked = 0
    for page in sorted((out / "language").glob("*.html")) + [out / "grammar" / "index.html"]:
        text = page.read_text(encoding="utf-8")
        ids = set(re.findall(r'\bid="([^"]+)"', text))
        for href in re.findall(r'(?:href|src)="([^"]+)"', text):
            if not href or href.startswith(("#", "http://", "https://", "mailto:", "//")):
                if href.startswith("#") and href[1:] and href[1:] not in ids:
                    problems.append(f"{page.relative_to(out)}: missing anchor {href}")
                continue
            clean = href.split("#", 1)[0]
            if not clean:
                continue
            target = (page.parent / clean).resolve()
            if clean.endswith("/"):
                target = target / "index.html"
            checked += 1
            if not target.is_file():
                problems.append(f"{page.relative_to(out)}: broken link {href}")
    if problems:
        for p in problems:
            print(f"build-docs: {p}", file=sys.stderr)
        die(f"{len(problems)} broken internal link(s)")
    return checked


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream", type=Path, required=True, help="engineering checkout at the pinned commit")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()

    config = load_json(args.config)
    commit = config.get("commit")
    if not commit:
        die("interpreter.json has no commit")
    head = upstream_head(args.upstream)
    if head != commit:
        die(f"upstream HEAD {head} does not equal pinned commit {commit}")

    lang_src = args.upstream / UPSTREAM_LANGUAGE
    grammar_src = args.upstream / UPSTREAM_GRAMMAR
    for d in DOCUMENTS:
        p = lang_src / d.upstream
        if not p.is_file():
            die(f"missing upstream document: {p}")
    for p in (grammar_src / "glon-grammar.ebnf", grammar_src / "index.html"):
        if not p.is_file():
            die(f"missing upstream grammar file: {p}")

    out = args.out
    for directory in (out / "language", out / "grammar", out / "source"):
        if directory.exists():
            shutil.rmtree(directory)
        directory.mkdir(parents=True, exist_ok=True)
    asset_src = ROOT / "docs" / "assets"
    asset_dst = out / "assets"
    asset_dst.mkdir(parents=True, exist_ok=True)
    if asset_src.resolve() != asset_dst.resolve():
        shutil.copytree(asset_src, asset_dst, dirs_exist_ok=True)
    if not (asset_dst / "mermaid.min.js").is_file():
        die("missing docs/assets/mermaid.min.js (vendored Mermaid runtime)")

    (out / "language" / "style.css").write_text(DOC_CSS.strip() + "\n", encoding="utf-8")
    (out / "source").mkdir(exist_ok=True)

    for d in DOCUMENTS:
        source_text = (lang_src / d.upstream).read_text(encoding="utf-8")
        (out / "source" / d.original).write_text(source_text, encoding="utf-8")
        body = render_markdown(source_text)
        page = page_shell(d.title, body, source_href=f"../source/{d.original}", commit=commit)
        (out / "language" / f"{d.slug}.html").write_text(page, encoding="utf-8")

    (out / "language" / "index.html").write_text(build_language_index(out, commit), encoding="utf-8")

    source_items = "\n".join(
        f'<li><a href="{html.escape(d.original)}">{html.escape(d.original)}</a> — '
        f'{html.escape(d.title)} (<a href="../language/{d.slug}.html">rendered HTML</a>)</li>'
        for d in DOCUMENTS
    )
    source_body = f"""
<header><h1>Glon Source Documents</h1>
<p class="muted">Original Markdown preserved verbatim from upstream commit <code>{html.escape(commit)}</code>.</p></header>
<section><h2>Markdown</h2><ul>{source_items}</ul></section>
<section><h2>Grammar</h2><ul><li><a href="glon-grammar.ebnf">glon-grammar.ebnf</a> — machine-readable reader grammar</li></ul></section>
"""
    (out / "source" / "index.html").write_text(
        page_shell("Glon Source Documents", source_body, root_href="../", commit=commit, language_href="../language/"),
        encoding="utf-8",
    )

    shutil.copyfile(grammar_src / "glon-grammar.ebnf", out / "grammar" / "glon-grammar.ebnf")
    shutil.copyfile(grammar_src / "glon-grammar.ebnf", out / "source" / "glon-grammar.ebnf")
    shutil.copytree(grammar_src / "railroad", out / "grammar" / "railroad", dirs_exist_ok=True)
    grammar_html = (grammar_src / "index.html").read_text(encoding="utf-8")
    (out / "grammar" / "index.html").write_text(patch_grammar_page(grammar_html), encoding="utf-8")

    checked = check_links(out)
    print(f"build-docs: wrote {len(DOCUMENTS)} rendered documents from {commit}; checked {checked} internal links")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
