# Blockhouse_QS-intern

# Smart Order Router Backtest

This project implements a Smart Order Router (SOR) that optimally splits a large order across venues using Level-1 quote data. It compares the SOR's performance against baseline strategies: Best-Ask, TWAP, and VWAP.

## Approach

At each timestamp, the router minimizes an execution cost function that includes:

- Price (ask + fee)
- Mid-price deviation (for adverse selection)
- Under/overfill penalties
- Queue risk

The router randomly samples 100 combinations of the parameters (`lambda_over`, `lambda_under`, `theta_queue`) and selects the one with the lowest average fill price.

## Parameter Ranges

The search space for the hyperparameters is:

- `lambda_over`: 0.001 – 10  
- `lambda_under`: 0.001 – 10  
- `theta_queue`: 0.001 – 10

These control trade-offs between execution cost, fill risk, and inventory accuracy.

## Improving Fill Realism

To improve realism, Level-3 data (e.g., order lifetime, cancellations) could be used to estimate fill probabilities more accurately. Prior research shows that knowing the distribution of front-of-queue cancellations and marketable orders would enhance simulation quality.

If only Level-2 data is available, incorporating order imbalance could help anticipate short-term directional pressure, leading to more adaptive and price-sensitive execution.

## Example Output

```json
{
  "smart_order_router": {
    "lambda_over": 3.4268,
    "lambda_under": 0.7187,
    "theta_queue": 6.5776,
    "total_cash_spent": 1091828.8,
    "average_fill_price": 222.8222
  },
  "best_ask": {
    "total_cash_spent": 1114112.28,
    "average_fill_price": 222.8225
  },
  "twap_60s": {
    "total_cash_spent": 1115345.58,
    "average_fill_price": 223.0691
  },
  "vwap_volume_weighted": {
    "total_cash_spent": 1115371.53,
    "average_fill_price": 223.0743
  },
  "savings_vs_baseline_bps": {
    "vs_best_ask": 200.01,
    "vs_twap_60s": 210.85,
    "vs_vwap_volume_weighted": 211.08
  }
}

