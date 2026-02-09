from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class Period:
    year: int
    quarter: int
    ic: List[Dict[str, Any]]  # income statement
    bs: List[Dict[str, Any]]  # balance sheet
    cf: List[Dict[str, Any]]  # cash flow


def _concept_value(items: List[Dict[str, Any]], concepts: List[str]) -> Optional[float]:
    if not items:
        return None
    targets = {c.lower() for c in concepts}

    # Prefer XBRL concept match
    for row in items:
        c = str(row.get("concept", "")).lower()
        if c in targets:
            v = row.get("value", None)
            try:
                return float(v) if v is not None else None
            except Exception:
                return None

    # Fallback to label match
    for row in items:
        lbl = str(row.get("label", "")).lower()
        if lbl in targets:
            v = row.get("value", None)
            try:
                return float(v) if v is not None else None
            except Exception:
                return None
    return None


def parse_periods(payload: Dict[str, Any]) -> List[Period]:
    data = (payload or {}).get("data", []) or []
    out: List[Period] = []
    for d in data:
        try:
            y = int(d.get("year"))
            q = int(d.get("quarter"))
        except Exception:
            continue
        rep = d.get("report", {}) or {}
        out.append(Period(y, q, rep.get("ic", []) or [], rep.get("bs", []) or [], rep.get("cf", []) or []))
    out.sort(key=lambda p: (p.year, p.quarter))
    return out


def last_n_quarters(periods: List[Period], n: int = 4) -> List[Period]:
    return periods[-n:] if len(periods) >= n else periods[:]


def _sum_quarters(qtrs: List[Period], stmt: str, concepts: List[str]) -> Optional[float]:
    total = 0.0
    ok = False
    for p in qtrs:
        items = getattr(p, stmt)
        v = _concept_value(items, concepts)
        if v is None:
            continue
        total += float(v)
        ok = True
    return total if ok else None


def _last_balance(qtrs: List[Period], concepts: List[str]) -> Optional[float]:
    if not qtrs:
        return None
    return _concept_value(qtrs[-1].bs, concepts)


def _avg_balance_last2(qtrs: List[Period], concepts: List[str]) -> Optional[float]:
    if not qtrs:
        return None
    if len(qtrs) == 1:
        return _concept_value(qtrs[-1].bs, concepts)
    v1 = _concept_value(qtrs[-1].bs, concepts)
    v0 = _concept_value(qtrs[-2].bs, concepts)
    if v1 is None and v0 is None:
        return None
    if v1 is None:
        return v0
    if v0 is None:
        return v1
    return (float(v0) + float(v1)) / 2.0


def build_fundamentals_from_reported(periods: List[Period]) -> Dict[str, Any]:
    """
    Build a standardized fundamentals dict for the screeners.

    Outputs keys:
      roic, operating_margin, debt_to_fcf, interest_coverage,
      current_ratio, debt_to_equity,
      plus ttm_netinc and bs_equity_avg2 (for PE/PB calc).

    Note: XBRL concept coverage differs by issuer. Missing data is expected.
    """
    qtrs = last_n_quarters(periods, 4)

    # Income TTM
    revenue_ttm = _sum_quarters(qtrs, "ic", ["Revenues", "SalesRevenueNet", "RevenueFromContractWithCustomerExcludingAssessedTax"])
    opinc_ttm   = _sum_quarters(qtrs, "ic", ["OperatingIncomeLoss", "OperatingIncome"])
    pretax_ttm  = _sum_quarters(qtrs, "ic", ["IncomeBeforeIncomeTaxes", "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItems"])
    tax_ttm     = _sum_quarters(qtrs, "ic", ["IncomeTaxExpenseBenefit"])
    netinc_ttm  = _sum_quarters(qtrs, "ic", ["NetIncomeLoss", "NetIncome"])
    interest_ttm = _sum_quarters(qtrs, "ic", ["InterestExpense", "InterestExpenseNonoperating"])

    # Cashflow TTM
    cfo_ttm = _sum_quarters(qtrs, "cf", ["NetCashProvidedByUsedInOperatingActivities", "NetCashProvidedByOperatingActivities"])
    capex = _sum_quarters(qtrs, "cf", ["PaymentsToAcquirePropertyPlantAndEquipment", "CapitalExpenditures"])
    capex_spend = abs(float(capex)) if capex is not None else None
    fcf_ttm = (float(cfo_ttm) - float(capex_spend)) if (cfo_ttm is not None and capex_spend is not None) else None

    # Balance sheet (latest / avg2)
    cash = _avg_balance_last2(qtrs, ["CashAndCashEquivalentsAtCarryingValue", "CashCashEquivalentsAndShortTermInvestments"])
    curr_assets = _last_balance(qtrs, ["AssetsCurrent"])
    curr_liab   = _last_balance(qtrs, ["LiabilitiesCurrent"])
    equity      = _avg_balance_last2(qtrs, ["StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"])
    ltd         = _avg_balance_last2(qtrs, ["LongTermDebtNoncurrent", "LongTermDebt"])
    std         = _avg_balance_last2(qtrs, ["DebtCurrent", "ShortTermBorrowings", "ShortTermDebt"])

    total_debt = None
    if ltd is not None or std is not None:
        total_debt = float(ltd or 0.0) + float(std or 0.0)

    operating_margin = (float(opinc_ttm) / float(revenue_ttm)) if (opinc_ttm is not None and revenue_ttm not in (None, 0)) else None

    interest_coverage = None
    if opinc_ttm is not None and interest_ttm not in (None, 0):
        interest_coverage = float(opinc_ttm) / abs(float(interest_ttm))

    # Tax rate for NOPAT (clamped)
    tax_rate = None
    if pretax_ttm not in (None, 0) and tax_ttm is not None:
        tr = float(tax_ttm) / float(pretax_ttm)
        tax_rate = max(0.0, min(0.5, tr))

    nopat_ttm = (float(opinc_ttm) * (1.0 - float(tax_rate))) if (opinc_ttm is not None and tax_rate is not None) else None

    invested_capital = None
    if equity is not None and total_debt is not None:
        invested_capital = float(equity) + float(total_debt) - float(cash or 0.0)

    roic = (float(nopat_ttm) / float(invested_capital)) if (nopat_ttm is not None and invested_capital not in (None, 0) and invested_capital > 0) else None

    debt_to_fcf = None
    if total_debt is not None and cash is not None and fcf_ttm is not None and fcf_ttm > 0:
        net_debt = float(total_debt) - float(cash)
        debt_to_fcf = net_debt / float(fcf_ttm)

    current_ratio = (float(curr_assets) / float(curr_liab)) if (curr_assets is not None and curr_liab not in (None, 0)) else None

    debt_to_equity = (float(total_debt) / float(equity)) if (total_debt is not None and equity not in (None, 0)) else None

    return {
        "roic": roic,
        "operating_margin": operating_margin,
        "debt_to_fcf": debt_to_fcf,
        "interest_coverage": interest_coverage,
        "current_ratio": current_ratio,
        "debt_to_equity": debt_to_equity,

        # For PE/PB calculation:
        "ttm_netinc": netinc_ttm,
        "bs_equity_avg2": equity,

        # Transparency/debug:
        "ttm_revenue": revenue_ttm,
        "ttm_opinc": opinc_ttm,
        "ttm_cfo": cfo_ttm,
        "ttm_capex_spend": capex_spend,
        "ttm_fcf": fcf_ttm,
        "bs_cash_avg2": cash,
        "bs_total_debt_avg2": total_debt,
        "invested_capital": invested_capital,
        "ttm_nopat": nopat_ttm,
    }
