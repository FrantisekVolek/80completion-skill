#!/usr/bin/env python3
"""
Build the 80% completion epic report from prefetched Jira data.

Usage:
    python3 build_report.py <input_json> <output_dir>

Reads _80completion_input.json (produced by prefetch.py) and generates the
markdown report with status breakdown, initiative groupings, and observations.
"""

import json
import os
import sys
from datetime import date


def categorize_status(status_name, status_category):
    """Categorize an epic status into Done/Cancelled/In Progress/To Do."""
    if status_name == "Cancelled":
        return "Cancelled"
    if status_category == "Done":
        return "Done"
    if status_category == "In Progress":
        return "In Progress"
    return "To Do / Backlog"


def fmt_prio(v):
    if v is None:
        return "-"
    if isinstance(v, float) and v == int(v):
        return str(int(v))
    return str(v)


def build_report(data):
    quarter = data["quarter"]
    label = data["quarter_label"]
    label_alt = data["quarter_label_alt"]
    initiatives = data["initiatives"]
    # Filter out cancelled epics — they don't count toward completion
    labeled_epics = {k: v for k, v in data["labeled_epics"].items()
                     if categorize_status(v["status"], v["status_category"]) != "Cancelled"}
    unlabeled_epics = {k: v for k, v in data["unlabeled_epics"].items()
                       if categorize_status(v["status"], v["status_category"]) != "Cancelled"}

    # Sort initiatives by prio (null last)
    initiatives.sort(key=lambda i: (i["prio"] is None, i["prio"] if i["prio"] is not None else 0))

    # --- Map epics to initiatives ---
    labeled_mapped = set()
    init_labeled = {}
    init_unlabeled = {}

    for init in initiatives:
        init_labeled[init["key"]] = []
        init_unlabeled[init["key"]] = []
        for ek in init["linked_epic_keys"]:
            if ek in labeled_epics:
                init_labeled[init["key"]].append(labeled_epics[ek])
                labeled_mapped.add(ek)
            elif ek in unlabeled_epics:
                init_unlabeled[init["key"]].append(unlabeled_epics[ek])

    unmapped = [labeled_epics[k] for k in labeled_epics if k not in labeled_mapped]

    # --- Status breakdown ---
    all_labeled = list(labeled_epics.values())
    all_unlabeled_linked = []
    for epics in init_unlabeled.values():
        all_unlabeled_linked.extend(epics)
    seen_ul = set()
    unique_unlabeled = []
    for ep in all_unlabeled_linked:
        if ep["key"] not in seen_ul:
            seen_ul.add(ep["key"])
            unique_unlabeled.append(ep)

    def count_by_status(epics):
        counts = {"Done": 0, "In Progress": 0, "To Do / Backlog": 0}
        for ep in epics:
            cat = categorize_status(ep["status"], ep["status_category"])
            if cat != "Cancelled":
                counts[cat] += 1
        return counts

    lab_counts = count_by_status(all_labeled)
    unlab_counts = count_by_status(unique_unlabeled)
    lab_total = sum(lab_counts.values())
    unlab_total = sum(unlab_counts.values())
    grand_total = lab_total + unlab_total

    def pct(n):
        if grand_total == 0:
            return "0%"
        return f"{n / grand_total * 100:.1f}%"

    # --- Build markdown ---
    lines = []
    lines.append(f"# {quarter} — 80% Completion Epic Report")
    lines.append("")
    lines.append(f"**Generated:** {date.today().isoformat()}")
    lines.append(f"**Labels searched:** `{label}`, `{label_alt}`")
    lines.append(f"**Total labeled epics:** {lab_total}")
    lines.append(f"**Total linked epics without labels:** {unlab_total}")
    lines.append(f"**Committed initiatives:** {len(initiatives)}")
    lines.append("")

    # --- Status Breakdown ---
    lines.append("## Epic Status Breakdown")
    lines.append("")
    lines.append("| Category | Count | % |")
    lines.append("| --- | --- | --- |")
    for status in ["Done", "In Progress", "To Do / Backlog"]:
        lines.append(f"| Labelled — {status} | {lab_counts[status]} | {pct(lab_counts[status])} |")
    lines.append(f"| **Labelled total** | **{lab_total}** | **{pct(lab_total)}** |")
    lines.append("| | | |")
    for status in ["Done", "In Progress", "To Do / Backlog"]:
        lines.append(f"| Unlabelled — {status} | {unlab_counts[status]} | {pct(unlab_counts[status])} |")
    lines.append(f"| **Unlabelled total** | **{unlab_total}** | **{pct(unlab_total)}** |")
    lines.append("| | | |")
    lines.append(f"| **Grand total** | **{grand_total}** | **100%** |")
    lines.append("")

    # --- Committed Initiatives ---
    lines.append("## Committed Initiatives")
    lines.append("")
    lines.append("| Prio | Initiative | Summary | Owner | Domain | Status |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for init in initiatives:
        lines.append(f"| {fmt_prio(init['prio'])} | {init['key']} | {init['summary']} | {init['owner']} | {init['domain']} | {init['status']} |")
    lines.append("")

    # --- Labeled epics by initiative ---
    lines.append("## Labeled Epics by Initiative")
    lines.append("")
    for init in initiatives:
        epics = init_labeled[init["key"]]
        if not epics:
            continue
        lines.append(f"### {init['key']}: {init['summary']}")
        lines.append(f"**Prio:** {fmt_prio(init['prio'])} | **Owner:** {init['owner']} | **Status:** {init['status']}")
        lines.append("")
        lines.append("| Prio | Initiative | Domain | Init. Owner | Epic | Summary | Labels | Epic Owner | Status |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
        for ep in epics:
            labels_str = ", ".join(ep["labels"])
            lines.append(f"| {fmt_prio(init['prio'])} | {init['key']} | {init['domain']} | {init['owner']} | {ep['key']} | {ep['summary']} | {labels_str} | {ep['epic_owner']} | {ep['status']} |")
        lines.append("")

    # --- Unlabeled linked epics ---
    lines.append("## Linked Epics Without Quarter Labels")
    lines.append("")
    has_unlabeled = False
    for init in initiatives:
        epics = init_unlabeled[init["key"]]
        if not epics:
            continue
        has_unlabeled = True
        lines.append(f"### {init['key']}: {init['summary']}")
        lines.append("")
        lines.append("| Initiative | Domain | Epic | Summary | Status |")
        lines.append("| --- | --- | --- | --- | --- |")
        for ep in epics:
            lines.append(f"| {init['key']} | {init['domain']} | {ep['key']} | {ep['summary']} | {ep['status']} |")
        lines.append("")
    if not has_unlabeled:
        lines.append("No unlabeled linked epics found.")
        lines.append("")

    # --- Unmapped labeled epics ---
    lines.append("## Epics with Unclear Initiative Mapping")
    lines.append("")
    if unmapped:
        lines.append("| Epic | Summary | Labels | Epic Owner | Status |")
        lines.append("| --- | --- | --- | --- | --- |")
        for ep in unmapped:
            labels_str = ", ".join(ep["labels"])
            lines.append(f"| {ep['key']} | {ep['summary']} | {labels_str} | {ep['epic_owner']} | {ep['status']} |")
    else:
        lines.append("All labeled epics are mapped to initiatives.")
    lines.append("")

    # --- Initiatives with no epics ---
    lines.append("## Initiatives with No Linked Epics")
    lines.append("")
    no_epics = [i for i in initiatives if not i["linked_epic_keys"]]
    if no_epics:
        for init in no_epics:
            lines.append(f"- **{init['key']}**: {init['summary']}")
    else:
        lines.append("All initiatives have at least one linked epic.")
    lines.append("")

    # --- Label observations ---
    lines.append("## Label Observations")
    lines.append("")
    label_variants = set()
    for ep in all_labeled:
        for lb in ep["labels"]:
            if label.lower() in lb.lower() or label_alt.lower() in lb.lower():
                label_variants.add(lb)
    lines.append(f"- Quarter label variants found: {', '.join(sorted(label_variants)) if label_variants else 'none'}")
    lines.append(f"- {len(unmapped)} labeled epic(s) not mapped to any committed initiative")
    no_label_count = sum(1 for i in initiatives if not init_labeled[i["key"]])
    lines.append(f"- {no_label_count} initiative(s) have no labeled epics")
    lines.append("")

    return "\n".join(lines)


def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <input_json> <output_dir>")
        sys.exit(1)

    input_path = sys.argv[1]
    output_dir = sys.argv[2]

    with open(input_path) as f:
        data = json.load(f)

    report = build_report(data)

    os.makedirs(output_dir, exist_ok=True)
    q_name = data["quarter"].split()[0]
    report_path = os.path.join(output_dir, f"{q_name}-Epic-Report.md")
    with open(report_path, "w") as f:
        f.write(report)

    print(f"Report saved: {report_path}")


if __name__ == "__main__":
    main()
