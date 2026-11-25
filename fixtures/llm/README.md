# Mock model answers

`texts.json` and `categories.json` stand in for Claude in mock mode (the default). They
are **not** real model output: `scripts/build_mock_fixtures.py` writes them from the same
facts the real model would receive, using a fixed template.

The `_planted` list in each file names the answers that were broken on purpose (changed
number, wrong unit, invented VDE or warranty claim, title too long, leading dash, link,
prose instead of JSON, a category outside the list) plus five correct variants that must
pass: two give the length in cm instead of mm, three are phrased the way a real model
writes German copy ("besteht aus", "Bestehend aus", "Bestellnummer"). `tests/test_pipeline.py` asserts that the checks catch every planted defect and
block none of the correct variants.
