#!/usr/bin/env python3
"""
43 — Subscribe Lifecycle

The full subscription management cycle:
  1. subscribe (batch) — add stocks + subtypes
  2. query_subscription — check quota usage
  3. unsubscribe — remove specific subscriptions
  4. unsubscribe_all — blow it all away

Why it matters: push handlers accumulate subscriptions. Forgetting to
unsubscribe is a common cause of stale data and quota exhaustion in bots.

SDK: OpenQuoteContext.subscribe(code_list, subtype_list)
                   unsubscribe / unsubscribe_all
                   query_subscription(is_all_conn=True)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import futu as ft
from connect import create_quote_context


def get_quota(ctx):
    """Return (total_used, remain) from query_subscription quota dict."""
    ret, data = ctx.query_subscription(is_all_conn=True)
    if ret != 0:
        return None, None
    if isinstance(data, dict):
        return data.get("total_used"), data.get("remain")
    return None, None


def main():
    ctx = create_quote_context()

    stocks    = ["HK.00700", "HK.09988", "HK.03690"]
    subtypes  = [ft.SubType.QUOTE, ft.SubType.ORDER_BOOK]

    # ── 1. Batch subscribe ─────────────────────────────────────────
    print("=== SUBSCRIBE (batch) ===")
    used_before, _ = get_quota(ctx)

    ret, _ = ctx.subscribe(code_list=stocks, subtype_list=subtypes)
    print(f"  subscribe({len(stocks)} stocks, {len(subtypes)} subtypes) -> ret={ret}")

    used_after, remain = get_quota(ctx)
    delta = (used_after - used_before) if used_before else None
    print(f"  Quota: used={used_after}, remain={remain} (delta={delta:+d})")

    # ── 2. Add more subtypes ─────────────────────────────────────
    print("\n=== ADD MORE SUBTYPES ===")
    used_before = used_after
    ret, _ = ctx.subscribe(code_list=["HK.00700"], subtype_list=[ft.SubType.TICKER])
    print(f"  subscribe(HK.00700, TICKER) -> ret={ret}")
    used_after, remain = get_quota(ctx)
    print(f"  Quota: used={used_after}, remain={remain} (delta={used_after - used_before:+d})")

    # ── 3. Unsubscribe specific ───────────────────────────────────
    print("\n=== UNSUBSCRIBE SPECIFIC ===")
    used_before = used_after
    ret, _ = ctx.unsubscribe(code_list=["HK.09988"], subtype_list=[ft.SubType.QUOTE])
    print(f"  unsubscribe(HK.09988, QUOTE) -> ret={ret}")
    used_after, remain = get_quota(ctx)
    print(f"  Quota: used={used_after}, remain={remain} (delta={used_after - used_before:+d})")

    # ── 4. Unsubscribe all ──────────────────────────────────────
    print("\n=== UNSUBSCRIBE ALL ===")
    used_before = used_after
    ret, _ = ctx.unsubscribe_all()
    print(f"  unsubscribe_all() -> ret={ret}")
    used_after, remain = get_quota(ctx)
    print(f"  Quota: used={used_after}, remain={remain} (delta={used_after - used_before:+d})")

    ctx.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
