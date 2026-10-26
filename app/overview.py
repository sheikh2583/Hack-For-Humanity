"""Overview statistics and accessible bar markup (module P3).

Input schema: the prepared kiln frame with ``district``, ``upazila``,
``priority_band`` and ``class``/``class_name`` columns (any may be missing).
Output schema: small pandas tables (``district_stats``, ``upazila_stats``), a
list of ``(type, count)`` pairs (``type_split``) and escaped HTML strings built from
already-translated labels. No Streamlit import, so it is unit-testable. Every number is
a plain groupby/count of the frame; nothing is estimated and there is no time series.
"""

from __future__ import annotations

import html
from collections.abc import Mapping, Sequence

import pandas as pd

HIGH_GLYPH = "▲"  # same glyph as design_tokens.PRIORITY["High"]
TYPE_ORDER: tuple[str, ...] = ("Zigzag", "FCBK", "other")


def _clean(series: pd.Series) -> pd.Series:
    """Strip text values; blanks and missing become NA."""
    text = series.astype("string").str.strip()
    return text.mask(text.eq(""))


def district_stats(frame: pd.DataFrame) -> pd.DataFrame:
    """Per-district candidate counts.

    Input: kiln frame. Output: columns ``district``, ``total``, ``high``, ``medium``,
    ``low`` (ints), ranked by ``total`` desc, then ``high`` desc, then name. Rows
    without a district are left out (they are not assigned to any bar).
    """
    columns = ["district", "total", "high", "medium", "low"]
    if "district" not in frame:
        return pd.DataFrame(columns=columns).astype({c: "int64" for c in columns[1:]})
    work = pd.DataFrame({"district": _clean(frame["district"])})
    band = frame["priority_band"].astype(str) if "priority_band" in frame else pd.Series("", index=frame.index)
    work["high"] = band.eq("High").to_numpy()
    work["medium"] = band.eq("Medium").to_numpy()
    work["low"] = band.eq("Low").to_numpy()
    work = work.dropna(subset=["district"])
    grouped = work.groupby("district", sort=False).agg(
        total=("district", "size"), high=("high", "sum"), medium=("medium", "sum"), low=("low", "sum")
    )
    result = grouped.reset_index().astype({c: "int64" for c in columns[1:]})
    return result.sort_values(["total", "high", "district"], ascending=[False, False, True],
                              kind="stable").reset_index(drop=True)[columns]


def public_district_counts(frame: pd.DataFrame) -> pd.DataFrame:
    """Per-district candidate counts for the public Overview: columns ``district``, ``total``.

    Input: the PUBLIC kiln frame. Output: districts ranked by ``total`` desc then name; rows
    without a district are left out. It never reads a priority column, so it is safe to call
    on any frame and has no ``high`` series.
    """
    columns = ["district", "total"]
    if "district" not in frame:
        return pd.DataFrame(columns=columns).astype({"total": "int64"})
    names = _clean(frame["district"]).dropna()
    counts = names.groupby(names, sort=False).size().rename("total").reset_index()
    counts.columns = columns
    counts["total"] = counts["total"].astype("int64")
    return counts.sort_values(["total", "district"], ascending=[False, True],
                              kind="stable").reset_index(drop=True)


def public_district_bar_html(total: int, maximum: int, total_label: str) -> str:
    """One labelled bar (all candidates) for a district row on the public Overview."""
    total = int(total)
    return (
        "<div class='dhoa-bar-block'>"
        "<div class='dhoa-bar-line'>"
        f"<span class='dhoa-bar dhoa-bar-total' style='width:{bar_width(total, maximum)}%' "
        f"role='img' aria-label='{html.escape(total_label, quote=True)}: {total:,}'></span>"
        f"<span class='dhoa-bar-value'>{total:,}</span></div>"
        "</div>"
    )


def upazila_stats(frame: pd.DataFrame, limit: int = 10) -> pd.DataFrame:
    """Top ``limit`` upazilas by candidate count.

    Output columns: ``upazila``, ``district``, ``total``, ``high``; ranked by ``total``
    desc, ``high`` desc, upazila, district. An upazila name used in two districts stays
    two rows. Rows without an upazila are left out.
    """
    columns = ["upazila", "district", "total", "high"]
    if "upazila" not in frame:
        return pd.DataFrame(columns=columns).astype({"total": "int64", "high": "int64"})
    work = pd.DataFrame({
        "upazila": _clean(frame["upazila"]),
        "district": _clean(frame["district"]) if "district" in frame else pd.Series(pd.NA, index=frame.index, dtype="string"),
        "high": (frame["priority_band"].astype(str).eq("High").to_numpy() if "priority_band" in frame else False),
    }).dropna(subset=["upazila"])
    work["district"] = work["district"].fillna("")
    grouped = work.groupby(["upazila", "district"], sort=False).agg(
        total=("upazila", "size"), high=("high", "sum")
    ).reset_index().astype({"total": "int64", "high": "int64"})
    ranked = grouped.sort_values(["total", "high", "upazila", "district"],
                                 ascending=[False, False, True, True], kind="stable")
    return ranked.head(max(int(limit), 0)).reset_index(drop=True)[columns]


def type_split(frame: pd.DataFrame) -> list[tuple[str, int]]:
    """Counts of ``Zigzag`` and ``FCBK`` kilns, plus ``other`` for anything else/missing.

    Output: ``(type, count)`` pairs in ``TYPE_ORDER``, zero counts dropped; counts add up
    to ``len(frame)``.
    """
    column = "class" if "class" in frame else ("class_name" if "class_name" in frame else None)
    if column is None:
        return [("other", int(len(frame)))] if len(frame) else []
    values = frame[column].astype("string").str.strip()
    counts = {
        "Zigzag": int(values.eq("Zigzag").sum()),
        "FCBK": int(values.eq("FCBK").sum()),
    }
    counts["other"] = int(len(frame)) - counts["Zigzag"] - counts["FCBK"]
    return [(name, counts[name]) for name in TYPE_ORDER if counts[name] > 0]


def bar_width(value: int, maximum: int) -> float:
    """Bar width in percent (0-100, one decimal); 0 when ``maximum`` is not positive."""
    if maximum <= 0 or value <= 0:
        return 0.0
    return round(min(100.0, 100.0 * value / maximum), 1)


def bars_legend_html(total_label: str, high_label: str) -> str:
    """Legend: a plain bar for all candidates and a triangle for High priority."""
    return (
        "<div class='dhoa-bar-legend'>"
        f"<span><i class='dhoa-key dhoa-key-total' aria-hidden='true'></i>{html.escape(total_label)}</span>"
        f"<span><i class='dhoa-key dhoa-key-high' aria-hidden='true'>{HIGH_GLYPH}</i>{html.escape(high_label)}</span>"
        "</div>"
    )


def district_bar_html(row: Mapping[str, int | str], maximum: int, total_label: str, high_label: str) -> str:
    """Two directly-labelled bars (all candidates, High priority) for one district row.

    Input: a ``district_stats`` row, the largest ``total`` (the shared scale), and
    translated series labels. Output: escaped HTML. Values are printed as text at
    the end of each bar, so nothing depends on colour or on reading an axis.
    """
    total, high = int(row["total"]), int(row["high"])
    return (
        "<div class='dhoa-bar-block'>"
        "<div class='dhoa-bar-line'>"
        f"<span class='dhoa-bar dhoa-bar-total' style='width:{bar_width(total, maximum)}%' "
        f"role='img' aria-label='{html.escape(total_label, quote=True)}: {total:,}'></span>"
        f"<span class='dhoa-bar-value'>{total:,}</span></div>"
        "<div class='dhoa-bar-line'>"
        f"<span class='dhoa-bar dhoa-bar-high' style='width:{bar_width(high, maximum)}%' "
        f"role='img' aria-label='{html.escape(high_label, quote=True)}: {high:,}'></span>"
        f"<span class='dhoa-bar-value dhoa-bar-value-high'>{HIGH_GLYPH} {high:,}</span></div>"
        "</div>"
    )


def type_split_html(parts: Sequence[tuple[str, int]], labels: Mapping[str, str], share_format: str) -> str:
    """Stacked share bar plus a direct-label legend for the kiln-type split.

    Input: ``type_split`` pairs, translated ``labels`` per type key and a
    ``{0}``/``{1}`` format (label, percent). Output: escaped HTML; each segment is also
    named in the legend text with its count and share, with a different fill pattern
    per type so it is not colour only.
    """
    total = sum(count for _, count in parts)
    if total <= 0:
        return ""
    segments, legend = [], []
    for name, count in parts:
        percent = 100.0 * count / total
        label = html.escape(labels.get(name, name))
        css = f"dhoa-split-{name.lower()}"
        segments.append(f"<span class='dhoa-split-seg {css}' style='width:{percent:.1f}%'></span>")
        legend.append(
            f"<li><i class='dhoa-split-key {css}' aria-hidden='true'></i>"
            f"<span>{label}</span> <strong>{count:,}</strong> "
            f"<span class='dhoa-split-share'>({html.escape(share_format.format(percent))})</span></li>"
        )
    return (
        "<div class='dhoa-split'><div class='dhoa-split-bar' role='presentation'>"
        + "".join(segments) + "</div><ul class='dhoa-split-legend'>" + "".join(legend) + "</ul></div>"
    )
