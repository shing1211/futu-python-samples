# 80 — Multi-Leg Options Strategy Execution

**Category**: Execution Strategy (SIMULATE)

Builds and executes multi-leg options strategies (straddle, strangle, iron condor) using the Futu options API. All legs are placed together with market orders and monitored for fills.

## Strategies

| Strategy | Legs | Profit When |
|----------|------|-------------|
| **Straddle** | Long 1 ATM Call + Long 1 ATM Put | Large move in either direction |
| **Strangle** | Long 1 OTM Call + Long 1 OTM Put | Large move (cheaper than straddle) |
| **Iron Condor** | Short call spread + Short put spread | Price stays within inner strikes |

## How It Works

1. Fetches current price for the underlying stock.
2. Searches option chain for matching contracts via `get_option_chain`.
3. Builds strategy legs with hedge ratios.
4. Places all legs simultaneously with market orders.
5. Monitors fill status until all legs filled or timeout.
6. `cancel_all_order` in `finally`.

## Usage

```bash
python3 main.py --strategy straddle --stock HK.00700
python3 main.py --strategy iron_condor --stock HK.00700 --expiry 202606
```

## Key Concepts Demonstrated

- `get_option_chain` with pagination
- Multi-leg order placement
- Strategy pattern (register/dispatch)
- Market order execution on options
- SIMULATE-only with proper cleanup

## Configuration

| Flag | Default | Description |
|------|---------|-------------|
| `--strategy` | `straddle` | Strategy: straddle, strangle, iron_condor |
| `--stock` | `HK.00700` | Underlying stock |
| `--expiry` | `""` (first available) | Expiry in YYYYMM format |
| `--max-minutes` | `10` | Safety timeout |