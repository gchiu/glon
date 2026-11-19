# Rosetta Code: FizzBuzz

Task: <https://rosettacode.org/wiki/FizzBuzz>

Print the integers 1 through 100, replacing multiples of 3 with `Fizz`,
multiples of 5 with `Buzz`, and multiples of both with `FizzBuzz`.

## Glon implementation

[`fizzbuzz.glon`](fizzbuzz.glon) is the posted Glon implementation. The only
harness adjustment is that the final top-level `rows 0` call is supplied by the
case runner; the source is definitions-only like the other challenges.

```glon
divides?: func [d n] [ = n * d / n d ]

say: func [n] [
    either divides? 15 n [ s/print "FizzBuzz" ] [
    either divides? 3 n  [ s/print "Fizz" ] [
    either divides? 5 n  [ s/print "Buzz" ] [
    print n ] ] ]
]

row: func [i last] [
    either > i last [ none ] [ say i row + i 1 last ]
]

rows: func [t] [
    either > t 90 [ none ] [ row + t 1 + t 10 rows + t 10 ]
]
```

### Why the recursion is divided into rows

`row` prints from `i` to `last` recursively. On the pinned 64K interpreter, one
recursive row over 1..100 reaches about line 83 and then fail-stops with
return-stack exhaustion. `rows` divides the output into ten-row blocks
(`row + t 1 + t 10`), keeping each row's activation depth bounded while adding
only ten outer `rows` levels. The direct-row probe in
[`cases.json`](cases.json) records the observed failure; `rows 0` completes all
100 lines.

This is a resource-shaped implementation choice, not a semantic requirement.
It preserves the posted implementation and introduces no library or runtime
change.

## REBOL implementation from Rosetta Code

The original REBOL listing from the Rosetta Code page is preserved verbatim in
[`reference.reb`](reference.reb). It uses `repeat`, `copy`, `case/all`, `append`,
`mod`, `mold` and `print`.

Attribution and source: **Rosetta Code, “FizzBuzz”, REBOL solution**,
<https://rosettacode.org/wiki/FizzBuzz>.

Both listings are application-level programs. The Glon version uses recursion
because the posted implementation does; the REBOL version uses iteration. This
is not a concision comparison.

## Expected results and verification

The expected stdout is exactly 100 lines for 1..100, generated independently
from Python integer modulo rules (not from Glon). The full string is stored in
`cases.json` and compared exactly.

- Correctness case: `rows 0` — all 100 lines, exit 0.
- Resource probe: `row 1 100` — observed machine fail-stop after about 83 lines;
  not counted as a passing correctness test.

Verification uses the pinned interpreter revision:

```sh
python3 scripts/run-challenges.py \
  --glon .tools/glon-eng/glon \
  --output results \
  --challenge fizzbuzz
```

The pinned revision is recorded in [`../../interpreter.json`](../../interpreter.json);
currently `935e9f7584748fb80590660985bba0af851a03fa`.

## Limitations

- The direct 1..100 recursive row exceeds the pinned interpreter's activation
  resources; this is a machine halt, not a catchable `SIN!`.
- The challenge is fixed to the task's 1..100 range.
- No engineering/runtime change was made to increase recursion capacity.
