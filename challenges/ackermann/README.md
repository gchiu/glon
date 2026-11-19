# Rosetta Code: Ackermann Function

Task: <https://rosettacode.org/wiki/Ackermann_function>

The two-argument Ackermann function is defined recursively:

- A(0, n) = n + 1
- A(m, 0) = A(m - 1, 1)
- A(m, n) = A(m - 1, A(m, n - 1))

## Glon implementation

[`ackermann.glon`](ackermann.glon) is the unoptimized recursive definition. It
uses no memoisation, closed-form shortcuts, MASM acceleration or new language
facilities.

```glon
ackermann: func [m n] [
    either = m 0 [
        + n 1
    ] [
        either = n 0 [
            ackermann - m 1 1
        ] [
            ackermann - m 1 ackermann m - n 1
        ]
    ]
]
```

Example: `print ackermann 3 2` produces `29`.

## Expected values

These are the mathematical expected results for the tested table, not results
inferred from prior Glon runs:

| m | n=0 | n=1 | n=2 | n=3 | n=4 |
|---|---|---|---|---|---|
| 0 | 1 | 2 | 3 | 4 | 5 |
| 1 | 2 | 3 | 4 | 5 | 6 |
| 2 | 3 | 5 | 7 | 9 | 11 |
| 3 | 5 | 13 | 29 | 61 | 125 |

## Actual tested range and results

Each case runs in its own bounded process.

- **Passing correctness cases: 19/20.** All values for m = 0..3 and n = 0..4
  except (3,4) were produced correctly.
- **Resource-limit probe: A(3,4).** The mathematically expected value is 125,
  but the unoptimized Glon recursion fail-stops on the pinned 64K interpreter
  with a machine-level halt (not a `SIN!`) before producing a result. It is
  recorded as a resource probe, not as a passing case.

No larger inputs were pursued to determine a maximum recursion depth.

## REBOL implementation from Rosetta Code

The unoptimized REBOL listing from the Rosetta Code page is preserved verbatim
in [`reference.reb`](reference.reb):

```rebol
ackermann: func [m n] [
    case [
        m = 0 [n + 1]
        n = 0 [ackermann m - 1 1]
        true [ackermann m - 1 ackermann m n - 1]
    ]
]
```

Attribution and source: **Rosetta Code, “Ackermann function”, REBOL solution**,
<https://rosettacode.org/wiki/Ackermann_function>. The page also shows a
separate optimized small-`m` variant, which is not used here.

Both listings are application-level recursive definitions at the same
abstraction level. The Glon resource limit is documented rather than hidden by
an optimization.

## Verification

```sh
python3 scripts/run-challenges.py \
  --glon .tools/glon-eng/glon \
  --output results \
  --challenge ackermann
```

The pinned revision is recorded in [`../../interpreter.json`](../../interpreter.json);
currently `935e9f7584748fb80590660985bba0af851a03fa`.

## Limitations

- Correctness is established for the 19 passing table entries only.
- A(3,4) exceeds the pinned interpreter's activation/return-stack resources.
- The fail-stop is a machine halt, not a catchable `SIN!`.
- No memoisation or closed-form shortcuts are added; larger inputs are out of
  scope.
