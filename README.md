# Glon Programming Challenges and Language Documentation

An independent challenge suite and the canonical public documentation portal for the published Glon Alpha language.

The purpose is to measure how many REBOL Cookbook and Rosetta Code style
problems can be solved using Glon's existing, published grammar and vocabulary
— without adding primitives, changing the parser, or modifying the runtime.

This repository contains challenge programs, verification scripts, generated
language documentation and the static public website. It does **not** contain
the Glon interpreter, its applications, demos or the engineering website. The
interpreter and authoritative language sources are pinned from
[`gchiu/rebol-substrate-experiment`](https://github.com/gchiu/rebol-substrate-experiment).

The canonical public documentation portal is:

- https://gchiu.github.io/glon/language/
- https://gchiu.github.io/glon/grammar/

The engineering repository remains authoritative for language development and
source specifications. This repository generates rendered HTML from the pinned
upstream Markdown and EBNF; it does not maintain divergent handwritten copies.

## Current status

| Challenge | Language surface | Status |
|---|---|---|
| [GCD](challenges/gcd/README.md) | Nonnegative integer subtraction Euclid | Verified |
| [Factorial](challenges/factorial/README.md) | Recursive multiplication, 0!–19! | Verified; overflow at 20! |
| [File Text Replacement](challenges/file-replace/README.md) | REBOL 2 Cookbook file replace, in-memory partial | Partial; file I/O blocked |

Challenges are added one at a time and reviewed before the next is started.
REBOL Cookbook challenges include the original `reference.reb` listing alongside
the Glon source; the generated page compares their behaviour and limitations.

## Pinned interpreter

`interpreter.json` records the exact engineering commit used for verification:

```text
repository: https://github.com/gchiu/rebol-substrate-experiment
commit:     89de40e737b022a0d987093bb6c5b1e8d1a8a83e
build:      make glon
```

The build target produces the native `glon` CLI plus its `glon-lib/` libraries
from that commit. The interpreter is not copied into this repository.

Rendered language documentation:

- [Language reference](https://gchiu.github.io/glon/language/)
- [Grammar and railroad diagrams](https://gchiu.github.io/glon/grammar/)
- [Alpha language laws](https://gchiu.github.io/glon/language/laws.html)
- [Language specification](https://gchiu.github.io/glon/language/spec.html)
- [Evaluation model](https://gchiu.github.io/glon/language/evaluation.html)
- [Host ABI](https://gchiu.github.io/glon/language/host-abi.html)
- [AI authoring guide](https://gchiu.github.io/glon/language/ai-authoring.html)

Original upstream Markdown and EBNF are preserved under `/source/`, including
`source/GLON-LANGUAGE-SPEC.md`, `source/GLON-ALPHA-LAWS.md` and
`source/glon-grammar.ebnf`.

## Repository layout

```text
challenges/<name>/
  <name>.glon       challenge source; definitions only, no test calls
  cases.json        challenge metadata, cases, expected results and limits
  README.md         problem statement and language notes
scripts/
  build-interpreter.sh   build the pinned engineering commit in a temp/tools dir
  run-challenges.py      execute cases and write machine-readable results
  build-site.py          render the challenge site from verified results
  build-docs.py          render upstream Markdown/EBNF into language/grammar pages
docs/                    generated static site (GitHub Pages)
  challenges/            verified challenge pages
  language/              rendered language documentation
  grammar/               grammar reference and railroad diagrams
  source/                original Markdown and EBNF at stable URLs
  assets/                locally vendored Mermaid runtime
interpreter.json         pinned interpreter commit and documentation links
requirements.txt         pinned documentation build dependency
.github/workflows/       verification and Pages publication
```

## Build the interpreter locally

From the repository root:

```sh
scripts/build-interpreter.sh 89de40e737b022a0d987093bb6c5b1e8d1a8a83e .tools/glon-eng
```

The script clones the engineering repository at the pinned commit and runs
`make glon`. The resulting CLI is `.tools/glon-eng/glon`; its `glon-lib/`
directory sits beside it and is loaded automatically.

`.tools/` is ignored by Git.

## Run the checks

```sh
python3 scripts/run-challenges.py \
  --glon .tools/glon-eng/glon \
  --output results

python3 scripts/build-site.py \
  --results results \
  --out docs \
  --require-pass
```

Rendered documentation is built from the same pinned upstream checkout:

```sh
python3 -m pip install -r requirements.txt
python3 scripts/build-docs.py --upstream .tools/glon-eng --out docs
```

`build-docs.py` verifies that the checkout is exactly the commit in
`interpreter.json`, copies the original Markdown/EBNF into `docs/source/`,
renders language pages into `docs/language/`, and imports the generated grammar
page and railroad SVGs into `docs/grammar/`.

`run-challenges.py` exits with:

- `0` — every case passed;
- `1` — a language or expected-output failure;
- `2` — a harness error (missing interpreter/source/case data, invalid JSON,
  process could not be started).

Results record actual stdout, stderr, exit status, duration, timeout status and
the interpreter commit. They are not fabricated from expected values.

`build-site.py --require-pass` refuses to build a published site unless every
challenge result is fully passing. The publication workflow only deploys the
generated artifact after that check succeeds, so a failed test cannot overwrite
the last successfully published site.

## REBOL Cookbook reference implementations

For a REBOL Cookbook challenge, add the original program verbatim as
`challenges/<name>/reference.reb` and add a `reference_implementation` object to
`cases.json`:

```json
{
  "reference_implementation": {
    "language": "REBOL 2",
    "source": "reference.reb",
    "title": "Original recipe title",
    "attribution": "Author and recipe attribution",
    "url": "https://web.archive.org/.../archived-recipe.html",
    "notes": "What the original program does"
  }
}
```

An optional `implementation_comparison` object supplies the comparison by
abstraction layer:

```json
{
  "implementation_comparison": {
    "layers": [
      {
        "layer": "1. Core operations and primitives",
        "rebol": "What the reference runtime provides; do not assert provenance without evidence.",
        "glon": "What the frozen S1/R0 layers provide.",
        "note": "Comparability note."
      },
      {
        "layer": "2. Mezzanine/library functions",
        "rebol": "For example: replace is a mezzanine in Oldes' Rebol 3 at src/mezz/mezz-series.reb:129; this does not establish REBOL 2 provenance.",
        "glon": "The reusable Glon library function and its scope.",
        "glon_source_size": true,
        "note": "Library layer, not application equivalent."
      },
      {
        "layer": "3. Application code",
        "rebol": "The reference application and the facilities it uses.",
        "glon": "Whether a complete Glon application exists and what is missing.",
        "rebol_source_size": true,
        "note": "Application layer; state missing file I/O explicitly."
      }
    ],
    "notice": "Source sizes are factual metadata labelled by layer, not a concision claim."
  }
}
```

The generator displays the original and Glon listings side by side on desktop
and stacked on mobile, adds both to the challenge page, and puts source-size
metadata in the layer where it belongs. It must not imply that the programs
are equally concise or that the original program was executed. Every reference
source must remain byte-for-byte verbatim.

## Challenge rules

- Use only the published Glon grammar and existing vocabulary.
- Do not add primitives, parser features, grammar changes or host facilities.
- Do not silently substitute REBOL semantics for Glon semantics.
- Keep harness failures separate from language failures.
- Preserve failures and documented limits.
- Record the interpreter commit used for every result.
- Reuse the same runner and site builder for subsequent challenges.

## CI and website

- `.github/workflows/verify.yml` runs on pushes and pull requests, builds the
  pinned interpreter, executes all challenges, renders the documentation and
  validates the site builder.
- `.github/workflows/publish.yml` runs verification first and deploys to GitHub
  Pages only after it succeeds.
- The committed `docs/` tree is a local snapshot generated from actual results
  and the pinned upstream documentation. GitHub Actions rebuilds it before
  publication.

The website is plain static HTML/CSS. Mermaid diagrams use a locally vendored
runtime (`docs/assets/mermaid.min.js`); there is no CDN or runtime service.
