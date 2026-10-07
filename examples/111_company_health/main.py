import sys, logging, argparse, json, pandas as pd
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import futu as ft
from connect import create_quote_context

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

KEYWORDS = ["AI", "CLOUD", "BIOTECH", "SEMICONDUCTOR", "FINANCIAL", "BANKING", "INSURANCE", "TECHNOLOGY", "HEALTHCARE", "ENERGY", "CONSUMER"]
FAVORED_SECTORS = ["Technology", "Healthcare", "Financials", "Consumer Cyclical"]


def safe_df(result):
    if result is None:
        return pd.DataFrame()
    if isinstance(result, tuple) and len(result) == 2 and result[1] is None:
        return pd.DataFrame()
    ret = result[0]
    if ret != 0:
        return None
    df = result[1]
    if df is None or df.empty:
        return None
    return df


def safe_dict(result):
    if result is None:
        return None
    ret = result[0]
    if ret != 0:
        return None
    data = result[1]
    if not isinstance(data, dict):
        return None
    return data


def score_management(exec_df):
    score = 0
    if exec_df is None or exec_df.empty:
        return 0, "No executive data"

    details = []
    ages = []
    has_cfo = False
    for _, row in exec_df.iterrows():
        pos = str(row.get("position_name", ""))
        age = row.get("leader_age", 0)
        if age:
            ages.append(int(age))
        if "CFO" in pos.upper() or "CHIEF FINANCIAL" in pos.upper():
            has_cfo = True

    if len(exec_df) >= 3:
        score += 5
        details.append("3+ exec listed")
    if len(exec_df) >= 5:
        score += 5
    if ages:
        avg_age = sum(ages) / len(ages)
        if 45 <= avg_age <= 60:
            score += 5
            details.append(f"Avg age {avg_age:.0f}")
    if has_cfo:
        score += 5
        details.append("CFO present")
    if len(exec_df) <= 12:
        score += 5
        details.append("Board size OK")

    return min(score, 25), "; ".join(details) if details else "Basic"


def score_efficiency(ops_data):
    score = 0
    if ops_data is None:
        return 0, "No data"

    details = []

    roe_data = ops_data.get("roe", ops_data.get("return_on_equity", 0))
    if isinstance(roe_data, (int, float)) and roe_data > 0:
        if roe_data > 15:
            score += 10
            details.append(f"ROE={roe_data:.1f}%")
        elif roe_data > 8:
            score += 5
            details.append(f"ROE={roe_data:.1f}%")

    op_margin = ops_data.get("operating_margin", ops_data.get("operating_profit_margin", 0))
    if isinstance(op_margin, (int, float)) and op_margin > 0:
        if op_margin > 20:
            score += 10
            details.append(f"OpMargin={op_margin:.1f}%")
        elif op_margin > 10:
            score += 5
            details.append(f"OpMargin={op_margin:.1f}%")

    if isinstance(roe_data, (int, float)) and isinstance(op_margin, (int, float)):
        if roe_data > 0 and op_margin > 0:
            score += 5

    return min(score, 25), "; ".join(details) if details else "Basic"


def score_financial(fin_data):
    score = 0
    if fin_data is None:
        return 0, "No data"

    details = []
    stmts = fin_data.get("income_statement", fin_data.get("financial_statement_list", []))
    if not stmts:
        return 0, "No statements"

    stmt = stmts[0] if isinstance(stmts, list) else stmts
    if not isinstance(stmt, dict):
        return 0, "No statements"

    revenue = float(stmt.get("revenue", stmt.get("total_revenue", 0)))
    net_profit = float(stmt.get("net_profit", stmt.get("netProfit", 0)))
    total_assets = float(stmt.get("total_assets", 0))
    total_liabilities = float(stmt.get("total_liabilities", 0))

    if revenue > 0 and net_profit > 0:
        profit_margin = net_profit / revenue * 100
        if profit_margin > 15:
            score += 8
            details.append(f"Margin={profit_margin:.1f}%")
        elif profit_margin > 5:
            score += 4
            details.append(f"Margin={profit_margin:.1f}%")

    if total_assets > 0:
        de_ratio = total_liabilities / total_assets
        if de_ratio < 0.5:
            score += 9
            details.append(f"D/E={de_ratio:.2f}")
        elif de_ratio < 1.0:
            score += 5
            details.append(f"D/E={de_ratio:.2f}")

    if net_profit > 0:
        score += 8
        details.append("Profitable")

    return min(score, 25), "; ".join(details) if details else "Basic"


def score_profile(prof_df):
    score = 0
    if prof_df is None or prof_df.empty:
        return 0, "No data"

    details = []
    prof_dict = {}
    for _, row in prof_df.iterrows():
        k = str(row.get("name", "")).strip()
        v = row.get("value", "")
        prof_dict[k] = v

    employees = prof_dict.get("employees", prof_dict.get("员工人数", "0"))
    try:
        emp_count = int(employees) if employees else 0
        if emp_count > 10000:
            score += 5
            details.append(f"{emp_count:,} employees")
        elif emp_count > 1000:
            score += 3
    except (ValueError, TypeError):
        pass  # static-checks: allow-suppress -- optional numeric field absent or unparsable; score skips this adjustment

    desc = str(prof_dict.get("business_description", prof_dict.get("description", ""))).upper()
    keyword_hits = 0
    for kw in KEYWORDS:
        if kw in desc:
            keyword_hits += 1
    if keyword_hits >= 3:
        score += 10
        details.append(f"Growth keywords ({keyword_hits})")
    elif keyword_hits >= 1:
        score += 5
        details.append(f"Sector keywords ({keyword_hits})")

    industry = str(prof_dict.get("industry", prof_dict.get("industry_name", "")))
    if industry in FAVORED_SECTORS:
        score += 10
        details.append(f"{industry} (favored)")

    return min(score, 25), "; ".join(details) if details else "Basic"


def letter_grade(score):
    if score >= 80:
        return "A"
    if score >= 60:
        return "B"
    if score >= 40:
        return "C"
    if score >= 20:
        return "D"
    return "F"


def main():
    parser = argparse.ArgumentParser(description="Company Health Score")
    parser.add_argument("--code", default="US.NVDA", help="Stock code")
    args = parser.parse_args()
    code = args.code

    ctx = create_quote_context()

    try:
        exec_df = safe_df(ctx.get_company_executives(code))
        prof_df = safe_df(ctx.get_company_profile(code))
        ops_data = safe_dict(ctx.get_company_operational_efficiency(code))
        fin_data = safe_dict(ctx.get_financials_statements(code, 0, 0))

        mgmt_score, mgmt_detail = score_management(exec_df)
        eff_score, eff_detail = score_efficiency(ops_data)
        fin_score, fin_detail = score_financial(fin_data)
        prof_score, prof_detail = score_profile(prof_df)

        total = mgmt_score + eff_score + fin_score + prof_score
        grade = letter_grade(total)

        print(f"\n  === COMPANY HEALTH SCORE: {code} ===\n")
        print(f"  {'Dimension':<24} {'Score':<8} {'Max':<8} {'Details'}")
        print(f"  {'-'*24} {'-'*8} {'-'*8} {'-'*30}")
        print(f"  {'Management Quality':<24} {mgmt_score:<8} 25    {mgmt_detail}")
        print(f"  {'Operational Efficiency':<24} {eff_score:<8} 25    {eff_detail}")
        print(f"  {'Financial Health':<24} {fin_score:<8} 25    {fin_detail}")
        print(f"  {'Company Profile':<24} {prof_score:<8} 25    {prof_detail}")
        print(f"  {'-'*70}")
        print(f"  {'TOTAL':<24} {total:<8} 100   GRADE: {grade}")

        bar_len = 20
        for name, score, max_score in [
            ("Mgmt", mgmt_score, 25),
            ("Efficiency", eff_score, 25),
            ("Financial", fin_score, 25),
            ("Profile", prof_score, 25),
        ]:
            filled = int(score / max_score * bar_len) if max_score > 0 else 0
            bar = "█" * filled + "░" * (bar_len - filled)
            print(f"  {name:<12} {bar} {score}/{max_score}")

    finally:
        ctx.close()


if __name__ == "__main__":
    main()
