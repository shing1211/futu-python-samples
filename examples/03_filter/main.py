# -*- coding: utf-8 -*-

"""演示如何使用股票筛选功能"""

import futu as ft
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from connect import create_quote_context


def simple_financial_filter():
    """
    验证接口：条件选股功能 get_stock_filter
    这里只设置了"简单属性"和"财务属性"作为筛选条件。
    """
    quote_ctx = create_quote_context()

    # 简单属性
    simple_filter = ft.SimpleFilter()
    simple_filter.filter_min = 2
    simple_filter.filter_max = 1000
    simple_filter.stock_field = ft.StockField.CUR_PRICE
    simple_filter.is_no_filter = False
    # simple_filter.sort = SortDir.ASCEND

    # 财务属性
    financial_filter = ft.FinancialFilter()
    financial_filter.filter_min = 0.5
    financial_filter.filter_max = 50
    financial_filter.stock_field = ft.StockField.CURRENT_RATIO
    financial_filter.is_no_filter = False
    financial_filter.sort = ft.SortDir.ASCEND  # 多个筛选条件，只能有一个排序方向。
    financial_filter.quarter = ft.FinancialQuarter.ANNUAL

    # 对香港市场的股票做简单和财务筛选
    ret, ls = quote_ctx.get_stock_filter(market=ft.Market.HK,
                                         filter_list=[simple_filter, financial_filter])
    if ret == ft.RET_OK:
        last_page, all_count, ret_list = ls
        print(len(ret_list), all_count, ret_list)
        for item in ret_list:
            print(item.stock_code)  # 取股票代码
            print(item.stock_name)  # 取股票名称
            print(item[simple_filter])  # 取 simple_filter 对应的变量值
            print(item.cur_price)  # 效果同上，也是取 simple_filter 对应的变量值
            print(item[financial_filter])  # 取 financial_filter 对应的变量值
    else:
        print('error: ', ls)

    quote_ctx.close()


if __name__ == "__main__":
    simple_financial_filter()
