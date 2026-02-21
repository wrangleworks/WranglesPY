# Open Issues Review - Analysis Report
**Date:** February 21, 2026  
**Purpose:** Review the last 10 open issues to determine which can be closed based on current main branch implementation

---

## Summary

Out of 10 open issues reviewed:
- **1 issue can be CLOSED** (fully resolved by recent PR)
- **1 issue is PARTIALLY RESOLVED** (some aspects addressed, others remaining)
- **8 issues remain OPEN** (not yet addressed in codebase)

---

## Detailed Analysis

### ✅ Issue #899 - ALREADY CLOSED
**Title:** Train.lookup action update requires key column for semantic lookups  
**Status:** Closed on 2026-02-20 via PR #916  
**Analysis:** This issue was about semantic lookups requiring a Key column for updates, which shouldn't be necessary. PR #916 fixed this by updating the logic in `wrangles/connectors/train.py` to distinguish between key-based and semantic/embedding-based variants.

---

### ⚠️ Issue #900 - PARTIALLY RESOLVED (Suggest: Keep Open)
**Title:** Train.lookup specific error handling  
**Status:** Open (Created: 2026-02-13)  
**Related to:** Issue #899

**Analysis:**
- ✅ **UPDATE action validation** - PR #916 addressed the UPDATE issue mentioned (requiring Key column alignment)
- ❌ **INSERT action error** - The issue specifically mentions that INSERT gives a misleading error:
  ```
  requests.exceptions.InvalidJSONError: ERROR IN WRITE: train.lookup - Out of range float values are not JSON compliant: nan
  ```
  This needs better error handling for column misalignment with INSERT action.

**Recommendation:** **KEEP OPEN** - While UPDATE is fixed, INSERT error handling still needs improvement for non-aligned columns.

---

### ❌ Issue #901 - NOT RESOLVED (Keep Open)
**Title:** Pytest - breaking changes  
**Status:** Open (Created: 2026-02-16)

**Analysis:**
- Pytest is currently fixed to version `7.4.4` in `.github/workflows/publish-main.yml` (lines 35, 70, 217)
- The issue requests upgrading to pytest 8.0+ which has breaking changes
- No changes have been made to address the breaking changes in test collection

**Current State:**
```yaml
pip install pytest==7.4.4 lorem pytest-mock
```

**Recommendation:** **KEEP OPEN** - Still needs investigation and code changes to support pytest 8.0+

---

### ❌ Issue #898 - NOT RESOLVED (Keep Open)
**Title:** train.lookup does not fail when using non-existent MatchingColumns  
**Status:** Open (Created: 2026-02-13)

**Analysis:**
- Examined `wrangles/connectors/train.py` for column validation
- Current validation (lines 310-315) checks for missing columns when updating existing models
- However, there's no pre-training validation to catch non-existent MatchingColumns before model training
- The error only appears after training completes, breaking the model

**Recommendation:** **KEEP OPEN** - Needs pre-training validation to check if MatchingColumns exist in the input DataFrame

---

### ❌ Issue #894 - NOT RESOLVED (Keep Open)
**Title:** Action broken with multi-column match/no key column  
**Status:** Open (Created: 2026-02-12)

**Analysis:**
- While PR #916 improved semantic lookup handling without Key columns
- The specific issue with multi-column matching (multiple MatchingColumns without a Key) needs verification
- The issue states: "Insert and upsert simply append the new data, even when they are duplicates of existing data, while update fails completely"
- PR #916 focused on UPDATE action for semantic lookups, not INSERT/UPSERT behavior with multi-column matching

**Recommendation:** **KEEP OPEN** - Needs specific testing for INSERT/UPSERT with multiple MatchingColumns and no Key column

---

### ❌ Issue #895 - NOT RESOLVED (Keep Open)
**Title:** remove_words enhancements  
**Status:** Open (Created: 2026-02-12)

**Analysis:**
Current implementation in `wrangles/extract.py` (lines 590-650):
- ✅ `tokenize_to_remove` parameter exists
- ✅ `ignore_case` parameter exists
- ❌ `tokenize_to_remove` does NOT default to `True` (no default in function signature)
- ❌ No `characters_to_consider` parameter
- ❌ No automatic punctuation/space trimming at beginning/end
- ❌ No automatic list/str conversion logic
- ❌ Missing comprehensive tests for all combinations

**Requirements NOT MET:**
1. `tokenize_to_remove` should default to `True`
2. Add `characters_to_consider: all | letters_numbers_only` (default)
3. Strip punctuation/spaces from beginning/end of tokens
4. Auto-convert between str/list when one is str and other is list
5. Document `ignore_case` default as `True` in schema
6. Add comprehensive tests

**Recommendation:** **KEEP OPEN** - Significant enhancements still needed

---

### ❌ Issue #889 - NOT RESOLVED (Keep Open)
**Title:** Default Vertical Position (Top)  
**Status:** Open (Created: 2026-02-09)

**Analysis:**
- Searched `wrangles/connectors/excel.py` for "vertical", "alignment" - no results
- No vertical alignment settings found in Excel connector implementation
- Issue requests setting default vertical cell alignment to "Top" for:
  - Tables written to excel.sheet > write
  - Files written via file > .xl* connectors
  - Should apply to headers too

**Recommendation:** **KEEP OPEN** - Feature not implemented

---

### ❌ Issue #888 - NOT RESOLVED (Keep Open)
**Title:** Standardize Spellcheck  
**Status:** Open (Created: 2026-02-06)

**Analysis:**
- Searched `wrangles/standardize.py` for "spellcheck" - no results
- Spellcheck parameter exists in `wrangles/extract.py` for extraction (line 427: `use_spellcheck`)
- Issue requests spellcheck functionality for `standardize` function, not extract
- Requires microservice implementation first (per issue description)

**Recommendation:** **KEEP OPEN** - Not implemented in standardize function

---

### ❌ Issue #887 - NOT RESOLVED (Keep Open)
**Title:** Read/Write Meta Data With Train Connector  
**Status:** Open (Created: 2026-02-06)

**Analysis:**
- Examined `wrangles/connectors/train.py`
- Code references metadata internally (lines 271-276, 370, 379) via `_data.model(model_id)`
- However, no exposed read/write methods for users to access or modify model metadata
- Issue suggests variants like `train.meta_data` or adding to existing variants like `train.lookup`

**Recommendation:** **KEEP OPEN** - Metadata read/write functionality not exposed to users

---

### 🆕 Issue #913 - NOT RESOLVED (Keep Open)
**Title:** move large, optional packages to separate add-ons package  
**Status:** Open (Created: 2026-02-19, Most Recent)

**Analysis:**
- Examined `requirements.txt` - contains all dependencies without separation
- All packages (database connectors, cloud services, ML tools) are required on install
- No optional/extras setup in `setup.py`
- Issue suggests moving optional imports to separate package to reduce core package size

**Current dependencies that could be optional:**
- boto3 (AWS S3)
- simple-salesforce (Salesforce)
- pymongo (MongoDB)
- pymssql, psycopg2-binary, pymysql (Database connectors)
- fabric (SFTP)

**Recommendation:** **KEEP OPEN** - Architectural change not implemented

---

### 🔬 Issue #904 - NOT RESOLVED (Keep Open)
**Title:** Categorical maps for lookups  
**Status:** Open (Created: 2026-02-16)

**Analysis:**
- Issue describes a feature for storing categorical mappings in memory for semantic matching
- References code from "classifier-refactor" branch (not in main)
- No implementation found in current main branch
- Would require memory management for categorical encodings

**Recommendation:** **KEEP OPEN** - Feature not implemented in main branch

---

## Recommendations

### Can Close Immediately:
**None** - Issue #899 is already closed

### Should Keep Open (Not Resolved):
1. **#913** - Optional package separation (architectural change needed)
2. **#904** - Categorical maps (new feature)
3. **#901** - Pytest 8.0 upgrade (breaking changes)
4. **#900** - Train.lookup INSERT error handling (partially fixed)
5. **#898** - MatchingColumns validation (needs pre-training check)
6. **#894** - Multi-column match actions (INSERT/UPSERT behavior)
7. **#895** - remove_words enhancements (5+ missing features)
8. **#889** - Excel vertical alignment (not implemented)
9. **#888** - Standardize spellcheck (requires microservice)
10. **#887** - Train metadata read/write (not exposed)

---

## Verification Steps Performed

1. ✅ Fetched last 10 open issues via GitHub API
2. ✅ Reviewed recent commits (20 most recent)
3. ✅ Analyzed closed PRs (especially PR #916)
4. ✅ Examined source code files:
   - `wrangles/connectors/train.py`
   - `wrangles/extract.py`
   - `wrangles/standardize.py`
   - `wrangles/connectors/excel.py`
   - `.github/workflows/publish-main.yml`
   - `requirements.txt`
   - `setup.py`
5. ✅ Cross-referenced issue descriptions with current implementations
6. ✅ Verified PR #916 addressed issue #899 (already closed)

---

## Conclusion

While recent development has made progress (particularly PR #916 addressing issue #899), **none of the 10 open issues reviewed can be closed at this time**. All require additional implementation work, with issue #900 being the closest to resolution (partially addressed by PR #916).

The most straightforward issues to address next would be:
1. **#898** - Add validation for MatchingColumns before training
2. **#900** - Improve INSERT action error handling for column misalignment
3. **#895** - Implement remove_words enhancements (well-specified requirements)
