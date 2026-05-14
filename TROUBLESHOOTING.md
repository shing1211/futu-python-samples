# Troubleshooting

Common issues when running Futu Python samples against OpenD gateways.

---

## Connection Problems

### "No reachable OpenD gateways"

```
RuntimeError: No reachable OpenD gateways
```

**Causes:**

- OpenD is not running on the target host/port
- Firewall blocking TCP port 11111 (or custom port)
- `FUTU_OPEND_HOSTS` has the wrong host/port/format

**Check:**

```bash
# Is OpenD actually listening?
nc -zv 172.18.208.88 11111

# Did your env file load?
python3 -c "from dotenv import load_dotenv; load_dotenv(); import os; print(os.environ.get('FUTU_OPEND_HOSTS', 'NOT SET'))"
```

**Fix:**

```bash
# .env — explicit localhost with no RSA
FUTU_OPEND_HOSTS="127.0.0.1:11111:False"
```

### "Failed to connect" after TCP probe succeeds

TCP probe passes (host is reachable) but the SDK `OpenQuoteContext()` call fails.

**Causes:**

- RSA key path is wrong or missing
- RSA is required but was skipped (`is_rsa=False` on a remote gateway)
- RSA was attempted but the key file is invalid
- OpenD is still starting up (give it 10 seconds after launch)

**Fix:**

```bash
# Verify RSA key exists and is readable
ls -la /etc/futu/keys/private_key.pem

# Make sure is_rsa flag matches your gateway config
FUTU_OPEND_HOSTS="172.18.208.88:11111:True"
```

The client auto-retries with RSA toggled (`True`→`False` or `False`→`True`) when `is_rsa=None` (the default). If you set an explicit `is_rsa`, the fallback is disabled.

### Connection succeeds but `get_global_state()` fails

The TCP handshake works, `OpenQuoteContext` is created, but the first API call crashes.

**Causes:**

- OpenD is behind a proxy that terminates SSL at a different layer
- OpenD version mismatch with the SDK (`pip show futu-api`)
- Gateway in maintenance mode

**Check SDK version:**

```bash
pip show futu-api | grep Version
# Should be 10.5.6508 or compatible
```

---

## RSA Errors

### "check sha error"

```
check sha error
```

The RSA key file doesn't match what the OpenD gateway expects.

**Fix:** Generate the correct key pair on the OpenD server and copy the private key to the path specified in `FUTU_RSA_KEY`.

### "proto encrypt not enabled"

The gateway requires RSA encryption but `SysConfig.enable_proto_encrypt(True)` was not called before connecting.

**Fix in `connect.py`:** Set `is_rsa=True` for that host in `FUTU_OPEND_HOSTS`. If using `create_quote_context()` directly, pass `is_rsa=True`.

---

## Trade / SIMULATE Account

### "unlock_trade failed: too many attempts"

```
unlock_trade failed: too many attempts
```

The gateway imposes a rate limit on password attempts (typically 5 failures = 5-minute cooldown).

**Fix:** Wait 5 minutes. Check your `FUTU_TRADE_PWD` in `.env`. The default is `123456` for SIMULATE accounts.

### "unlock_trade failed" with correct password

**Causes:**

- Using a REAL account password with a SIMULATE context (or vice versa)
- Account does not have SIMULATE trading enabled
- `filter_trdmarket` in `create_trade_context()` excludes the account's market

**Fix:** The default `filter_trdmarket=ft.TrdMarket.HK`. For multi-market accounts, pass `filter_trdmarket=ft.TrdMarket.ALL`.

### Trade API returns -1 "Unknown protocol id"

```
get_acc_cash_flow returned -1: Unknown protocol id
```

The API is not available for your account type. Some trade APIs are only available for specific brokerage firms or account tiers.

**Affected examples:** `49_acc_cash_flow`, `35_cashflow`

**Fix:** Skip these APIs if your account doesn't support them — the example handles this gracefully.

---

## Subscription & Quota

### "quota not enough"

```
subscribe failed: quota not enough
```

You've exhausted your subscription quota. The free tier typically allows 100–200 concurrent subscriptions per connection.

**Check quota:**

```python
ret, data = ctx.query_subscription(is_all_conn=True)
print(data)   # look for "total_used" and "remain"
```

**Fix:** Unsubscribe from unused stocks/subtypes before subscribing to new ones.

```python
ctx.unsubscribe_all()                     # clear everything
ctx.subscribe(code_list=["HK.00700"], subtype_list=[ft.SubType.QUOTE])
```

### Push handlers not firing

You subscribed to a subtype and registered a handler, but `on_recv_rsp()` is never called.

**Causes:**

- The market is closed (no data flowing)
- Your data permission level is too low (LV1 required for BROKER push)
- You closed the context before pushes arrived (sleep long enough)
- Multi-market: HK and US stocks require separate subscriptions on the same connection

**Check market state:**

```python
ret, state = ctx.get_market_state(["HK.00700"])
print(state)   # PRE_OPEN / OPEN / AFTER / CLOSED
```

**Check your permissions:** Run `examples/10_orderbook/main.py` — if ORDER_BOOK works but BROKER doesn't, you need LV1 data.

---

## Historical K-Line / Rate Limits

### "history kline quota exceeded"

```
get_history_kl_quota: used=500 remain=0
```

The free tier caps historical K-line requests. Quota resets daily.

**Check remaining quota:**

```bash
python3 examples/26_history_kl_quota/main.py
```

### `request_history_kline()` throttling

When fetching many bars across multiple stocks, you may hit rate limits. Add `time.sleep(0.5)` between calls or use the pagination cursor (`next_page_token`) to stay within limits.

---

## pandas / Data Issues

### `KeyError: 'close'` when accessing DataFrame column

The column name returned by the SDK may differ from what you expect. Check actual columns:

```python
ret, data = ctx.get_cur_kline("HK.00700", ...)
print(list(data.columns))
```

Common gotchas:

| Expected | Actual |
|----------|--------|
| `'name'` (in `get_plate_list`) | `'plate_name'` |
| `'period_type'` param (in `get_capital_flow`) | No such param — intraday vs daily is market-determined |
| `'BFQ'` enum (for `AuType`) | Use `'HFQ'` (no adjustment) or `'QFQ'` (adjusted) |

### `ValueError: The truth value of a DataFrame is ambiguous`

```python
if data:   # ✗ wrong
    ...
```

**Fix:**

```python
if data is not None and not data.empty:   # ✓ correct
    ...
```

### `TypeError: %d format: a real number is required, not tuple`

```python
ret = ctx.subscribe("HK.00700", ft.SubType.QUOTE)
logger.info("subscribe ret=%d", ret)   # ✗ ret is a tuple, not an int
```

**Fix:**

```python
ret, _ = ctx.subscribe("HK.00700", ft.SubType.QUOTE)
logger.info("subscribe ret=%d", ret)   # ✓ ret is a plain int
```

---

## Platform-Specific

### Windows: `sys.path.insert` not working

The path separator on Windows uses backslashes. `Path(__file__).parent.parent` handles this correctly, but if you copy the code to a notebook or IDE runner, the relative path may be wrong.

**Fix:** Run examples from the repo root:

```bash
cd futu-python-samples
python3 examples/07_kline/main.py
```

### Docker / container: OpenD not on localhost

If OpenD runs in a separate container, use the container's hostname or IP in `FUTU_OPEND_HOSTS`. Docker Compose users can use the service name:

```yaml
# docker-compose.yml
services:
  opend:
    image: futu-opend:latest
    ports:
      - "11111:11111"

  bot:
    build: .
    environment:
      - FUTU_OPEND_HOSTS=opend:11111:True
```

---

## Still Stuck?

- Open an issue at https://github.com/shing1211/futu-python-samples/issues
- Check the Futu OpenAPI docs: https://openapi.futunn.com/futu-api-doc/
- Verify SDK version: `pip show futu-api` (tested with `10.5.6508`)
