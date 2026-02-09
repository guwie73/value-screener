from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class BuffettResult:
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


def buffett_screen(
    fundamentals: Dict[str, Any],
    *,
    min_roic: float = 0.12,
    min_margin: float = 0.10,
    max_debt_to_fcf: float = 5.0,
    min_interest_coverage: float = 5.0,
) -> BuffettResult:
    """Conservative quality filter; missing data never crashes (reasons explain)."""
    reasons: List[str] = []
    score = 0
    ok_all = True

    roic = _get(fundamentals, "roic")
    margin = _get(fundamentals, "operating_margin")
    d_fcf = _get(fundamentals, "debt_to_fcf")
    icov = _get(fundamentals, "interest_coverage")

    # ROIC (35)
    if roic is None:
        ok_all = False
        reasons.append("ROIC fehlt (Datenabdeckung)")
    elif roic >= min_roic:
        score += 35
        reasons.append(f"ROIC ok ({roic:.2%} ≥ {min_roic:.2%})")
    else:
        ok_all = False
        reasons.append(f"ROIC zu niedrig ({roic:.2%} < {min_roic:.2%})")

    # Operating margin (25)
    if margin is None:
        ok_all = False
        reasons.append("Marge fehlt (Datenabdeckung)")
    elif margin >= min_margin:
        score += 25
        reasons.append(f"Marge ok ({margin:.2%} ≥ {min_margin:.2%})")
    else:
        ok_all = False
        reasons.append(f"Marge zu niedrig ({margin:.2%} < {min_margin:.2%})")

    # Debt/FCF (25)
    if d_fcf is None:
        ok_all = False
        reasons.append("Debt/FCF fehlt (FCF/NetDebt nicht verfügbar)")
    elif d_fcf <= max_debt_to_fcf:
        bonus = max(0.0, (max_debt_to_fcf - d_fcf) / max_debt_to_fcf) * 25.0
        score += int(round(bonus))
        reasons.append(f"Debt/FCF ok ({d_fcf:.2f} ≤ {max_debt_to_fcf:.2f})")
    else:
        ok_all = False
        reasons.append(f"Debt/FCF zu hoch ({d_fcf:.2f} > {max_debt_to_fcf:.2f})")

    # Interest coverage (15)
    if icov is None:
        ok_all = False
        reasons.append("Interest coverage fehlt (Zinsdaten nicht verfügbar)")
    elif icov >= min_interest_coverage:
        score += 15
        reasons.append(f"Interest coverage ok ({icov:.1f}x ≥ {min_interest_coverage:.1f}x)")
    else:
        ok_all = False
        reasons.append(f"Interest coverage zu niedrig ({icov:.1f}x < {min_interest_coverage:.1f}x)")

    return BuffettResult(passed=ok_all, score=min(score, 100), reasons=reasons)
