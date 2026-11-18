# Factorial

## Problem

Compute `n!` for a nonnegative integer using recursive multiplication.

- `0! = 1`
- `1! = 1`
- for `n > 1`, `n! = n * (n - 1)!`

The Glon source uses only `func`, `either`, `<=`, `-`, `*` and recursion. It
does not add iteration, primitives, parser features, host facilities or runtime
changes.

## Attribution

Challenge family: REBOL Cookbook / Rosetta Code. Problem definition:
[Rosetta Code — Factorial](https://rosettacode.org/wiki/Factorial). The Glon
implementation here is original for this challenge.

## Glon source

[`fact.glon`](fact.glon) defines `factorial` only. The runner appends one
`print <call>` expression per case.

## Verified cases

The committed results cover `0!` through `19!`. The required `0!` through `12!`
range is included, including both base cases:

| n | Expected |
|---:|---:|
| 0 | 1 |
| 1 | 1 |
| 2 | 2 |
| 3 | 6 |
| 4 | 24 |
| 5 | 120 |
| 6 | 720 |
| 7 | 5040 |
| 8 | 40320 |
| 9 | 362880 |
| 10 | 3628800 |
| 11 | 39916800 |
| 12 | 479001600 |

The result JSON also verifies 13! through 19! against independent Python
`math.factorial` values. All 20 cases pass on the pinned interpreter.

## First limitation: arithmetic overflow at 20!

The first incorrect result is `20!`:

```text
mathematical 20! = 2432902008176640000
Glon actual     = 127058998962946048
exit status     = 0
```

Glon does not detect or raise on integer overflow. The process still exits
successfully and prints a wrapped/incorrect tagged integer. Later factorial
values are not mathematically valid results even though the interpreter may
still exit 0.

## Later limitation: recursion exhaustion

A separate resource limit exists much later:

| Call | Observed |
|---|---|
| `factorial 85` | exit 0, stdout `0` (already overflowed) |
| `factorial 86` | exit 1, machine halt: return-stack exhaustion |

The 86! failure is resource exhaustion, not arithmetic overflow. It is a
machine-level fail-stop, not a catchable `SIN!`, and is preserved in the
results rather than worked around by changing the runtime.

## Verification

```sh
scripts/build-interpreter.sh 89de40e737b022a0d987093bb6c5b1e8d1a8a83e .tools/glon-eng
python3 scripts/run-challenges.py --glon .tools/glon-eng/glon --output results --run-probes
python3 scripts/build-site.py --results results --out docs --require-pass
python3 scripts/build-docs.py --upstream .tools/glon-eng --out docs
```

The exact interpreter commit, actual stdout/stderr, exit statuses, durations,
resource probes and verification date appear on the generated challenge page.
