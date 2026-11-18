# REBOL 2 Cookbook: File Text Replacement

## Original REBOL 2 program

```rebol
file: %doc.txt
text: read file
replace text "web" "rebol"
write file text
```

The reference program reads a text file, replaces the first occurrence of
`"web"` with `"rebol"`, and writes the modified contents back to the same file.

Original source is preserved verbatim in [`reference.reb`](reference.reb).

Attribution: **Carl Sassenrath**, REBOL Cookbook recipe 0004, “Replace Text in a
File”. Archived recipe:
<https://web.archive.org/web/20250320233703/http://www.rebol.net/cookbook/recipes/0004.html>.

## Result: complete operation cannot be reproduced

The pinned native Glon interpreter and the published language vocabulary do not
provide a file read/write interface:

- The native `glon FILE...` CLI treats arguments as **Glon source files**; it
  does not expose file read/write words to programs.
- The language specification and string library provide immutable in-memory
  strings and output (`s/print`), but no file operations.
- The WASM/browser host has no filesystem.
- The desktop proof has an asynchronous `fs-read` request/reply binding, but no
  general Glon file-write binding. It is a separate host application, not the
  pinned native CLI used by this challenge suite.

No new primitive, parser feature, runtime change or host-side replacement
algorithm was added.

## Partial Glon implementation

[`replace.glon`](replace.glon) implements REBOL's first-occurrence replacement
semantics on in-memory strings, using the published optional `strings-ext`
library for `s/slice` plus the existing `s/+`, `s/=`, and `s/length` functions.

The runner loads the unmodified upstream `strings-ext.glon` from
`vendor/strings-ext.glon` before the challenge source. It is a copy of the
published optional library at the pinned interpreter commit.

Verified in-memory cases:

| Case | Input | Expected |
|---|---|---|
| beginning | `web site` | `rebol site` |
| middle | `the web is wide` | `the rebol is wide` |
| end | `the web` | `the rebol` |
| no match | `the internet` | `the internet` |
| multiple matches | `web web web` | `rebol web web` |
| empty file text | empty string | empty string |

Only the first occurrence changes. Later occurrences remain unchanged.

These are **string-content tests**, not file tests. The file read/write part of
the original REBOL program remains blocked by the missing host capability.

## Three-layer comparison

The REBOL and Glon source listings are not equivalent abstraction layers.

| Layer | REBOL 2 | Glon |
|---|---|---|
| **1. Core operations and primitives** | REBOL 2 provides its own runtime and series/file facilities. This comparison does not assert which of `read`, `replace` and `write` are core primitives. | S1 has seven frozen primitives and the R0 evaluator has no file or replace primitive. String operations are library code. |
| **2. Mezzanine/library functions** | `replace` is a mezzanine in Oldes' Rebol 3 at `src/mezz/mezz-series.reb:129`. This does not establish the exact implementation or provenance of REBOL 2's `replace`. | `replace-first` is a reusable Glon library implementation over `s/slice`, `s/+`, `s/=` and `s/length`. It handles in-memory first-occurrence replacement only. |
| **3. Application code** | The Cookbook application is four lines of REBOL: read a file, call the existing `replace` mezzanine, write the file. | No complete application is implemented. The pinned native CLI has no file read/write capability; only the in-memory replacement job is tested. |

The source-size metadata is therefore labelled by layer:

- REBOL application listing: **4 lines / 74 bytes**;
- Glon `replace-first` library listing: **31 lines / 1,038 bytes**;
- Glon file application: **not implemented**.

These figures are not a concision comparison. The REBOL application uses
existing runtime/mezzanine facilities and file I/O; the Glon listing is a
reusable library function and the Glon file application is incomplete.

## Required host dependency for the complete operation

A complete implementation would need a documented Glon file capability, at
minimum:

- read the file content as a Glon STRING! or byte sequence;
- write the resulting string back to the same path.

Those operations are host-specific and are not present in the pinned native
CLI. This challenge does not emulate them with C, Python, shell commands or
host-side text processing.

## Verification

```sh
scripts/build-interpreter.sh 89de40e737b022a0d987093bb6c5b1e8d1a8a83e .tools/glon-eng
python3 scripts/run-challenges.py --glon .tools/glon-eng/glon --output results --run-probes
python3 scripts/build-site.py --results results --out docs --require-pass
python3 scripts/build-docs.py --upstream .tools/glon-eng --out docs
```

The generated challenge page records the partial status, actual outputs,
interpreter commit and the missing file capability.
