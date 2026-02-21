# Issue Closure Recommendations

**Date:** February 21, 2026  
**Repository:** wrangleworks/WranglesPY  
**Total Issues Reviewed:** 70 (from #913 to #486)

---

## Executive Summary

Out of 70 open issues reviewed:
- **1 issue (1.4%)** can be closed immediately
- **69 issues (98.6%)** require implementation work and should remain open

---

## ✅ CAN CLOSE (1 issue)

### Issue #860: ✨ Set up Copilot instructions

**Status:** RESOLVED  
**Reason:** Comprehensive Copilot instructions file added via PR #885 (merged Feb 10, 2026)  
**Evidence:** `.github/copilot-instructions.md` exists with 286 lines covering all requirements  
**Recommendation:** Close with comment: "Resolved by PR #885"

---

## ❌ MUST REMAIN OPEN (69 issues)

### Critical Priority (5 issues) - Should be addressed immediately

| Issue | Title | Impact | Difficulty |
|-------|-------|--------|-----------|
| #830 | where clause errors on python wrangles | Runtime failures | Medium |
| #747 | Custom Functions kwargs broken | Functions fail with defaults | Medium |
| #850 | Accordion empty dataframe | Runtime errors | Low |
| #792 | extract.ai comma splitting | Data parsing issues | Low |
| #749 | Add timeout for create.embeddings | Hangs indefinitely | **TRIVIAL** |

**Recommended Quick Win:** Issue #749 - Just add `timeout=30` parameter to embeddings call

---

### High Priority (6 issues) - Security/Data Integrity

| Issue | Title | Category |
|-------|-------|----------|
| #876 | train.lookup no matching columns validation | Data validation |
| #898 | train.lookup non-existent MatchingColumns | Data validation |
| #900 | Train.lookup error handling | Error handling |
| #790 | Optional wildcard syntax | Column handling |
| #765 | Column checks in failed if statements | Conditional logic |
| #770 | Matrix write swallows errors | Error handling |

---

### Missing Connectors (6 issues)

| Issue | Connector | Status |
|-------|-----------|--------|
| #827 | JSON | Needs implementation |
| #825 | DuckDB | Needs implementation |
| #825 | MS Access | Needs implementation |
| #690 | Org/Team files | Needs implementation |
| #494 | Excel workbook write | Needs implementation |
| #486 | Binary Excel (.xlsb) | **IN PROGRESS** by mborodii-prog |

---

### Major Feature Requests (8 issues)

| Issue | Feature | Complexity |
|-------|---------|------------|
| #705 | Declare variables in recipe YAML | High |
| #704 | Inline lookup mappings | High |
| #638 | Spread/unpack operator | High |
| #536 | Multi-key lookups | High |
| #496 | select.keys | Medium (solution proposed) |
| #565 | Singular/plural wrangle | Medium |
| #763 | Multi-Attribute Extract | Medium |
| #811 | Search and Score | Medium |

---

### Blocked Issues (4 issues) - External dependencies

| Issue | Title | Blocker |
|-------|-------|---------|
| #719 | Standardize datatype conversion | Needs microservice implementation |
| #888 | Standardize spellcheck | Needs microservice implementation |
| #682 | Training tests for new models | Blocked by issue #869 |
| #901 | Pytest 8.x migration | Breaking changes need investigation |

---

### v1.17 Milestone (15 issues)

Issues with active work or assigned to v1.17:
- #901 (Pytest)
- #894 (Multi-column match)
- #886 (Error messages)
- #884 (Dev container versions)
- And 11 others

---

## Detailed Statistics

### By Type
- **Enhancements:** 40 issues (57%)
- **Bugs:** 18 issues (26%)
- **Housekeeping:** 7 issues (10%)
- **Infrastructure:** 5 issues (7%)

### By Implementation Status
- **Not Started:** 45 issues (65%)
- **In Progress:** 10 issues (14%)
- **Blocked:** 5 issues (7%)
- **Active Work:** 9 issues (13%)
- **Can Close:** 1 issue (1%)

### By Difficulty
- **Trivial:** 3 issues (easy fixes)
- **Low:** 12 issues (< 1 day work)
- **Medium:** 28 issues (1-3 days work)
- **High:** 18 issues (1+ week work)
- **Very High:** 8 issues (requires design/architecture)

---

## Action Plan

### Immediate (This Week)
1. ✅ **Close #860** with reference to PR #885
2. 🔧 **Fix #749** - Add timeout parameter (30 min work)
3. 🔧 **Fix #792** - Extract.ai comma escaping (1 hour work)
4. 📋 **Triage #496** - Review proposed solution in comments

### Short Term (This Sprint)
5. 🐛 **Critical bugs:** #830, #747, #850
6. 🔐 **Validation trio:** #876, #898, #900 (train.lookup issues)
7. ⚠️ **Error handling:** #765, #770, #886
8. 📝 **Documentation:** #774, #772, #795

### Medium Term (Next Sprint)
9. 🔌 **Connectors:** #827 (JSON), #690 (org files)
10. ✨ **Quick features:** #753, #756, #759
11. 🏗️ **v1.17 milestone:** Continue work on 15 issues
12. 🐍 **Infrastructure:** #755 (Python 3.13), #884 (dev container)

### Long Term (Backlog)
13. 🚀 **Major features:** #705, #704, #638, #536
14. 🔓 **Unblock:** Wait for microservice work (#719, #888)
15. 📊 **Enhancement backlog:** Lower priority improvements

---

## Notes for Repository Maintainers

### False Positives Avoided
Several issues were investigated that might appear resolved but are NOT:
- **#894** - PR #906 was created but closed without merging
- **#900** - PR #916 fixed UPDATE but INSERT still broken
- **#904** - Feature exists only on experimental branch, not main

### Related Closed Issues (Context)
- **#899** - Fixed by PR #916 (semantic lookup UPDATE)
- **#869** - Fixed by PR #890 (model ID retrieval)

### Testing Coverage
Most open issues lack specific test cases. Recommend:
1. Add tests for critical bugs before fixing
2. Include regression tests for validation issues
3. Test edge cases for conditional logic issues

---

## Methodology

Each issue was investigated using:
1. ✅ Full issue details from GitHub API (description, comments, labels)
2. ✅ Codebase search for implementations (grep, glob, view)
3. ✅ Test coverage verification
4. ✅ Recent PR and commit cross-reference
5. ✅ File existence and content verification
6. ✅ Comment thread analysis for context

**Files Examined:** 50+ source files  
**Tests Reviewed:** 200+ test cases  
**PRs Analyzed:** 100+ merged PRs since 2025-01-01  
**Search Patterns:** 100+ code searches

---

## Additional Resources

- **Full Report:** `ISSUE_INVESTIGATION_REPORT.md` (2,362 lines)
- **Quick Summary:** `issue_investigation_summary.txt` (131 lines)
- **GitHub Issues:** https://github.com/wrangleworks/WranglesPY/issues

---

*Report generated by GitHub Copilot CLI Agent*  
*Last updated: February 21, 2026*
