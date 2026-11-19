# Rosetta Code: Palindrome Detection

Task: <https://rosettacode.org/wiki/Palindrome_detection>

Return true when a string reads the same in both directions. This challenge is
**exact and case-sensitive** and compares raw bytes. It does not implement
Unicode normalisation, case folding or an inexact “ignore punctuation” mode.

## Glon implementation

The proposed implementation used the words `true` and `false`. Those words are
not bound in the pinned Glon prelude, and the program fail-stops if they are
used. The verified implementation corrects this with Glon's existing Boolean
convention: **1 for true, 0 for false**.

Indexing is inclusive: `left` starts at 0 and `right` starts at `length - 1`.
`s/raw-at` returns one byte as an integer, so the comparison is exact and
case-sensitive.

```glon
palindrome-range?: func [text left right] [
    either >= left right [
        1
    ] [
        either = s/raw-at text left s/raw-at text right [
            palindrome-range? text + left 1 - right 1
        ] [
            0
        ]
    ]
]

palindrome?: func [text] [
    palindrome-range? text 0 - s/length text 1
]
```

The source is definitions-only; the case runner supplies calls such as
`print palindrome? "racecar"`.

## REBOL implementation from Rosetta Code

The actual extended REBOL listing from the page is preserved verbatim in
[`reference.reb`](reference.reb), including its published test suite. It uses
`func` refinements, `==`/`=`, `reverse`, `copy`, `charset` and `parse`.

Attribution and source: **Rosetta Code, “Palindrome detection”, REBOL solution**,
<https://rosettacode.org/wiki/Palindrome_detection>.

The page also contains a separate minimalistic one-line REBOL version; as
published it is malformed/truncated, so the valid extended solution is the
reference here.

### Comparison-semantics differences

- The REBOL extended `palindrome?` is **case-insensitive by default** (`=` on
  strings); `palindrome?/case` uses exact comparison. The Glon challenge
  implements the exact, case-sensitive contract only.
- REBOL also provides `inexact-palindrome?/ignore` to remove selected spaces and
  punctuation. That variant is intentionally not introduced in Glon.
- REBOL `reverse` operates on characters; Glon compares one byte per cell with
  `s/raw-at`. The Glon result is therefore about exact byte sequences, not
  Unicode character sequences.
- Both listings are application-level recursive definitions. Neither source
  size is presented as a concision claim.

## Expected results and verification

Expected values come from independent Python byte-sequence reversal
(`b == b[::-1]`), including case-sensitive text, binary-safe NUL/high-byte
values and deterministic random byte strings. The committed suite has **43
cases**.

| Input | Expected |
|---|---|
| `""` | 1 |
| `"a"` | 1 |
| `"aa"` | 1 |
| `"ab"` | 0 |
| `"aba"` | 1 |
| `"abba"` | 1 |
| `"racecar"` | 1 |
| `"redivider"` | 1 |
| `"glon"` | 0 |
| `"rebol"` | 0 |
| `"Racecar"` | 0 (case-sensitive) |
| `"never odd or even"` | 0 (spaces count) |
| `"neveroddoreven"` | 1 |

Also covered:

- NUL and high-byte palindromes/non-palindromes;
- 20 deterministic random byte sequences (lengths 0–64);
- constructed byte palindromes of lengths 3, 8, 15, 31, 64 and 160;
- exact stdout (`1`/`0`), not merely line counts.

Verification uses the pinned interpreter revision:

```sh
python3 scripts/run-challenges.py \
  --glon .tools/glon-eng/glon \
  --output results \
  --challenge palindrome
```

The pinned revision is recorded in [`../../interpreter.json`](../../interpreter.json);
currently `935e9f7584748fb80590660985bba0af851a03fa`.

## Recursive-depth limitation

Each compared pair adds one recursive activation. The 160-byte constructed
palindrome passes; a 200-byte palindrome (100 pairs) fail-stops with
return-stack exhaustion on the pinned 64K interpreter. This is recorded as a
resource probe, is a machine halt rather than a `SIN!`, and was not pursued to
find a maximum.
