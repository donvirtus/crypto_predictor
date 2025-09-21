import pandas as pd


def add_derivative_features(df: pd.DataFrame, cfg) -> pd.DataFrame:
    for lag in cfg.lagged_periods:
        df[f'close_lag_{lag}'] = df['close'].shift(lag)
        for p in cfg.ma_periods:
            ma_col = f'ma_{p}'
            if ma_col in df.columns:
                df[f'{ma_col}_lag_{lag}'] = df[ma_col].shift(lag)
        rsi_col = f'rsi_{cfg.rsi_period}'
        if rsi_col in df.columns:
            df[f'{rsi_col}_lag_{lag}'] = df[rsi_col].shift(lag)
    for p in cfg.ma_periods:
        ma_col = f'ma_{p}'
        if ma_col in df.columns:
            df[f'close_to_{ma_col}'] = df['close'] / df[ma_col]
    if 'vwap' in df.columns:
        df['close_to_vwap'] = df['close'] / df['vwap']
    for period in cfg.bb_periods:
        mid = f'bb_{period}_middle'
        if mid in df.columns:
            df[f'close_to_{mid}'] = df['close'] / df[mid]
    if 'macd' in df.columns and 'macd_signal' in df.columns:
        df['macd_diff'] = df['macd'] - df['macd_signal']
    return df
