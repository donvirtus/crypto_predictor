import os, sqlite3
import pandas as pd
from datetime import datetime
from trade_predictor.utils.logging import get_logger
from trade_predictor.utils.config import load_config
from trade_predictor.data.binance_fetch import init_exchange, normalize_symbol, fetch_ohlcv
from trade_predictor.data.external.coingecko import fetch_coingecko_snapshot
from trade_predictor.data.external.coinmetrics import fetch_coinmetrics
from trade_predictor.data.external.dune import fetch_dune_query
from trade_predictor.features.indicators import add_price_indicators
from trade_predictor.features.derivatives import add_derivative_features
from trade_predictor.features.targets import label_future_direction, label_regime_volatility


def merge_external(df: pd.DataFrame, cfg, logger):
    df['date'] = df['timestamp'].dt.date
    frames = []
    if cfg.external.get('enable_coingecko', False):
        cg = fetch_coingecko_snapshot(cfg.external.get('coin_id','bitcoin'))
        frames.append(cg)
    if cfg.external.get('enable_coinmetrics', False):
        cm = fetch_coinmetrics(asset=cfg.external.get('coinmetrics_asset','btc'), metrics=tuple(cfg.external.get('coinmetrics_metrics',["AdrActCnt"])) )
        frames.append(cm)
    # Dune (placeholder)
    if cfg.external.get('enable_dune', False):
        for q in cfg.external.get('dune_query_ids', []):
            dq = fetch_dune_query(q)
            frames.append(dq)
    if not frames:
        return df
    ext = frames[0]
    for add in frames[1:]:
        if add is not None and not add.empty:
            ext = ext.merge(add, on='date', how='outer')
    ext.sort_values('date', inplace=True)
    merged = df.merge(ext, on='date', how='left')
    merged.sort_values('timestamp', inplace=True)
    merged.ffill(inplace=True)
    return merged


def save_to_sqlite(df: pd.DataFrame, db_path: str, table: str, mode: str = 'replace'):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        df.to_sql(table, conn, if_exists=mode, index=False)


def build(cfg_path: str = 'config/config.yaml', output_db: str = 'data/db/preprocessed.sqlite'):
    logger = get_logger('pipeline')
    cfg = load_config(cfg_path)
    ex = init_exchange()
    all_frames = []
    for pair in cfg.pairs:
        sym = normalize_symbol(ex, pair)
        for tf in cfg.timeframes:
            logger.info(f"Fetching {pair} {tf}")
            raw = fetch_ohlcv(ex, sym, tf, months=cfg.months)
            if raw.empty:
                logger.warning(f"Empty data for {pair} {tf}")
                continue
            raw['pair']=pair; raw['timeframe']=tf
            enriched = add_price_indicators(raw.copy(), cfg)
            enriched = add_derivative_features(enriched, cfg)
            enriched = merge_external(enriched, cfg, logger)
            # labels
            enriched = label_future_direction(enriched, cfg.target.get('horizon', 20), cfg.target.get('sideways_threshold_pct', 1.0))
            vol_col = f'volatility_{cfg.volatility_period}'
            enriched = label_regime_volatility(enriched, vol_col)
            enriched.dropna(inplace=True)
            all_frames.append(enriched)
    if not all_frames:
        logger.error("No data fetched.")
        return None
    final = pd.concat(all_frames, ignore_index=True)
    save_to_sqlite(final, output_db, 'features')
    meta = pd.DataFrame([{ 'created_at': datetime.utcnow().isoformat(), 'pairs': str(cfg.pairs), 'timeframes': str(cfg.timeframes)}])
    save_to_sqlite(meta, output_db, 'metadata', mode='append')
    logger.info(f"Saved dataset rows={len(final)} to {output_db}")
    return final

if __name__ == '__main__':
    build()
