import pandas as pd
import numpy as np


def label_future_direction(df: pd.DataFrame, horizon: int, sideways_threshold_pct: float = 1.0) -> pd.DataFrame:
    future_price = df['close'].shift(-horizon)
    pct_change = (future_price - df['close']) / df['close'] * 100
    cond_up = pct_change > sideways_threshold_pct
    cond_down = pct_change < -sideways_threshold_pct
    df['direction'] = np.select([cond_down, cond_up], [0,2], default=1)
    df['future_return_pct'] = pct_change
    return df


def label_regime_volatility(df: pd.DataFrame, vol_col: str, low_q: float = 0.33, high_q: float = 0.66) -> pd.DataFrame:
    if vol_col not in df.columns:
        return df
    low = df[vol_col].quantile(low_q)
    high = df[vol_col].quantile(high_q)
    df['vol_regime'] = np.select([df[vol_col] < low, df[vol_col] > high], [0,2], default=1)
    return df
