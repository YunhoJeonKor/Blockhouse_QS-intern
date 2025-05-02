# Blockhouse_QS-intern

Blockhouse Quant Strategist Intern Submission
This is Yunho Jeon (yj3258@nyu.edu), currently studying Mathematics in Finance at NYU.

# Smart Order Router Backtest

This project implements a Smart Order Router (SOR) that optimally splits a large order across venues using Level-1 quote data. In this case, we had single venue. It compares the SOR's performance against baseline strategies: Best-Ask, TWAP, and VWAP.  
For VWAP, the data was divided into 1-minute buckets, and weights were assigned based on observed ask sizes.

## Approach

The goal is to buy 5,000 shares before the time horizon ends using four methods: SOR, Best-Ask, TWAP, and VWAP.

At each timestamp, following the cost function proposed in the paper, the router minimizes an execution cost composed of:

- Fee
- Mid-price deviation (to account for adverse selection)
- Underfill and overfill penalties
- Queue risk

The SOR randomly samples 100 parameter combinations (`lambda_over`, `lambda_under`, `theta_queue`) and selects the one that yields the lowest execution cost.
Then compare the SOR's performance against baseline strategies based on cumulative cost.

## Parameter Ranges

The search space for the hyperparameters is sampled from uniform distributions:

- `lambda_over`: 0.001 – 10  
- `lambda_under`: 0.001 – 10  
- `theta_queue`: 0.001 – 10

These control trade-offs between execution cost, fill precision, and queue risk sensitivity.

## Suggested Improvement

To improve realism, Level-3 data (e.g., order lifetime, cancellations) could be used to estimate fill probabilities more accurately. Prior research suggests that knowing the distribution of front-of-queue cancellations and marketable orders would significantly enhance simulation realism.

In addition, incorporating order imbalance can help anticipate short-term directional pressure, allowing for more adaptive and price-aware execution strategies.

## Example Output

AS we see here, SOR outperms than the other baselines.


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



