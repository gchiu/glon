# Greatest Common Divisor

## Problem

Compute the greatest common divisor of two nonnegative integers using Euclid's
algorithm.

This challenge uses **repeated subtraction**, not modulo:

- if `b = 0`, the answer is `a`;
- if `a = 0`, the answer is `b`;
- if `a = b`, the answer is `a`;
- if `a > b`, recurse with `a - b` and `b`;
- otherwise recurse with `a` and `b - a`.

The source is deliberately limited to nonnegative integers. Negative inputs are
outside the contract.

## Attribution

Challenge family: REBOL Cookbook / Rosetta Code. Problem definition:
[Rosetta Code — Greatest common divisor](https://rosettacode.org/wiki/Greatest_common_divisor).
The Glon implementation here is original for this challenge.

## Glon source

[`gcd.glon`](gcd.glon) defines the function only. The runner appends one
`print <call>` expression per case, so the source remains reusable and does not
contain hard-coded test output.

## Cases and reference results

| a | b | Expected |
|---:|---:|---:|
| 48 | 18 | 6 |
| 1071 | 462 | 21 |
| 17 | 13 | 1 |
| 42 | 42 | 42 |
| 42 | 0 | 42 |
| 0 | 42 | 42 |
| 0 | 0 | 0 |

The expected values are independent Euclidean GCD results. `gcd(0,0)` is
defined as `0` here to match the proposed recursion's base case.

## Language notes

The implementation uses only published Glon features:

- `func` for a lexical function;
- `either` for conditional execution;
- `=` and `>` for comparison;
- `-` for subtraction;
- recursion for iteration.

No new primitive, parser feature, grammar change or host facility is used.

## Resource limits

The subtraction variant makes one recursive Glon call per subtraction. The
published 64K interpreter has a bounded return stack (about 84 nested calls in
the documented main-world measurement, affected by the loaded libraries and
call shape).

Observed with the pinned interpreter:

| Call | Observed |
|---|---|
| `gcd 73 1` | exit 0, output `1` |
| `gcd 74 1` | exit 1, machine halt (return-stack exhaustion) |

The failure is a machine fail-stop, not a `SIN!`, so `judge` cannot catch it.
This limit is preserved in the results rather than worked around by modifying
the runtime.

## Verification

The committed result snapshot is produced by:

```sh
scripts/build-interpreter.sh 89de40e737b022a0d987093bb6c5b1e8d1a8a83e .tools/glon-eng
python3 scripts/run-challenges.py --glon .tools/glon-eng/glon --output results
python3 scripts/build-site.py --results results --out docs --require-pass
```

The exact interpreter commit, actual stdout/stderr, exit statuses, durations
and verification date are shown on the generated challenge page.
