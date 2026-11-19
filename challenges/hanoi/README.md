# Rosetta Code: Towers of Hanoi

Task: <https://rosettacode.org/wiki/Towers_of_Hanoi>

Print the sequence of moves that transfers a tower of `n` disks from a source
peg to a target peg using a spare peg. Each line has the form
`source -> target`; the proposed Glon example uses pegs `A`, `C` and `B`.

## Glon implementation

[`hanoi.glon`](hanoi.glon) is the proposed implementation, definitions-only like
the other challenges; the runner supplies the case call.

```glon
hanoi: func [n source target spare] [
    either > n 0 [
        hanoi - n 1 source spare target
        s/print s/+ source s/+ " -> " target
        hanoi - n 1 spare target source
    ] [
        none
    ]
]
```

For the three-letter example the case call is
`hanoi 3 "A" "C" "B"`. The implementation is ordinary Glon `func`/`either`,
comparison, arithmetic, `s/+` and `s/print`; no primitive, vocabulary, allocator
or scheduler change was made.

## REBOL implementation from Rosetta Code

The original REBOL listing from the Rosetta Code page is preserved verbatim in
[`reference.reb`](reference.reb). It uses a `/poles` refinement, default
`left`/`middle`/`right` peg words and a four-disk example.

Attribution and source: **Rosetta Code, “Towers of Hanoi”, REBOL solution**,
<https://rosettacode.org/wiki/Towers_of_Hanoi>.

Both listings are application-level recursive definitions. REBOL selects peg
names through a refinement; Glon passes three explicit string arguments. This
is not a concision comparison.

## Expected results and verification

The exact move sequence is generated independently by the standard Python
recursive reference. Local verification ran the Glon program for disk counts
**0, 1, 2, 3, 5, 8 and 10** in separate bounded processes and checked:

- exact move sequence against the Python reference;
- correct move count `2^n - 1`;
- no larger disk placed on a smaller disk, by simulating the three pegs;
- all disks transferred to the target peg, with source and spare empty.

| Disks | Moves | Result |
|---:|---:|---|
| 0 | 0 | exact sequence, legal, transferred |
| 1 | 1 | exact sequence, legal, transferred |
| 2 | 3 | exact sequence, legal, transferred |
| 3 | 7 | exact sequence, legal, transferred |
| 5 | 31 | exact sequence, legal, transferred |
| 8 | 255 | exact sequence, legal, transferred |
| 10 | 1,023 | exact sequence, legal, transferred |

All 7/7 committed cases compare the exact stdout. No resource limit was
encountered at 10 disks.

Verification uses the pinned interpreter revision:

```sh
python3 scripts/run-challenges.py \
  --glon .tools/glon-eng/glon \
  --output results \
  --challenge hanoi
```

The pinned revision is recorded in [`../../interpreter.json`](../../interpreter.json);
currently `935e9f7584748fb80590660985bba0af851a03fa`.

## Limitations

- Only disk counts 0, 1, 2, 3, 5, 8 and 10 are tested; larger counts were not
  pursued.
- Recursive activation depth grows with disk count, so very large counts may
  exceed the pinned interpreter's resources.
- Peg names are application-level strings; the implementation does not require
  them to be distinct.
