# Blockhouse_QS-intern

# Smart Order Router Backtest

This project implements a Smart Order Router (SOR) that optimizes how to split a marketable order across multiple venues, using Level-1 quote data.

## Approach

At each time snapshot, we simulate order routing decisions by allocating shares across venues. The allocation minimizes a cost function that accounts for:

- **Execution price (ask + fee)**
- **Mid-price deviation penalty**: Captures adverse selection
- **Underfill and overfill penalties**: Encourages hitting target quantity
- **Queue risk**: Penalizes partial fills or overfills

The SOR explores 100 random parameter combinations (`lambda_over`, `lambda_under`, `theta_queue`) and selects the one that minimizes the average fill price.

This is compared against three baseline strategies:
- **Best-Ask**: Always routes to the lowest ask
- **TWAP (Time-Weighted Average Price)**: Uniformly splits across 60-second intervals
- **VWAP (Volume-Weighted Average Price)**: Splits based on volume observed at each interval

## Parameter Ranges

Each hyperparameter is sampled from a uniform range:

- `lambda_over`: 0.001 to 10  
- `lambda_under`: 0.001 to 10  
- `theta_queue`: 0.001 to 10  

These represent trade-offs between cost, fill accuracy, and execution risk.

## Improving Fill Realism

One potential improvement is **incorporating queue position awareness**. Right now, all posted liquidity is assumed to be immediately available. In reality, orders often sit behind others in the queue. By tracking queue depth or using historical fill ratios, the model could estimate **fill probabilities**, which would better reflect true slippage and execution uncertainty.

## Example Output

When run, the script prints a single JSON object with the best parameters and performance comparisons:

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
