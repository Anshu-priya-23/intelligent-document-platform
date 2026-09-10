"""Preserve visual rows/columns instead of Tesseract block reading order."""
import csv
import io
from statistics import median


def spatial_rows(tsv):
    words = []
    for item in csv.DictReader(io.StringIO(tsv), delimiter="\t"):
        if item.get("level") != "5" or not item.get("text", "").strip():
            continue
        words.append({"text": item["text"], "left": int(item["left"]),
                      "top": int(item["top"]), "width": int(item["width"]), "height": int(item["height"])})
    return rows_from_words(words)


def rows_from_words(words):
    if not words:
        return [], ""
    height = median(w["height"] for w in words if w["height"] > 0)
    groups = []
    for word in sorted(words, key=lambda w: w["top"] + w["height"] / 2):
        center = word["top"] + word["height"] / 2
        if not groups or abs(center - groups[-1][0]) > height * .65:
            groups.append([center, [word]])
        else:
            groups[-1][1].append(word)
    rows = []
    for _, group in groups:
        group.sort(key=lambda w: w["left"])
        rows.append({"text": " ".join(w["text"] for w in group), "words": group})
    # Explicit row boundaries retain the paired period headings and amounts.
    return rows, "\n".join(row["text"] for row in rows)
