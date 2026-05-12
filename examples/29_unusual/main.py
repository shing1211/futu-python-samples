# -*- coding: utf-8 -*-
"""异动 (get_technical_unusual / get_financial_unusual / get_derivative_unusual)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import futu as ft
from connect import create_quote_context


if __name__ == "__main__":
    ctx = create_quote_context()

    code = "HK.00700"

    print(f"=== get_technical_unusual: {code} ===")
    ret, data = ctx.get_technical_unusual(code)
    if ret == 0:
        print(data.to_string())
    else:
        print("error:", data)

    print(f"\n=== get_financial_unusual: {code} ===")
    ret, data = ctx.get_financial_unusual(code)
    if ret == 0:
        print(data.to_string())
    else:
        print("error:", data)

    print(f"\n=== get_derivative_unusual: {code} ===")
    ret, data = ctx.get_derivative_unusual(code)
    if ret == 0:
        print(data.to_string())
    else:
        print("error:", data)

    ctx.close()
