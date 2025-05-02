# smart_order_router.py

import pandas as pd
import random
import matplotlib.pyplot as plt
import json

# Constants
ORDER_SIZE = 5000
FEE = 0.002
REBATE = 0.0015
STEP = 100  # 100-share chunks

def load_snapshots(csv_path, fee=0.002, rebate=0.0015):
    df = pd.read_csv(csv_path)
    df['ts_event'] = pd.to_datetime(df['ts_event'])
    df = df.sort_values('ts_event')
    df_cleaned = df.groupby(['ts_event', 'publisher_id']).first().reset_index()

    snapshots = []
    for ts, group in df_cleaned.groupby('ts_event'):
        venues = []
        for _, row in group.iterrows():
            venues.append({
                'ask': row['ask_px_00'],
                'ask_size': int(row['ask_sz_00']),
                'mid_price': row['price'],
                'fee': fee,
                'rebate': rebate,
                'ts_event': row['ts_event']
            })
        snapshots.append(venues)
    return snapshots

def compute_cost(split, venues, order_size, lambda_over, lambda_under, theta_queue):
    executed = 0
    cash_spent = 0

    for i in range(len(venues)):
        order = split[i]
        venue = venues[i]
        executed_here = min(order, venue['ask_size'])
        executed += executed_here
        cash_spent += executed_here * (venue['ask'] - venue['mid_price'] + venue['fee'])
        rebate = max(order - executed_here, 0) * venue['rebate']
        cash_spent -= rebate

    underfill = max(order_size - executed, 0)
    overfill = max(executed - order_size, 0)
    risk_penalty = theta_queue * (underfill + overfill)
    cost_penalty = lambda_under * underfill + lambda_over * overfill
    return cash_spent + risk_penalty + cost_penalty

def allocate(order_size, venues, lambda_over, lambda_under, theta_queue):
    step = STEP
    splits = [[]]

    for v in range(len(venues)):
        new_splits = []
        for alloc in splits:
            used = sum(alloc)
            remaining = order_size - used
            max_q = min(remaining, venues[v]['ask_size'])
            for q in range(0, max_q, step):
                new_splits.append(alloc + [q])
        splits = new_splits

    best_cost = float('inf')
    best_split = None
    for split in splits:
        cost = compute_cost(split, venues, order_size, lambda_over, lambda_under, theta_queue)
        if cost < best_cost:
            best_cost = cost
            best_split = split
    return best_split, best_cost

def best_ask_strategy(snapshots, order_size):
    fill = 0
    total_cash = 0
    fill_log = []

    for snapshot in snapshots:
        best_venue = min(snapshot, key=lambda x: x['ask'])
        available = best_venue['ask_size']
        price = best_venue['ask']
        fee = best_venue['fee']
        ts = best_venue['ts_event']

        take = min(order_size - fill, available)
        if take <= 0:
            break

        cost = take * (price + fee)
        total_cash += cost
        fill += take

        fill_log.append({
            'timestamp': ts,
            'filled_qty': take,
            'price': price,
            'fee': fee,
            'cost': cost,
            'cumulative_fill': fill,
            'cumulative_cost': total_cash
        })

        if fill >= order_size:
            break

    avg_price = total_cash / fill if fill > 0 else float('inf')
    return total_cash, avg_price, fill, fill_log

def twap_60s_fill_all_snapshots_with_timestamps(snapshots, order_size):
    ts_list = [snap[0]['ts_event'] for snap in snapshots]
    df = pd.DataFrame({'ts': ts_list})
    df['bucket'] = df['ts'].dt.floor('60S')
    buckets = df['bucket'].unique()
    per_bucket = order_size // len(buckets)

    fill = 0
    total_cash = 0
    timestamps_filled = []

    for b in buckets:
        idxs = df[df['bucket'] == b].index
        remaining = per_bucket
        for idx in idxs:
            snapshot = snapshots[idx]
            venue = snapshot[0]
            ts = venue['ts_event']
            take = min(venue['ask_size'], remaining, order_size - fill)

            if take > 0:
                total_cash += take * (venue['ask'] + venue['fee'])
                fill += take
                remaining -= take
                timestamps_filled.append((ts, take))

            if fill >= order_size or remaining <= 0:
                break
        if fill >= order_size:
            break

    avg_price = total_cash / fill if fill > 0 else float('inf')
    return total_cash, avg_price, timestamps_filled


def vwap_strategy_by_volume_weight(snapshots, order_size):
    ts_list = [snap[0]['ts_event'] for snap in snapshots]
    df = pd.DataFrame({'ts': ts_list})
    df['bucket'] = df['ts'].dt.floor('60S')
    buckets = sorted(df['bucket'].unique())

    volume_by_bucket = {}
    snapshot_map = {}

    for i, snap in enumerate(snapshots):
        ts = snap[0]['ts_event']
        bucket = ts.floor('60S')
        volume = snap[0]['ask_size']

        volume_by_bucket[bucket] = volume_by_bucket.get(bucket, 0) + volume
        snapshot_map.setdefault(bucket, []).append(snap[0])

    total_volume = sum(volume_by_bucket.values())
    if total_volume == 0:
        return 0, float('inf'), pd.DataFrame([])

    fill = 0
    total_cash = 0
    fill_log = []
    allocated_so_far = 0

    for i, bucket in enumerate(buckets):
        bucket_volume = volume_by_bucket[bucket]
        bucket_share = bucket_volume / total_volume

        if i == len(buckets) - 1:
            bucket_target = order_size - allocated_so_far
        else:
            bucket_target = int(order_size * bucket_share)
            allocated_so_far += bucket_target

        venues = snapshot_map[bucket]
        for venue in venues:
            to_fill = min(venue['ask_size'], bucket_target, order_size - fill)
            if to_fill <= 0:
                continue

            total_cash += to_fill * (venue['ask'] + venue['fee'])
            fill += to_fill
            bucket_target -= to_fill

            fill_log.append({
                'timestamp': venue['ts_event'],
                'filled_qty': to_fill,
                'price': venue['ask'],
                'fee': venue['fee'],
                'cost': to_fill * (venue['ask'] + venue['fee']),
                'cumulative_fill': fill,
                'cumulative_cost': total_cash
            })

            if fill >= order_size:
                break
        if fill >= order_size:
            break

    avg_price = total_cash / fill if fill > 0 else float('inf')
    fill_log_df = pd.DataFrame(fill_log)
    return total_cash, avg_price, fill_log_df


def compute_sor_result(snapshots, num_trials=100, param_bounds=None):
    if param_bounds is None:
        param_bounds = {
            'lambda_over': (0.001, 10),
            'lambda_under': (0.001, 10),
            'theta_queue': (0.001, 10),
        }

    best_fill_price = float('inf')
    best_params = None
    best_total_cash = None

    for _ in range(num_trials):
        λo = random.uniform(*param_bounds['lambda_over'])
        λu = random.uniform(*param_bounds['lambda_under'])
        θq = random.uniform(*param_bounds['theta_queue'])

        fill = 0
        total_cash = 0

        for snapshot in snapshots:
            remaining = ORDER_SIZE - fill
            if remaining <= 0:
                break

            split, _ = allocate(remaining, snapshot, λo, λu, θq)

            for i, qty in enumerate(split):
                exe = min(qty, snapshot[i]['ask_size'])
                take = min(exe, ORDER_SIZE - fill)
                total_cash += take * (snapshot[i]['ask'] + snapshot[i]['fee'])
                fill += take
                if fill >= ORDER_SIZE:
                    break

            if fill >= ORDER_SIZE:
                break

        fill_price = total_cash / fill if fill > 0 else float('inf')
        if fill_price < best_fill_price:
            best_fill_price = fill_price
            best_params = (λo, λu, θq)
            best_total_cash = total_cash

    return best_params, best_total_cash, best_fill_price


def main():
    snapshots = load_snapshots("l1_day.csv")

    # --- Smart Order Router ---
    best_params, sor_cost, sor_price = compute_sor_result(snapshots)

    # --- Baselines ---
    baselines = {}
    for name, func in {
        "best_ask": best_ask_strategy,
        "twap_60s": twap_60s_fill_all_snapshots_with_timestamps,
        "vwap_volume_weighted": vwap_strategy_by_volume_weight
    }.items():
        total_cost, avg_price, *_ = func(snapshots, ORDER_SIZE)
        baselines[name] = {
            "total_cash_spent": round(total_cost, 2),
            "average_fill_price": round(avg_price, 4)
        }

    # --- Result JSON ---
    result = {
        "smart_order_router": {
            "lambda_over": round(best_params[0], 4),
            "lambda_under": round(best_params[1], 4),
            "theta_queue": round(best_params[2], 4),
            "total_cash_spent": round(sor_cost, 2),
            "average_fill_price": round(sor_price, 4)
        },
        **baselines,
        "savings_vs_baseline_bps": {
            f"vs_{name}": round((baseline["total_cash_spent"] - sor_cost) / baseline["total_cash_spent"] * 10000, 2)
            for name, baseline in baselines.items()
        }
    }

    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
