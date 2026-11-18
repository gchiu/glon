#!/usr/bin/env python3
"""Build the static Glon challenge results site from verified result JSON.

Refuses to write a published site when --require-pass is set and any result is
not fully passing. The output is plain HTML/CSS with no network dependency.
"""
from __future__ import annotations

import argparse
import html
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = ROOT / "interpreter.json"
DEFAULT_CHALLENGES = ROOT / "challenges"
DEFAULT_RESULTS = ROOT / "results"
DEFAULT_OUT = ROOT / "docs"

CSS = """
:root {
  --fg:#171a1f; --muted:#5d6573; --bg:#fdfdfc; --panel:#f3f5f7; --line:#d9dee4;
  --accent:#2456a6; --ok:#1b6b42; --bad:#8b2f22; --warn:#8a4b12; --code:#20262e;
}
@media (prefers-color-scheme: dark) {
  :root { --fg:#e7e9ed; --muted:#a0a8b4; --bg:#15171b; --panel:#1e2229; --line:#343b46;
          --accent:#8db1f2; --ok:#7ad6a2; --bad:#ff9b8d; --warn:#ffbd7a; --code:#242a32; }
}
* { box-sizing:border-box; }
html { scroll-behavior:smooth; }
body { margin:0 auto; max-width:980px; padding:1.6rem 16px 4rem; background:var(--bg); color:var(--fg);
       font:16px/1.6 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; overflow-wrap:anywhere; }
a { color:var(--accent); }
h1,h2,h3 { line-height:1.2; letter-spacing:-.01em; }
h1 { font-size:clamp(2rem,5vw,3rem); margin:0 0 .35rem; }
h2 { font-size:clamp(1.2rem,3vw,1.5rem); margin:2.3rem 0 .6rem; }
h3 { font-size:1.05rem; margin:0 0 .3rem; }
p { margin:.5rem 0; }
code,pre { font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-size:.9rem; }
code { background:var(--code); color:#eef2f6; padding:.05rem .25rem; border-radius:3px; overflow-wrap:anywhere; }
pre { background:var(--code); color:#eef2f6; border-radius:8px; padding:.8rem 1rem; overflow:auto; line-height:1.45; }
.muted { color:var(--muted); }
.topnav { display:flex; flex-wrap:wrap; gap:.6rem 1rem; align-items:center; justify-content:space-between;
          padding:.7rem 0; border-bottom:1px solid var(--line); margin-bottom:1.5rem; }
.brand { font-weight:800; color:var(--fg); text-decoration:none; }
.navlinks { display:flex; flex-wrap:wrap; gap:.45rem 1rem; font-size:.9rem; }
.navlinks a { color:var(--muted); text-decoration:none; }
.navlinks a:hover { color:var(--accent); text-decoration:underline; }
.code-compare { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:1rem; margin:1rem 0; }
.code-pane { border:1px solid var(--line); border-radius:9px; background:var(--panel); padding:1rem; min-width:0; }
.code-pane h3 { margin:0 0 .25rem; }
.pane-meta { color:var(--muted); font-size:.85rem; margin:.25rem 0 .55rem; }
.pane-meta a { font-weight:600; }
.compare-table { margin-top:.8rem; }
.notice { color:var(--muted); font-size:.9rem; margin:.6rem 0 1rem; }
@media (max-width:760px) { .code-compare { grid-template-columns:1fr; } }
.cards { display:grid; grid-template-columns:repeat(auto-fit,minmax(240px,1fr)); gap:.85rem; margin:.8rem 0; }
.card { border:1px solid var(--line); border-radius:9px; background:var(--panel); padding:1rem; }
.card p:last-child { margin-bottom:0; }
.status { display:inline-block; font-size:.72rem; font-weight:700; letter-spacing:.04em;
          border-radius:999px; padding:.12rem .55rem; border:1px solid var(--line); }
.status.pass { color:var(--ok); background:color-mix(in srgb,var(--ok) 10%,transparent); }
.status.fail { color:var(--bad); background:color-mix(in srgb,var(--bad) 10%,transparent); }
.status.partial { color:var(--warn); background:color-mix(in srgb,var(--warn) 12%,transparent); }
.callout { border:1px solid var(--line); border-left:4px solid var(--warn); border-radius:8px;
           background:color-mix(in srgb,var(--warn) 7%,var(--panel)); padding:.8rem 1rem; margin:1rem 0; }
.meta { display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:.6rem 1.2rem;
        margin:.7rem 0; padding:.8rem 1rem; border:1px solid var(--line); border-radius:8px; background:var(--panel); }
.meta div { min-width:0; }
.meta strong { display:block; font-size:.78rem; text-transform:uppercase; letter-spacing:.05em; color:var(--muted); }
table { border-collapse:collapse; width:100%; margin:.7rem 0 1rem; font-size:.9rem; table-layout:fixed; }
th,td { border:1px solid var(--line); padding:.45rem .5rem; text-align:left; vertical-align:top; overflow-wrap:anywhere; }
th { background:var(--panel); }
td pre { margin:0; padding:.35rem .45rem; font-size:.82rem; }
tr.pass td:last-child { color:var(--ok); font-weight:600; }
tr.fail td:last-child { color:var(--bad); font-weight:600; }
ul { padding-left:1.2rem; }
li { margin:.25rem 0; }
footer { margin-top:3rem; padding-top:1rem; border-top:1px solid var(--line); font-size:.85rem; color:var(--muted); }
@media (max-width:560px) { body { padding:1rem 14px 3rem; } .topnav { align-items:flex-start; } pre { white-space:pre-wrap; overflow-wrap:anywhere; } }
"""


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"build-site: cannot read {path}: {exc}")


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def code(value) -> str:
    return "<pre><code>" + esc(value) + "</code></pre>"


def status_badge(passed: bool, implementation_status: str = "verified") -> str:
    if implementation_status == "partial":
        return '<span class="status partial">PARTIAL</span>'
    return '<span class="status pass">VERIFIED</span>' if passed else '<span class="status fail">FAILED</span>'


def load_results(results_dir: Path) -> list[dict]:
    results = []
    for path in sorted(results_dir.glob("*.json")):
        data = load_json(path)
        if isinstance(data, dict) and data.get("challenge"):
            results.append(data)
    return results


def doc_links(config: dict) -> str:
    docs = config.get("documentation", {})
    items = [
        ("Language reference", docs.get("language_reference")),
        ("Grammar and railroad diagrams", docs.get("grammar")),
        ("Alpha language laws", docs.get("laws")),
        ("Language specification", docs.get("specification")),
        ("Evaluation model", docs.get("evaluation")),
        ("Host ABI", docs.get("host_abi")),
        ("AI authoring guide", docs.get("ai_authoring")),
    ]
    return "\n".join(
        f'<li><a href="{esc(url)}">{esc(label)}</a></li>' for label, url in items if url
    )


def clean_html(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.splitlines()) + "\n"


def page_shell(title: str, body: str, home_href: str = "index.html") -> str:
    link_prefix = home_href.rsplit("/", 1)[0] + "/" if "/" in home_href else ""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<style>{CSS}</style>
</head>
<body>
<nav class="topnav" aria-label="Primary navigation">
  <a class="brand" href="{esc(home_href)}">Glon</a>
  <div class="navlinks">
    <a href="{esc(home_href)}#challenges">Challenges</a>
    <a href="{esc(link_prefix)}language/">Language</a>
    <a href="{esc(link_prefix)}grammar/">Grammar</a>
    <a href="{esc(home_href)}#verification">Verification</a>
  </div>
</nav>
{body}
</body>
</html>
"""


def source_stats(text: str) -> str:
    return f"{len(text.rstrip(chr(10)).splitlines())} lines / {len(text.encode('utf-8'))} bytes"


def implementation_section(result: dict, source_text: str, challenge_dir: Path) -> tuple[str, str]:
    reference = result.get("reference_implementation")
    comparison = result.get("implementation_comparison") or {}
    glon_label = "Glon implementation"
    if result.get("implementation_status") == "partial":
        glon_label += " (partial)"
    glon_pane = (
        '<div class="code-pane">'
        f'<h3>{esc(glon_label)}</h3>'
        f'<p class="pane-meta"><a href="source.glon">Download Glon source</a> · {esc(source_stats(source_text))}</p>'
        f'{code(source_text)}</div>'
    )
    if not reference:
        return '<h2 id="source">Glon source</h2>' + glon_pane, ""

    ref_path = challenge_dir / str(reference.get("source", ""))
    ref_text = ref_path.read_text(encoding="utf-8") if ref_path.is_file() else ""
    lang = reference.get("language", "Reference")
    title = reference.get("title", "Original reference implementation")
    attribution = reference.get("attribution", "")
    url = reference.get("url", "")
    ref_meta = " · ".join(x for x in (attribution, source_stats(ref_text)) if x)
    ref_link = f' · <a href="{esc(url)}" target="_blank" rel="noopener">Archived Cookbook recipe</a>' if url else ""
    ref_pane = (
        '<div class="code-pane">'
        f'<h3>{esc(lang)} — original</h3>'
        f'<p class="pane-meta">{esc(title)}<br>{esc(ref_meta)}{ref_link}</p>'
        f'{code(ref_text)}</div>'
    )
    panes = f'<div class="code-compare">{ref_pane}{glon_pane}</div>'

    rows = []
    rebol = comparison.get("rebol", {})
    glon = comparison.get("glon", {})
    for label, rkey in [
        ("Observable behaviour", "observable_behaviour"),
        ("Required facilities", "facilities"),
        ("Test status", "test_status"),
    ]:
        rows.append(
            f'<tr><td>{esc(label)}</td><td>{esc(rebol.get(rkey, ""))}</td><td>{esc(glon.get(rkey, ""))}</td></tr>'
        )
    rows.append(
        f'<tr><td>Source size</td><td>{esc(source_stats(ref_text))}</td><td>{esc(source_stats(source_text))}</td></tr>'
    )
    notice = comparison.get("notice", "")
    compare_table = (
        '<h3>Implementation comparison</h3>'
        f'<table class="compare-table"><thead><tr><th>Aspect</th><th>{esc(lang)}</th><th>Glon</th></tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table>'
        + (f'<p class="notice">{esc(notice)}</p>' if notice else '')
    )
    return '<h2 id="source">Source listings</h2>' + panes, compare_table


def challenge_body(result: dict, source_text: str, config: dict, challenge_dir: Path) -> str:
    passed = bool(result.get("all_passed"))
    implementation_status = result.get("implementation_status", "verified")
    blocker = result.get("blocker", "")
    host_dependency = result.get("host_dependency", "")
    libraries = result.get("libraries", []) or []
    summary = result.get("summary", {})
    cases = result.get("cases", [])
    interpreter = result.get("interpreter", {})
    rows = []
    for case in cases:
        status = case.get("status", "unknown")
        cls = "pass" if status == "pass" else "fail"
        rows.append(
            "<tr class='%s'>"
            "<td><code>%s</code></td>"
            "<td><pre><code>%s</code></pre></td>"
            "<td><pre><code>%s</code></pre></td>"
            "<td><pre><code>%s</code></pre></td>"
            "<td>%s</td></tr>"
            % (
                cls,
                esc(case.get("id", "")),
                esc(repr(case.get("expected_stdout", ""))[1:-1]),
                esc(repr(case.get("actual_stdout", ""))[1:-1]),
                esc(str(case.get("actual_exit"))),
                esc(status),
            )
        )
    if not rows:
        rows.append("<tr class='fail'><td colspan='5'>No executable cases were recorded.</td></tr>")

    probe_rows = []
    for probe in result.get("resource_probes", []):
        actual = (probe.get("actual_stdout") or "").strip()
        stderr = (probe.get("actual_stderr") or "").strip().splitlines()
        detail = actual if actual else (stderr[-1] if stderr else "")
        probe_rows.append(
            "<tr><td><code>%s</code></td><td>%s</td><td>%s</td><td>%s</td></tr>"
            % (esc(probe.get("id", "")), esc(probe.get("call", "")),
               esc(str(probe.get("actual_exit"))), esc(detail))
        )

    limitations = "\n".join(f"<li>{esc(x)}</li>" for x in result.get("known_limitations", []))
    attribution = esc(result.get("attribution", ""))
    implementation_html, comparison_html = implementation_section(result, source_text, challenge_dir)
    return f"""
<main>
  <p class="muted"><a href="../../index.html">Challenge index</a> / {esc(result.get('challenge', ''))}</p>
  <h1>{esc(result.get('title', result.get('challenge', '')))}</h1>
  <p>{status_badge(passed, implementation_status)} <span class="muted">Execution results verified with the pinned interpreter; status reflects the implemented scope.</span></p>
  <p>{esc(result.get('description', ''))}</p>
  <p><strong>Attribution.</strong> {attribution}</p>
  {('<div class="callout"><strong>Complete operation blocked.</strong> ' + esc(blocker) + '</div>') if blocker else ''}
  {('<p class="muted"><strong>Host dependency:</strong> ' + esc(host_dependency) + '</p>') if host_dependency else ''}
  {('<p class="muted"><strong>Libraries loaded:</strong> ' + ', '.join('<code>' + esc(x) + '</code>' for x in libraries) + '</p>') if libraries else ''}
  <div class="meta">
    <div><strong>Interpreter commit</strong><code>{esc(interpreter.get('commit', 'unknown'))}</code></div>
    <div><strong>Verification date</strong>{esc(result.get('generated_at', 'unknown'))}</div>
    <div><strong>Cases</strong>{summary.get('passed', 0)} / {summary.get('total', 0)} passed</div>
    <div><strong>Domain</strong>{esc(result.get('domain', ''))}</div>
  </div>
  <p class="muted"><strong>Reference:</strong> {esc(result.get('reference', ''))}</p>

  {implementation_html}
  {comparison_html}

  <h2 id="results">Expected and actual results</h2>
  <table>
    <thead><tr><th>Case</th><th>Expected stdout</th><th>Actual stdout</th><th>Exit</th><th>Status</th></tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table>

  <h2 id="limits">Known limitations</h2>
  <ul>{limitations or '<li>None recorded.</li>'}</ul>

  {('<h2 id="probes">Resource probes</h2><table><thead><tr><th>Probe</th><th>Call</th><th>Exit</th><th>Observed stdout / diagnostic</th></tr></thead><tbody>' + ''.join(probe_rows) + '</tbody></table>') if probe_rows else ''}

  <h2 id="docs">Language documentation</h2>
  <ul>{doc_links(config)}</ul>
  <p><a href="source.glon">Download challenge source</a> · <a href="results.json">Result JSON</a></p>
</main>
<footer>Results are generated from actual runs of the pinned native Glon interpreter. No result is fabricated or manually marked as passing.</footer>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--challenges", type=Path, default=DEFAULT_CHALLENGES)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--require-pass", action="store_true",
                        help="refuse to write output unless every result is fully passing")
    args = parser.parse_args()

    config = load_json(args.config)
    if not args.results.is_dir():
        print(f"build-site: missing results directory: {args.results}", file=sys.stderr)
        return 1
    results = load_results(args.results)
    if not results:
        print(f"build-site: no result JSON files in {args.results}", file=sys.stderr)
        return 1
    failures = [r for r in results if not r.get("all_passed")]
    if args.require_pass and failures:
        print("build-site: refusing to build a published site from failing results:", file=sys.stderr)
        for r in failures:
            print(f"  {r.get('challenge')}: {r.get('summary')}", file=sys.stderr)
        return 1

    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    (out / "challenges").mkdir(exist_ok=True)
    (out / "style.css").write_text(CSS.strip() + "\n", encoding="utf-8")
    (out / ".nojekyll").write_text("", encoding="utf-8")

    cards = []
    for r in results:
        name = r.get("challenge", "unknown")
        cards.append(
            '<div class="card">'
            f'<h3><a href="challenges/{esc(name)}/index.html">{esc(r.get("title", name))}</a></h3>'
            f'<p>{status_badge(bool(r.get("all_passed")), r.get("implementation_status", "verified"))}</p>'
            f'<p>{esc(r.get("description", ""))}</p>'
            f'<p class="muted">Interpreter: <code>{esc(r.get("interpreter", {}).get("commit", "unknown"))}</code>'
            f'<br>Cases: {r.get("summary", {}).get("passed", 0)} / {r.get("summary", {}).get("total", 0)} passed</p>'
            '</div>'
        )
    total = sum(r.get("summary", {}).get("total", 0) for r in results)
    passed = sum(r.get("summary", {}).get("passed", 0) for r in results)
    index_body = f"""
<header>
  <h1>Glon</h1>
  <p class="muted">Canonical public language documentation and verified REBOL Cookbook / Rosetta Code style programming challenges, built from the published Glon grammar and upstream sources.</p>
  <div class="meta">
    <div><strong>Challenges</strong>{len(results)}</div>
    <div><strong>Cases passed</strong>{passed} / {total}</div>
    <div><strong>Interpreter commit</strong><code>{esc(config.get('commit', 'unknown'))}</code></div>
    <div><strong>Status</strong>{status_badge(not failures, "partial" if any(r.get("implementation_status") == "partial" for r in results) else "verified")}</div>
  </div>
</header>
<main>
  <h2 id="documentation">Language documentation</h2>
  <p>Canonical public documentation for Glon, generated from the pinned upstream Markdown and EBNF. Development and authoritative source specifications remain in <a href="https://github.com/gchiu/rebol-substrate-experiment">gchiu/rebol-substrate-experiment</a>.</p>
  <div class="cards">
    <div class="card"><h3><a href="language/">Language Reference</a></h3><p>Start here: laws, specification, evaluation, host ABI and AI authoring guide.</p></div>
    <div class="card"><h3><a href="grammar/">Grammar &amp; Railroad Diagrams</a></h3><p>All 20 grammar productions, EBNF and generated railroad diagrams.</p></div>
    <div class="card"><h3><a href="language/laws.html">Alpha Language Laws</a></h3><p>The normative Alpha language contract.</p></div>
    <div class="card"><h3><a href="language/spec.html">Language Specification</a></h3><p>Complete descriptive reference and traceability matrix.</p></div>
    <div class="card"><h3><a href="language/evaluation.html">Evaluation Model</a></h3><p>Execution, binding, calls, result sets, closures, return and judge.</p></div>
    <div class="card"><h3><a href="language/host-abi.html">Host ABI</a></h3><p>Native C, WASM and host capability boundary.</p></div>
  </div>
  <p class="muted">Raw sources for AI agents: <a href="source/GLON-LANGUAGE-SPEC.md">GLON-LANGUAGE-SPEC.md</a>,
     <a href="source/GLON-ALPHA-LAWS.md">GLON-ALPHA-LAWS.md</a>,
     <a href="source/GLON-EVALUATION-MODEL.md">GLON-EVALUATION-MODEL.md</a>,
     <a href="source/GLON-HOST-ABI.md">GLON-HOST-ABI.md</a>,
     <a href="source/glon-grammar.ebnf">glon-grammar.ebnf</a>.</p>

  <h2 id="challenges">Challenges</h2>
  <div class="cards">{''.join(cards)}</div>
  <h2 id="verification">Verification</h2>
  <p>Each result below comes from executing the pinned native Glon CLI. Expected values are independent problem results; actual stdout, stderr, exit status, duration, timeouts and the interpreter commit are recorded in the JSON. Harness failures are reported separately from language failures.</p>
  <p class="muted">Generated from {esc(args.results)}. Publication requires every case to pass.</p>
  <h2 id="docs">Language documentation</h2>
  <ul>{doc_links(config)}</ul>
</main>
<footer>Static challenge index. No framework, CDN or runtime service. Source: <a href="https://github.com/gchiu/glon">gchiu/glon</a>.</footer>
"""
    (out / "index.html").write_text(clean_html(page_shell("Glon — Language Documentation and Challenges", index_body)), encoding="utf-8")

    for r in results:
        name = r.get("challenge", "unknown")
        d = out / "challenges" / name
        d.mkdir(parents=True, exist_ok=True)
        source_name = r.get("source", "")
        source_path = args.challenges / name / source_name
        source_text = source_path.read_text(encoding="utf-8") if source_path.is_file() else ""
        (d / "source.glon").write_text(source_text, encoding="utf-8")
        shutil.copyfile(args.results / (name + ".json"), d / "results.json")
        body = challenge_body(r, source_text, config, args.challenges / name)
        (d / "index.html").write_text(
            clean_html(page_shell(r.get("title", name) + " — Glon Challenge", body, home_href="../../index.html")),
            encoding="utf-8")
    print(f"build-site: wrote {out} for {len(results)} challenge(s), {passed}/{total} cases passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
