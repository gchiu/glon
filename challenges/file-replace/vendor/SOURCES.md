# Vendored sources

These files are exact copies from the pinned engineering commit recorded in
`interpreter.json`:

| File | Engineering source |
|---|---|
| `find.glon` | `experiments/masm-vocabulary/find.glon` (MASM-1) |
| `u32.glon` | `experiments/masm2/u32.glon` (MASM-2) |
| `file-stream-masm.glon` | `experiments/masm-vocabulary/file-stream-masm.glon` |
| `file-atomic.glon` | `modules/file-atomic.glon` |
| `file-replace.glon` | `modules/file-replace.glon` |

The optional file module itself (`modules/file.glon`, `modules/file-stream.glon`,
`strings-ext.glon`) is built into `glon-lib/` by `make glon MODULES=file` at the
pinned commit and loaded by the CLI automatically.
