#!/usr/bin/env python3
"""
47 — Price Reminder Handler

PriceReminderHandlerBase receives push notifications when a price reminder
fires -- triggered by OpenD on the server side, not by polling get_price_reminder.

This means you get the alert even if your app is offline -- OpenD delivers it
the next time you connect. Much more reliable than polling.

Use this to build a real-time alert monitor or to log when your
watchlist stocks hit target prices.

SDK: OpenQuoteContext.set_handler() + PriceReminderHandlerBase
         OpenQuoteContext.set_price_reminder(code, op, key=, reminder_type=, reminder_freq=, value=, note=)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import time
import futu as ft
from connect import create_quote_context


class MyPriceReminderHandler(ft.PriceReminderHandlerBase):
    def on_recv_rsp(self, rsp_pb):
        ret_code, content = super().on_recv_rsp(rsp_pb)
        if ret_code != ft.RET_OK:
            return ft.RET_ERROR, content

        # content is a dict with fields:
        #   key: int64 reminder ID (returned as 2nd element of set_price_reminder tuple)
        #   code: stock code
        #   name: stock name
        #   trigger_time: when it fired
        #   value: the trigger value
        key          = content.get("key", "?")
        code         = content.get("code", "?")
        name         = content.get("name", "?")
        trigger_time = content.get("trigger_time", "?")
        value        = content.get("value", "?")

        print(f"  ALERT! [{code}] {name} | key={key} | "
              f"trigger_time={trigger_time} | value={value}")

        return ft.RET_OK, content


def main():
    ctx = create_quote_context()
    try:
        ctx.set_handler(MyPriceReminderHandler())
    
        stock = "HK.00700"
    
        # Set a price reminder with an unrealistic value so it won't fire during demo
        # Returns (ret_code, key) -- key is the server-assigned reminder ID
        ret, reminder_key = ctx.set_price_reminder(
            code=stock,
            op=ft.SetPriceReminderOp.ADD,
            key=0,                                           # 0 = ADD with auto ID assignment
            reminder_type=ft.PriceReminderType.PRICE_UP,     # fire when price crosses above value
            reminder_freq=ft.PriceReminderFreq.ONCE,         # fire once
            value=888888.0,                                  # unrealistic -- won't trigger in demo
            note=f"Test push alert for {stock}",
        )
        if ret != 0:
            print(f"set_price_reminder failed: ret={ret}, msg={reminder_key}")
            return
    
        print(f"Created price reminder key={reminder_key} on {stock}.")
        print("PriceReminderHandlerBase is listening for trigger events.\n")
        print("(To test: modify the reminder value to something realistic, then wait.)\n")
    
        # Query active reminders to confirm creation
        ret, reminders = ctx.get_price_reminder(stock)
        if ret == 0 and reminders is not None and not reminders.empty:
            print("Active reminders:")
            for _, r in reminders.iterrows():
                print(f"  key={r.get('key')} | {r.get('code')} | "
                      f"value={r.get('value')} | {str(r.get('note', ''))[:40]}")
    
        print("\nWaiting 10s -- listening for reminder push events...\n")
        time.sleep(10)
    
        # Clean up -- delete the test reminder
        ret, _ = ctx.set_price_reminder(
            code=stock,
            op=ft.SetPriceReminderOp.DEL,
            key=reminder_key,
        )
        print(f"\nCleaned up test reminder (key={reminder_key}) -> ret={ret}")
    
    finally:
        ctx.close()
    print("Done.")


if __name__ == "__main__":
    main()
