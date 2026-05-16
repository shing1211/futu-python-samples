#!/usr/bin/env python3

# Copyright (c) 2026 shing1211
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
48 — KeepAlive Handler

KeepAliveHandlerBase monitors the heartbeat between your client and OpenD.
OpenD sends periodic keep-alive packets to confirm the connection is still alive.
If you stop receiving them, the connection is dead — your push data has dried up.

Why it matters: long-running bots (overnight feeds, weekend watchers) can silently
lose their OpenD connection. Without a keep-alive monitor, you won't know until
you try to place an order and it times out. This handler gives you an early warning.

SDK: OpenQuoteContext.set_handler() + KeepAliveHandlerBase
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import time
import futu as ft
from connect import create_quote_context


class MyKeepAliveHandler(ft.KeepAliveHandlerBase):
    def on_recv_rsp(self, rsp_pb):
        ret_code, content = super().on_recv_rsp(rsp_pb)
        if ret_code != ft.RET_OK:
            return ft.RET_ERROR, content

        # content is the keep-alive payload from OpenD
        # includes connection timestamp and sequence number
        print(f"  KeepAlive received — content: {content}")
        return ft.RET_OK, content


def main():
    ctx = create_quote_context()
    try:
        ctx.set_handler(MyKeepAliveHandler())
    
        stock = "HK.00700"
    
        # Subscribe to quotes so OpenD has a reason to keep the channel active
        ret, _ = ctx.subscribe(stock, ft.SubType.QUOTE)
        if ret != 0:
            print(f"Subscribe failed: {ret}")
            return
    
        print(f"Connected to {stock} with keep-alive monitoring active.\n")
        print("Waiting 60s for keep-alive heartbeats (normally every ~30s)...\n")
    
        # Keep-alive packets arrive roughly every 30s from OpenD
        # We wait 60s to see at least one heartbeat
        time.sleep(60)
    
    finally:
        ctx.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
