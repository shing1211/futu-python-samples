# 59 — Dark Pool / Block Trade Detector

Cross-references TICKER prints against BROKER queue depth. When a large trade occurs without a corresponding queue reduction at that price, flags it as potential off-book execution.

**SDK APIs used:** `TickerHandlerBase`, `BrokerHandlerBase`, `subscribe(TICKER, BROKER)`

**Risk:** None — read-only. Requires LV1 data permission for BROKER feed (gracefully degrades without it).

```bash
python3 examples/59_dark_pool_detector/main.py
```
