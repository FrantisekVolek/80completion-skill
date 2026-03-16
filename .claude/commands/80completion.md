# 80% Completion — Quarterly Epic Report

Generate a report of all epics tied to committed initiatives for a given quarter, showing completion status.

Key files (in project root):
- `prefetch.py` — bulk Jira data fetcher (~3 seconds for all data)
- `build_report.py` — markdown report generator
- `generate_xlsx.py` — Excel report generator with per-domain breakdowns

---

## Step 1: Determine the quarter

Before any work begins, confirm the evaluation quarter.

- Ask the user which quarter to report on (e.g. "Q1 2026")
- Derive the epic label(s) to search for — both forms:
  - Primary: `<YY>Q<n>` (e.g. `26Q1`)
  - Alternative: `<YY>_Q<n>` (e.g. `26_Q1`)
- Never proceed without a confirmed quarter.

---

## Step 2: Fetch all Jira data (prefetch)

Run the prefetch script to bulk-fetch all data from Jira:

```bash
python3 prefetch.py "<quarter>" "<output_dir>"
# Example:
python3 prefetch.py "Q1 2026" "80completion-outputs/2026-03-14_Q1_Epic_Report"
```

This fetches:
- Committed initiatives (with prio, domain, status, issue links)
- All labeled epics (with status, labels, owner)
- Unlabeled linked epics (discovered from initiative links)
- Outputs `_80completion_input.json`

---

## Step 3: Build the reports

Generate markdown and Excel reports:

```bash
python3 build_report.py <output_dir>/_80completion_input.json <output_dir>
python3 generate_xlsx.py <output_dir>/_80completion_input.json <output_dir>
```

Output files:
- `<Quarter>-Epic-Report.md` — markdown report
- `<Quarter>-Epic-Report_YYYY-MM-DD.xlsx` — Excel with 5 sheets (Summary, Committed Initiatives, Labeled Epics, Unlabeled Epics, Unmapped & Issues)

---

## Report structure

### Summary sheet (Excel)

#### 1. Overall Epic Status Breakdown
Cancelled epics excluded. Columns: Category, Count, %, Change (vs previous report).

#### 2. Per-Domain Breakdown
One table per domain with same structure. Change column compares against previous report's domain data.

### Committed Initiatives sheet
Sorted by Prio ascending (null last). Columns: Prio, Initiative, Summary, Link, Owner, Domain, Status.

### Labeled Epics sheet
| Prio | Initiative | Domain | Init. Summary | Init. Link | Epic | Epic Summary | Epic Link | Labels | Epic Owner | Status |

### Unlabeled Epics sheet
| Initiative | Domain | Init. Summary | Init. Link | Epic | Epic Summary | Epic Link | Status |

### Unmapped & Issues sheet
- Labeled epics not mapped to any committed initiative
- Initiatives with no linked epics
