# Negative Space

**Version:** 0.1  
**Status:** experimental

Negative Space preserves **failed hypotheses, missing evidence, inconclusive searches, unavailable records, and research dead ends** without converting absence into proof.

Its central rule is deliberately strict:

> **not found ≠ proven absent**

Research usually keeps what worked and quietly drops what did not. That makes it easy to repeat the same search, resurrect a failed explanation, or accidentally turn “we could not locate it” into “it never existed.”

Negative Space keeps the discarded paths inspectable.

## What it records

A project contains:

- hypotheses
- hypothesis status history
- individual research checks
- the target and method of each check
- what evidence was expected
- what was actually found
- sources and optional URLs
- conditions under which a parked or rejected hypothesis should be reopened

Hypothesis statuses:

- `open`
- `weakened`
- `parked`
- `rejected`

Check outcomes:

- `found`
- `not-found`
- `inconclusive`
- `unavailable`
- `contradictory`

A check outcome **never automatically changes a hypothesis status**. Status changes require an explicit reason.

## Quick start

```bash
python negative_space.py new research.json --title "Missing diary entry"

python negative_space.py hypothesis research.json \
  "A keeper diary contained the famous final warning." \
  --reopen-when "Reopen if an authenticated diary is located."

python negative_space.py check research.json \
  --hypothesis H001 \
  --target "1904 log transcription" \
  --method "line-by-line review" \
  --expected "The quoted warning" \
  --outcome not-found \
  --result "No matching warning was found in the reviewed transcription."

python negative_space.py status research.json H001 parked \
  --reason "Checked early materials do not contain the warning and the later retelling supplies no traceable source." \
  --reopen-when "Reopen if an authenticated diary or contemporary transcript is found."

python negative_space.py render research.json -o report.md
python negative_space.py dead-ends research.json -o dead-ends.md
python negative_space.py mermaid research.json -o map.mmd
```

## Outputs

Negative Space can produce:

- plain JSON
- a full Markdown research report
- a focused dead-end / parked-path report
- a Mermaid map linking hypotheses to the checks performed on them

## Example

The fictional demo in [`examples/demo.json`](examples/demo.json) follows two familiar research patterns.

One hypothesis concerns a dramatic diary entry that appears in a later retelling but is not found in the checked early materials. It is **parked**, not declared impossible, with a concrete condition for reopening it.

A second weather hypothesis is **weakened** because the available records support rough conditions but not the stronger causal claim.

See:

- [`examples/demo.md`](examples/demo.md)
- [`examples/demo.mmd`](examples/demo.mmd)

## What Negative Space does not do

Negative Space does not treat a failed search as proof of nonexistence.

It does not automatically reject hypotheses.

It does not treat unavailable evidence as negative evidence.

It does not erase failed paths once a better explanation appears.

It records what was checked, how it was checked, what the check returned, and what would justify revisiting the path later.

## Tests

```bash
python -m unittest discover -s tests -v
```

## License and reuse

**No reuse license has been granted.**

This public build is available for inspection and development by its maintainers. Do not assume that public visibility grants permission to copy, redistribute, modify, sell, incorporate, or relicense the code or documentation.

See [`COPYRIGHT.md`](COPYRIGHT.md).

## Working principle

A dead end is still part of the map.
