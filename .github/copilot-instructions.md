# 80% Completion — Quarterly Epic Report

This project generates quarterly epic completion reports from Jira. It tracks committed initiatives and their linked epics, producing status breakdowns with change tracking.

## Project structure

- `prefetch.py` — Bulk Jira REST API fetcher. Produces `_80completion_input.json`.
- `build_report.py` — Generates markdown report from the JSON.
- `generate_xlsx.py` — Generates Excel report (5 sheets) from the JSON.
- `config.yaml` — User's Jira settings (not committed, see `config.example.yaml`).
- `config_loader.py` — Loads config from YAML + environment variables.

## How to run the skill

### Step 1: Determine the quarter

Ask the user which quarter to report on (e.g. "Q1 2026"). Derive epic labels:
- Primary: `26Q1` (format: `YYQn`)
- Alternative: `26_Q1` (format: `YY_Qn`)

### Step 2: Fetch data

```bash
python3 prefetch.py "<quarter>" "<output_dir>"
# Example:
python3 prefetch.py "Q1 2026" "80completion-outputs/2026-03-16_Q1_Report"
```

### Step 3: Build reports

```bash
python3 build_report.py <output_dir>/_80completion_input.json <output_dir>
python3 generate_xlsx.py <output_dir>/_80completion_input.json <output_dir>
```

Output:
- `<Quarter>-Epic-Report.md` — markdown report
- `<Quarter>-Epic-Report_YYYY-MM-DD.xlsx` — Excel with 5 sheets

## Configuration

All Jira-specific settings are in `config.yaml`:
- `jira.url`, `jira.username`, `jira.api_token` — Jira connection (or use env vars `JIRA_URL`, `JIRA_USERNAME`, `JIRA_API_TOKEN`)
- `initiatives.issue_type` — issue type name (default: "Initiative")
- `initiatives.commit_label` — label marking committed initiatives (default: "commit")
- `initiatives.quarter_field_id` — custom field ID for quarter checkboxes
- `initiatives.prio_field_id` — custom field ID for priority (optional)
- `initiatives.domain_field_id` — custom field ID for domain (optional)

## Report structure

### Summary sheet (Excel)
- **Overall status breakdown**: Done / In Progress / To Do counts and percentages, with Change column (pp delta vs previous report)
- **Per-domain breakdowns**: Same structure, one table per domain

### Other sheets
- **Committed Initiatives**: Sorted by prio, with Jira links
- **Labeled Epics**: Grouped by initiative, with domain and labels
- **Unlabeled Epics**: Linked epics missing quarter labels
- **Unmapped & Issues**: Orphaned epics + initiatives with no linked epics

## Key rules
- Cancelled epics are excluded from all calculations
- Change tracking is automatic — compares against previous `_80completion_input.json` in sibling directories
- Never proceed without a confirmed quarter from the user
