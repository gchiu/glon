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

## Result: complete original-path replacement

The pinned native Glon CLI is now built with `make glon MODULES=file`. The
optional asynchronous file module provides general read/write/temporary-file/
rename operations. The replacement algorithm remains Glon. The application
reads the existing file, replaces only the first occurrence, and atomically
replaces the original path. Files larger than the managed heap are streamed in
400-byte chunks; the host never performs substring replacement.

The application-level source is [`replace.glon`](replace.glon):

```glon
cookbook/replace-first: func [] [
    file/replace-first "doc.txt" "web" "rebol"
        func [done] [ s/print "COOKBOOK_DONE" ]
        func [error] [ raise error ]
]
```

The callbacks are honest asynchronous completion handlers; the operation
returns immediately and completes over later reply turns.

### Safe replacement semantics

`file/replace-first path old new success failure`:

1. opens the source read-only;
2. creates a unique `O_EXCL` temporary in the same directory, initially mode
   0600;
3. streams the first-occurrence replacement to the temporary;
4. checks every read, write, close and source-staleness condition;
5. applies the source permission bits and atomically renames the temporary over
   the original path;
6. on failure removes the temporary where possible and leaves the original path
   unchanged.

This is atomic with respect to process-level failure and concurrent readers. It
is **not** power-loss durable: no file or directory `fsync` is performed.
Ownership, group, ACLs, xattrs and timestamps are not preserved; permission bits
are. A symlink final component is rejected. Other hard links keep the old
content after replacement. Concurrent source modification is detected
best-effort from device/inode/size/mtime/mode, not by locking or a content hash.
A forcibly killed process may leave a `.glon-tmp-*` file; normal failure and
cleanup paths remove it.

## Reusable vocabulary

- [`s/replace-first`](vendor/file-replace.glon) — immutable in-memory
  first-occurrence replacement.
- [`stream/replace-first-to`](vendor/file-replace.glon) — streaming replacement
  into an already-open write handle.
- [`file/replace-first`](vendor/file-replace.glon) — safe original-path
  replacement with temporary output and atomic commit.
- [`io/temp-open`, `io/commit`, `io/discard`](vendor/file-atomic.glon) — general
  protocol-v2 filesystem operations, not replacement logic.

Vendored sources and their engineering origins are listed in
[`vendor/SOURCES.md`](vendor/SOURCES.md). The optional file module itself is
built into `glon-lib/` by `make glon MODULES=file` at the pinned commit.

Integrated acceleration: MASM-1 search (`vendor/find.glon`,
`vendor/file-stream-masm.glon`) and MASM-2 request-field encoding
(`vendor/u32.glon`). MASM-3 was not integrated: its matched/boundary benefit was
modest and its no-match performance approximately neutral, so it is not a
justified dependency for this completion. The host contains no text-replacement
code.

## Previous partial result (preserved)

The previous published challenge implemented only in-memory replacement on
`STRING!` values. The pinned CLI had no file read/write vocabulary, so the
original file round trip was not reproduced. Six in-memory cases passed and the
page was labelled **PARTIAL**. That result is superseded by the complete
operation above; it remains in Git history and in this page's completion
history.

## Layered comparison

| Layer | REBOL 2 | Glon |
|---|---|---|
| **1. Core operations and primitives** | REBOL 2 provides its own runtime and series/file facilities. This comparison does not assert which of `read`, `replace` and `write` are core primitives. | S1 has seven frozen primitives and the R0 evaluator has no file or replace primitive. The host file service moves bytes and performs general temp/commit/discard operations; replacement semantics are library code. |
| **2. Mezzanine/library functions** | `replace` is a mezzanine in Oldes' Rebol 3 at `src/mezz/mezz-series.reb:129`. This does not establish the exact implementation or provenance of REBOL 2's `replace`. | `s/replace-first`, `stream/replace-first-to` and `file/replace-first` are reusable Glon library code. `file/replace-first` composes replacement with same-directory temporary output and atomic commit. |
| **3. Application code** | The Cookbook application is four lines: read a file, call the existing `replace` mezzanine, write the same file. | `cookbook/replace-first` invokes the reusable operation with the Cookbook path/strings and asynchronous success/failure callbacks. |

Source sizes are factual metadata by layer, not a concision claim. The REBOL
application uses existing runtime/mezzanine facilities; the Glon application
composes a reusable library and an optional host file service.

## Verification

```sh
scripts/build-interpreter.sh 935e9f7584748fb80590660985bba0af851a03fa .tools/glon-eng
python3 scripts/run-challenges.py --glon .tools/glon-eng/glon --output results --run-probes
python3 scripts/build-site.py --results results --out docs --require-pass
python3 scripts/build-docs.py --upstream .tools/glon-eng --out docs
```

Expected file bytes are generated independently with Python
`bytes.replace(old, new, 1)`. Cases also verify original preservation on
failure, capability denial, path confinement, short reads/writes, temporary
cleanup, symlink/hard-link behaviour, binary content, chunk-boundary matches,
injected close/rename failures, cancellation and 1 KiB–4 MiB files. Actual
stdout, exit status, durations, interpreter commit and file checks are recorded
in `results.json`; none are hand-written.

The engineering implementation and full measurement report:
`docs/design/GLON-COOKBOOK-FILE-REPLACEMENT.md` in
`gchiu/rebol-substrate-experiment` at the pinned commit.

## Limitations

- Optional POSIX file backend only: no WASM, Windows or embedded file backend.
- No power-loss durability (no fsync of file or directory).
- Ownership/ACL/xattr/timestamp preservation is unsupported; permission bits are
  preserved.
- Symlink final components are rejected; hard links other than the replaced path
  keep old content.
- Concurrent modification detection is metadata-based and best-effort.
- Cancellation is cooperative; a commit already executing may complete
  atomically.
- The managed heap remains fixed at 7,232 cells. Live managed memory stays
  bounded, but GC time grows with file size.
