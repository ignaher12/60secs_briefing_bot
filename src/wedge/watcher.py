from wedge.types import Brief, ComplaintTheme

def diff_briefs(old: Brief, new: Brief) -> dict:
    old_labels = {t.label: t for t in old.themes}
    new_themes_only = [t for t in new.themes if t.label not in old_labels]
    changed = []
    for t in new.themes:
        if t.label in old_labels and t.frequency != old_labels[t.label].frequency:
            changed.append({
                "label": t.label,
                "old": old_labels[t.label].frequency,
                "new": t.frequency,
                "delta": t.frequency - old_labels[t.label].frequency,
            })
    return {"new_themes": new_themes_only, "changed_frequency": changed}

def format_delta_email(idea: str, delta: dict) -> str:
    lines = [f"Weekly delta for: {idea}", ""]
    if delta["new_themes"]:
        lines.append("New themes:")
        for t in delta["new_themes"]:
            lines.append(f"  - {t.label} ({t.severity}, {t.frequency} mentions)")
    if delta["changed_frequency"]:
        lines.append("Frequency changes:")
        for d in delta["changed_frequency"]:
            arrow = "↑" if d["delta"] > 0 else "↓"
            lines.append(f"  - {d['label']}: {d['old']} → {d['new']} ({arrow}{abs(d['delta'])})")
    if not delta["new_themes"] and not delta["changed_frequency"]:
        lines.append("No changes since last week.")
    return "\n".join(lines)
