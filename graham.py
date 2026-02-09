from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class GrahamResult:
    passed: bool
    score: int
    reasons: List[str]


def _get(d: Dict[str, Any], key: str) -> Optional[float]:
    v = d.get(key, None)
    if v is None:
        return None
    try:
        return float(v)
    except Exception:
        return None


def graham_screen(
    fundamentals: Dict[str, Any],
    *,
    max_pe: float = 15.0,
    max_pb: float = 1.5,
    min_current_ratio: float = 1.5,
    max_debt_to_equity: float = 1.0,
) -> GrahamResult:
    """Classic value filter; missing data never crashes (reasons explain)."""
    reasons: List[str] = []
    score = 0
    ok_all = True

    pe = _get(fundamentals, "pe")
    pb = _get(fundamentals, "pb")
    cr = _get(fundamentals, "current_ratio")
    de = _get(fundamentals, "debt_to_equity")

    if pe is None:
        ok_all = False
        reasons.append("PE fehlt")
    elif 0 < pe <= max_pe:
        score += 30
        reasons.append(f"PE ok ({pe:.1f} ≤ {max_pe:.1f})")
    else:
        ok_all = False
        reasons.append(f"PE nicht ok ({pe:.1f})")

    if pb is None:
        ok_all = False
        reasons.append("PB fehlt")
    elif 0 < pb <= max_pb:
        score += 30
        reasons.append(f"PB ok ({pb:.2f} ≤ {max_pb:.2f})")
    else:
        ok_all = False
        reasons.append(f"PB nicht ok ({pb:.2f})")

    if cr is None:
        ok_all = False
        reasons.append("Current ratio fehlt")
    elif cr >= min_current_ratio:
        score += 20
        reasons.append(f"Current ratio ok ({cr:.2f} ≥ {min_current_ratio:.2f})")
    else:
        ok_all = False
        reasons.append(f"Current ratio zu niedrig ({cr:.2f} < {min_current_ratio:.2f})")

    if de is None:
        ok_all = False
        reasons.append("D/E fehlt")
    elif 0 <= de <= max_debt_to_equity:
        score += 20
        reasons.append(f"D/E ok ({de:.2f} ≤ {max_debt_to_equity:.2f})")
    else:
        ok_all = False
        reasons.append(f"D/E zu hoch ({de:.2f} > {max_debt_to_equity:.2f})")

    return GrahamResult(passed=ok_all, score=min(score, 100), reasons=reasons)
