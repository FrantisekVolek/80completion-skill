#!/usr/bin/env python3
"""
Pre-fetch all Jira data needed for the 80% completion epic report.

Produces _80completion_input.json that build_report.py and generate_xlsx.py consume.

Usage:
    python3 prefetch.py <quarter> <output_dir>
    python3 prefetch.py "Q1 2026" "80completion-outputs/2026-03-14_Q1_Epic_Report"
"""

import json
import os
import sys

import requests
from requests.auth import HTTPBasicAuth

from config_loader import load_config


def jira_search(base_url, auth, jql, fields, max_results=200):
    """Execute a JQL search and return all issues (handles pagination)."""
    all_issues = []
    next_page_token = None
    while True:
        payload = {
            "jql": jql,
            "fields": fields,
            "maxResults": max_results,
        }
        if next_page_token:
            payload["nextPageToken"] = next_page_token
        resp = requests.post(
            f"{base_url}/rest/api/2/search/jql",
            auth=auth,
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
        all_issues.extend(data["issues"])
        if data.get("isLast", True):
            break
        next_page_token = data.get("nextPageToken")
        if not next_page_token:
            break
    return all_issues


def parse_quarter(quarter_str):
    """Parse quarter string like 'Q1 2026' into components.

    Returns (quarter_name, year, label, label_alt) e.g. ('Q1', '2026', '26Q1', '26_Q1')
    """
    parts = quarter_str.strip().upper().split()
    if len(parts) == 2:
        q, year = parts[0], parts[1]
    elif len(parts) == 1 and "Q" in parts[0]:
        from datetime import date
        q = parts[0]
        year = str(date.today().year)
    else:
        raise ValueError(f"Cannot parse quarter: {quarter_str}")

    yy = year[-2:]
    label = f"{yy}{q}"       # e.g. 26Q1
    label_alt = f"{yy}_{q}"  # e.g. 26_Q1
    return q, year, label, label_alt


def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <quarter> <output_dir>")
        print(f'Example: {sys.argv[0]} "Q1 2026" "80completion-outputs/2026-03-14_Q1_Epic_Report"')
        sys.exit(1)

    quarter_str = sys.argv[1]
    output_dir = sys.argv[2]

    cfg = load_config()
    jira = cfg["jira"]
    init_cfg = cfg.get("initiatives", {})
    epic_cfg = cfg.get("epics", {})

    q_name, year, label, label_alt = parse_quarter(quarter_str)
    quarter_full = f"{q_name} {year}"

    base_url = jira["url"]
    auth = HTTPBasicAuth(jira["username"], jira["api_token"])

    # Field IDs from config
    issue_type = init_cfg.get("issue_type", "Initiative")
    commit_label = init_cfg.get("commit_label", "commit")
    quarter_field_id = init_cfg.get("quarter_field_id", "12304")
    prio_field_id = init_cfg.get("prio_field_id")
    domain_field_id = init_cfg.get("domain_field_id")
    epic_type = epic_cfg.get("issue_type", "Epic")
    linked_type_name = epic_cfg.get("linked_type_name", "Epic")

    # --- Step 1: Fetch committed initiatives for the quarter ---
    jql_initiatives = (
        f'issuetype = "{issue_type}" AND labels = "{commit_label}" '
        f'AND cf[{quarter_field_id}] = "{quarter_full}"'
    )
    fields_initiatives = ["summary", "assignee", "status", "labels", "issuelinks"]
    if prio_field_id:
        fields_initiatives.append(f"customfield_{prio_field_id}")
    if domain_field_id:
        fields_initiatives.append(f"customfield_{domain_field_id}")

    print(f"Fetching committed initiatives: {jql_initiatives}")
    init_issues = jira_search(base_url, auth, jql_initiatives, fields_initiatives)
    print(f"  Found {len(init_issues)} initiatives")

    # --- Step 2: Fetch all labeled epics ---
    jql_epics = f'issuetype = "{epic_type}" AND labels in ("{label}", "{label_alt}")'
    fields_epics = ["summary", "labels", "assignee", "status"]

    print(f"Fetching labeled epics: {jql_epics}")
    epic_issues = jira_search(base_url, auth, jql_epics, fields_epics)
    print(f"  Found {len(epic_issues)} labeled epics")

    # Build labeled epic lookup
    labeled_epics = {}
    for ei in epic_issues:
        f = ei["fields"]
        assignee = f.get("assignee")
        labeled_epics[ei["key"]] = {
            "key": ei["key"],
            "summary": f.get("summary", ""),
            "labels": f.get("labels", []),
            "epic_owner": assignee.get("displayName", "-") if assignee else "-",
            "status": f.get("status", {}).get("name", "-"),
            "status_category": f.get("status", {}).get("statusCategory", {}).get("name", "-"),
        }

    # --- Step 3: Process initiatives and collect linked epics ---
    initiatives = []
    all_linked_epic_keys = set()

    for issue in init_issues:
        f = issue["fields"]
        assignee = f.get("assignee")

        prio = f.get(f"customfield_{prio_field_id}") if prio_field_id else None
        domain_field = f.get(f"customfield_{domain_field_id}") if domain_field_id else None

        # Extract linked epic keys from issue links
        linked_epic_keys = []
        for link in f.get("issuelinks") or []:
            for direction in ["inwardIssue", "outwardIssue"]:
                linked = link.get(direction)
                if not linked:
                    continue
                linked_type = linked.get("fields", {}).get("issuetype", {}).get("name", "")
                if linked_type == linked_type_name:
                    linked_epic_keys.append(linked.get("key", ""))

        all_linked_epic_keys.update(linked_epic_keys)

        initiatives.append({
            "key": issue["key"],
            "summary": f.get("summary", ""),
            "owner": assignee.get("displayName", "-") if assignee else "-",
            "prio": prio,
            "domain": domain_field.get("value", "-") if domain_field else "-",
            "status": f.get("status", {}).get("name", "-"),
            "linked_epic_keys": linked_epic_keys,
        })

    # --- Step 4: Fetch unlabeled epics (linked but not in labeled set) ---
    unlabeled_keys = all_linked_epic_keys - set(labeled_epics.keys())
    unlabeled_epics = {}

    if unlabeled_keys:
        ul_list = sorted(unlabeled_keys)
        chunk_size = 100
        for i in range(0, len(ul_list), chunk_size):
            chunk = ul_list[i : i + chunk_size]
            keys_str = ", ".join(chunk)
            jql_ul = f"key IN ({keys_str})"
            print(f"Fetching unlabeled epic details: {len(chunk)} epics (batch {i // chunk_size + 1})")
            ul_issues = jira_search(base_url, auth, jql_ul, ["summary", "status", "labels", "assignee"], max_results=100)
            for ui in ul_issues:
                uf = ui["fields"]
                assignee = uf.get("assignee")
                unlabeled_epics[ui["key"]] = {
                    "key": ui["key"],
                    "summary": uf.get("summary", ""),
                    "labels": uf.get("labels", []),
                    "epic_owner": assignee.get("displayName", "-") if assignee else "-",
                    "status": uf.get("status", {}).get("name", "-"),
                    "status_category": uf.get("status", {}).get("statusCategory", {}).get("name", "-"),
                }

    # --- Step 5: Save output ---
    os.makedirs(output_dir, exist_ok=True)
    output = {
        "quarter": quarter_full,
        "quarter_label": label,
        "quarter_label_alt": label_alt,
        "jira_url": base_url,
        "initiatives": initiatives,
        "labeled_epics": labeled_epics,
        "unlabeled_epics": unlabeled_epics,
    }

    output_path = os.path.join(output_dir, "_80completion_input.json")
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\nSaved to {output_path}")
    print(f"Initiatives: {len(initiatives)}")
    print(f"Labeled epics: {len(labeled_epics)}")
    print(f"Unlabeled epics: {len(unlabeled_epics)}")
    total_linked = sum(len(i["linked_epic_keys"]) for i in initiatives)
    print(f"Total epic links from initiatives: {total_linked}")


if __name__ == "__main__":
    main()
