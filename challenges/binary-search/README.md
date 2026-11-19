# Rosetta Code: Binary Search

Task: <https://rosettacode.org/wiki/Binary_search>

Return the zero-based index of a target integer in an ascending block, or `-1`
when the target is absent. The input block is read-only. For duplicate values,
any matching index is acceptable.

## Glon implementation

The proposed implementation is used, with the acceptance helper
`binary-search-found` added only so duplicate cases can check the value at the
returned index instead of requiring one particular duplicate.

```glon
binary-search-range: func [items target low high] [
    either > low high [
        -1
    ] [
        mid: + low / - high low 2
        value: block-at items mid

        either = value target [
            mid
        ] [
            either < value target [
                binary-search-range items target + mid 1 high
            ] [
                binary-search-range items target low - mid 1
            ]
        ]
    ]
]

binary-search: func [items target] [
    binary-search-range items target 0 - block-len items 1
]
```

Verified conventions against the pinned interpreter:

- `block-len` returns a tagged integer and is available in the prelude.
- `block-at` is **zero-based** and returns the element value.
- `/` performs integer division on tagged integers; the computed midpoint is
  `low + (high - low) / 2` and is nonnegative in this search.
- `mid:` and `value:` are local bindings used only within the current call.
- Empty blocks produce `high = -1`, so the first guard returns `-1`.

No iteration, MASM acceleration, new block operation or other vocabulary is
introduced.

## REBOL comparison

The referenced Rosetta Code **Binary search** page currently publishes no REBOL
solution. No REBOL listing is included here because there is no published source
to preserve; inventing one would misrepresent the page. This differs from the
other Rosetta Code challenges where a REBOL listing exists.

If a REBOL implementation is later published, it should be added verbatim with
attribution, and its indexing, not-found representation and accepted sequence
types compared with this byte/index contract.

## Expected results and verification

Expected indices are generated independently with Python `bisect_left` for
sorted unique blocks. Duplicate cases use `binary-search-found` and require the
returned index to hold the target value, not a specific duplicate index.

The committed suite has **101 cases**, including:

- empty block;
- single-element present/absent;
- two-element blocks;
- odd and even lengths;
- first, middle and last elements;
- missing values between existing elements;
- targets below and above the range;
- negative integers and zero;
- duplicate values and all-identical blocks;
- 12 deterministic randomised sorted blocks with present/missing targets;
- a 511-element literal block, near the parser block/form limit, with first,
  middle, last, between and above-range targets.

Exact stdout (`index` or `-1`) is compared. Input preservation was also checked
locally by searching a block with duplicate values and printing every element
afterwards; all elements were unchanged.

Verification uses the pinned interpreter revision:

```sh
python3 scripts/run-challenges.py \
  --glon .tools/glon-eng/glon \
  --output results \
  --challenge binary-search
```

The pinned revision is recorded in [`../../interpreter.json`](../../interpreter.json);
currently `935e9f7584748fb80590660985bba0af851a03fa`.

## Complexity and indexing cost

- The algorithm makes **O(log n)** comparisons/search steps.
- Recursive activation depth is **O(log n)**; no resource limit was encountered
  for the tested 511-element block.
- No intermediate block copying is performed; only scalar locals and indices are
  created.
- `block-at` is not a generic array primitive. In the current prelude it is a
  MASM worker that untags the block, adds the fixed payload offset and the
  zero-based index, and fetches one cell. It does not scan, so each access is
  constant-time for the current block representation. `block-len` similarly reads
  the stored count. The algorithmic O(log n) bound is therefore not multiplied
  by a linear indexing cost in this implementation.

## Limitations

- Input must already be sorted ascending; sorting and ordering validation are
  outside the contract.
- No REBOL solution is published on the referenced page, so no REBOL reference
  is included.
- The largest tested literal block is 511 elements; larger blocks would need
  construction outside a literal and were not pursued as a capacity
  investigation.
