# 80% Completion — Quarterly Epic Report

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill that generates quarterly epic completion reports from Jira. It fetches all committed initiatives for a quarter, finds their linked epics (both labeled and unlabeled), and produces detailed status breakdowns — overall and per domain — with change tracking against previous reports.

## What it does

Given a quarter (e.g. "Q1 2026"), this skill:

1. **Fetches committed initiatives** — issues matching your configured type + label + quarter field
2. **Finds labeled epics** — epics with quarter labels (e.g. `26Q1`, `26_Q1`)
3. **Discovers unlabeled linked epics** — epics linked to initiatives but missing quarter labels
4. **Produces reports** with:
   - Overall status breakdown (Done / In Progress / To Do) with change vs previous report
   - Per-domain breakdown with the same change tracking
   - Detailed epic tables grouped by initiative
   - Unmapped epics and initiatives with no linked epics

### Output

- **Markdown report** — full text report
- **Excel report** (5 sheets) — Summary with per-domain breakdowns, Committed Initiatives, Labeled Epics, Unlabeled Epics, Unmapped & Issues

## Prerequisites

- Python 3.8+
- A Jira Cloud instance with REST API access
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) (for the `/80completion` skill command)

## Installation

```bash
git clone https://github.com/YOUR_USERNAME/80completion-skill.git
cd 80completion-skill
pip install -r requirements.txt
cp config.example.yaml config.yaml
```

Edit `config.yaml` with your Jira settings:

```yaml
jira:
  url: "https://your-instance.atlassian.net"
  username: "your-email@example.com"
  api_token: "your-api-token"

initiatives:
  issue_type: "Initiative"        # Your initiative issue type name
  commit_label: "commit"          # Label marking committed initiatives
  quarter_field_id: "12304"       # Custom field ID for quarter (checkboxes)
  prio_field_id: "11452"          # Custom field ID for priority (numeric, optional)
  domain_field_id: "11445"        # Custom field ID for domain (dropdown, optional)
```

Alternatively, set credentials as environment variables:
```bash
export JIRA_URL="https://your-instance.atlassian.net"
export JIRA_USERNAME="your-email@example.com"
export JIRA_API_TOKEN="your-api-token"
```

### Finding your custom field IDs

You can find your Jira custom field IDs by:
1. Opening an issue that has the field populated
2. Appending `?expand=names` to the REST API URL: `https://your-instance.atlassian.net/rest/api/2/issue/ISSUE-123?expand=names`
3. Searching the response for your field name

Or use the Jira admin: **Settings → Issues → Custom fields** — the ID is in the URL when you click a field.

## Usage

### With Claude Code (recommended)

Simply run the `/80completion` command in Claude Code. It will ask you for the quarter and handle everything.

### Standalone CLI

```bash
# Step 1: Fetch data from Jira
python3 prefetch.py "Q1 2026" "80completion-outputs/2026-03-16_Q1_Report"

# Step 2: Generate markdown report
python3 build_report.py "80completion-outputs/2026-03-16_Q1_Report/_80completion_input.json" \
                        "80completion-outputs/2026-03-16_Q1_Report"

# Step 3: Generate Excel report
python3 generate_xlsx.py "80completion-outputs/2026-03-16_Q1_Report/_80completion_input.json" \
                         "80completion-outputs/2026-03-16_Q1_Report"
```

## Configuration

### Initiative identification

The tool finds initiatives using this JQL:

```
issuetype = "{issue_type}" AND labels = "{commit_label}" AND cf[{quarter_field_id}] = "Q1 2026"
```

Adjust `issue_type`, `commit_label`, and `quarter_field_id` in `config.yaml` to match your Jira setup.

### Epic labeling convention

The tool expects epics to be labeled with quarter identifiers in one of two formats:
- **Primary**: `YYQn` (e.g. `26Q1`)
- **Alternative**: `YY_Qn` (e.g. `26_Q1`)

These are derived automatically from the quarter input. Epics linked to initiatives but missing these labels appear in the "Unlabeled Epics" section.

### Change tracking

When multiple reports exist in the same parent directory, the Excel generator automatically compares against the most recent previous `_80completion_input.json` and shows percentage point changes in the breakdown tables. No configuration needed — just run the tool repeatedly.

## How it works

```
prefetch.py → _80completion_input.json → build_report.py → .md
                                       → generate_xlsx.py → .xlsx
```

1. `prefetch.py` makes 2-4 REST API calls to Jira (bulk JQL search with pagination)
2. Results are saved as a JSON intermediate file
3. `build_report.py` and `generate_xlsx.py` consume the JSON independently
4. The JSON file also serves as the baseline for future change tracking

## License

MIT
