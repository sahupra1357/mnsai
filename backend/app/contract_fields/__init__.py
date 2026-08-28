"""Contract field extraction: a ten-field schema over the visual extractor.

The operator picks any non-empty subset of the ten fields; five of them start
selected by default, and every one of them can be moved out. Whatever is selected, the result carries **the same ten keys in the
same order** (``catalogue.CANONICAL_FIELD_KEYS``), every value a string, blank when a
value could not be grounded, normalized, or was never asked for.

This package is purely additive — it reads what the visual document extractor already
produced and never runs its own OCR, and never modifies the existing pipeline.
"""
