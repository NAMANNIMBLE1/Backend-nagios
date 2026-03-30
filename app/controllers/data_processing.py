import pandas as pd
import numpy as np
from db.db_connection import get_sql_data
import re


def parse_perfdata(perfdata_str: str) -> dict:
    """
    Parses Nagios perfdata string into a dict of numeric values.
    Example input:
      'power=1240W;1500;1800;0;2000 cooling_capacity=85%;90;95;0;100'
    Output:
      {'power': 1240.0, 'cooling_capacity': 85.0}
    """
    result = {}
    if not perfdata_str or pd.isna(perfdata_str):
        return result

    # Each metric is: label=value[unit][;warn;crit;min;max]
    pattern = r"([\w\-]+)=([\d.]+)"
    matches = re.findall(pattern, str(perfdata_str))
    for key, val in matches:
        try:
            result[key] = float(val)
        except ValueError:
            pass
    return result



def build_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df['check_time'] = pd.to_datetime(df['check_time'])
    df = df.sort_values('check_time').reset_index(drop=True)

    # ── Parse perfdata into columns ──
    parsed = df['perf_data'].apply(parse_perfdata)
    perf_df = pd.json_normalize(parsed)
    df = pd.concat([df, perf_df], axis=1)

    # Print discovered metric columns
    metric_cols = perf_df.columns.tolist()
    print(f"[INFO] Parsed perfdata columns: {metric_cols}")

    # ── Time-based features ──
    df['hour']          = df['check_time'].dt.hour
    df['minute']        = df['check_time'].dt.minute
    df['day_of_week']   = df['check_time'].dt.dayofweek   # 0=Mon, 6=Sun
    df['day_of_month']  = df['check_time'].dt.day
    df['is_weekend']    = (df['day_of_week'] >= 5).astype(int)

    # ── Time index (numeric) for linear trend ──
    df['time_index'] = (
        df['check_time'] - df['check_time'].min()
    ).dt.total_seconds() / 3600  # hours since first check

    # ── Lag features (previous values) ──
    for col in metric_cols:
        df[f'{col}_lag1']  = df[col].shift(1)   # 5 min ago
        df[f'{col}_lag3']  = df[col].shift(3)   # 15 min ago
        df[f'{col}_lag6']  = df[col].shift(6)   # 30 min ago
        df[f'{col}_lag12'] = df[col].shift(12)  # 1 hour ago

        # ── Rolling statistics ──
        df[f'{col}_roll_mean_12'] = df[col].rolling(12).mean()  # 1hr avg
        df[f'{col}_roll_std_12']  = df[col].rolling(12).std()   # 1hr volatility
        df[f'{col}_roll_mean_36'] = df[col].rolling(36).mean()  # 3hr avg
        df[f'{col}_roll_max_12']  = df[col].rolling(12).max()   # 1hr peak

    # ── State features ──
    df['is_warning']  = (df['check_state'] == 1).astype(int)
    df['is_critical'] = (df['check_state'] == 2).astype(int)

    return df, metric_cols


def prepare_regression_data(df: pd.DataFrame, target_col: str):
    """
    target_col: the primary metric to predict (e.g. 'power')
    Returns: X (features), y (target), feature_names
    """
    feature_cols = [
        'time_index',
        'hour', 'minute', 'day_of_week', 'day_of_month', 'is_weekend',
        'is_warning', 'is_critical',
        f'{target_col}_lag1',
        f'{target_col}_lag3',
        f'{target_col}_lag6',
        f'{target_col}_lag12',
        f'{target_col}_roll_mean_12',
        f'{target_col}_roll_std_12',
        f'{target_col}_roll_mean_36',
        f'{target_col}_roll_max_12',
    ]

    # Keep only cols that exist
    feature_cols = [c for c in feature_cols if c in df.columns]

    df_model = df[feature_cols + [target_col]].dropna()

    X = df_model[feature_cols].values
    y = df_model[target_col].values

    print(f"[INFO] Target        : {target_col}")
    print(f"[INFO] Features      : {len(feature_cols)}")
    print(f"[INFO] Training rows : {len(X)}  (dropped {len(df) - len(X)} NaN rows)")
    print(f"[INFO] y range       : {y.min():.2f} → {y.max():.2f}")

    return X, y, feature_cols, df_model


def prediction_tabular_data():
    # Load
    data    = get_sql_data()
    df_raw  = pd.DataFrame(data["rows"], columns=data["columns"])
    print(f"[INFO] Raw rows loaded: {len(df_raw)}")

    # Build features
    df_feat, metric_cols = build_features(df_raw)

    # ── Pick target: first numeric metric found in perfdata ──
    if not metric_cols:
        raise ValueError("No numeric metrics found in perfdata — check parse_perfdata()")

    target_col = metric_cols[0]  # swap to 'power' or whatever your col is named
    print(f"[INFO] Auto-selected target: {target_col}")

    # Prepare regression arrays
    X, y, feature_names, df_model = prepare_regression_data(df_feat, target_col)

    return {
        "X"             : X,
        "y"             : y,
        "feature_names" : feature_names,
        "df_model"      : df_model,
        "df_full"       : df_feat,
        "target_col"    : target_col,
        "metric_cols"   : metric_cols,
    }


if __name__ == "__main__":
    result = prediction_tabular_data()
    X, y   = result["X"], result["y"]
    print(f"\nX shape: {X.shape}")
    print(f"y shape: {y.shape}")