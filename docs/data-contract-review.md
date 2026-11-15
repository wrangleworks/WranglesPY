# Data-contract review workbook

[Overview](../README.md) · [Data contracts](data-contracts.md) ·
[Missing-value guide](missing-values.md)

Open [the Excel review workbook](data-contract-review.xlsx) or
[download the saved file](https://github.com/wrangleworks/WranglesPY/raw/refs/heads/codex/pandas-data-contracts/docs/data-contract-review.xlsx).
The sequenced plan, current status, unresolved policies and preparation
acceptance criteria belong to
[issue #1279](https://github.com/wrangleworks/WranglesPY/issues/1279).
The preparatory implementation is
[draft PR #1278](https://github.com/wrangleworks/WranglesPY/pull/1278).

## What is in the workbook?

The workbook contains the November 14, 2026 analysis of **110 schema-exposed
operation paths**, including aliases. Each operation distinguishes its
DataFrame wrapper from the core Python, pandas, hybrid, NumPy, SQL or external
implementation. Current behavior, proposals, reproduced defects and policy
questions are separate; static classification does not establish complete
behavioral coverage.

| Sheet | Purpose |
| --- | --- |
| Index | Navigation, source baseline, scope and conventions. |
| Operations | Current handling, core engine, risks, proposed handling and editable review decisions/notes for all 110 operations. |
| Decisions | Shared policy questions and editable team decisions. Start here. |
| Findings | Reproduced defects, source findings and hypotheses, with their evidence and scope. |
| Validation | Preparatory pandas 2.3.3 checks separated from earlier PR #1274 experiments. Overlapping test counts must not be added. |
| Contract cases | Examples distinguishing nulls, empty/whitespace text, literal marker strings, zero/false and containers. |

In this analysis, “markers” means legacy **text representations** such as
`"None"` and `"nan"`. It does not mean custom Python sentinel objects.

Use the blank review fields to record proposals or decisions with colleagues;
publish accepted contracts in the owning source/docs and issue. A proposal or
an empty review cell is not approval. Preserve entered notes when publishing
later revisions rather than regenerating this snapshot over them.

## Provenance and verification

- Analysis baseline: main at `79a683312d67944523fc4696bec1e7daace9b05a`.
  Workbook source links are pinned to that baseline.
- Proposed runtime implementation recorded by the workbook: `751feb9f` on
  `codex/pandas-data-contracts`, draft PR #1278. The workbook is a historical
  snapshot; current branch/CI/merge status belongs in GitHub.
- Published to the branch on November 15, 2026 as an **exact byte copy** of the
  issued local `Review.xlsx`. No workbook data or review fields were rewritten.
- Saved-file size: **50,516 bytes**. SHA-256:
  `86e9ca1e065654fe7496fdc88ae997db58b607f1a3d977fd9af1f6d42c446d51`.
- Saved-file inspection verified 110 unique operation rows, six native Excel
  tables, frozen headers/key columns and the expected source hyperlinks. Review
  input fields were unfilled in this saved snapshot.
- No macros, formulas, embedded objects or external workbook connections were
  found. Ordinary GitHub/pandas documentation hyperlinks remain intact. All six
  sheets were rendered and visually reviewed during authoring; this does not
  claim a native Excel application test.

This small binary file is an explicitly published review document, not an
automated-test fixture. It contains code-analysis material and deliberately
illustrative values rather than customer records or service credentials.
Generated run outputs and local working data remain under ignored `.data/`;
only this selected workbook is tracked.
