from datetime import datetime, timedelta, timezone
import time
import pandas as pd
import ccxt

TIMEFRAME_MIN = {'1m':1,'5m':5,'15m':15,'1h':60,'4h':240,'1d':1440}

def init_exchange():
    ex = ccxt.binance({'enableRateLimit': True})
    ex.load_markets()
    return ex

def normalize_symbol(ex, symbol: str) -> str:
    if symbol in ex.markets:
        return symbol
    s = symbol.replace('_','/') if '_' in symbol else symbol
    if s in ex.markets:
        return s
    if not s.endswith('/USDT') and s.endswith('USDT'):
        candidate = s.replace('USDT','/USDT')
        if candidate in ex.markets:
            return candidate
    raise ValueError(f"Symbol not supported: {symbol}")

def fetch_ohlcv(ex, symbol: str, timeframe: str, months: int = 6, limit: int = 1000) -> pd.DataFrame:
    if timeframe not in TIMEFRAME_MIN:
        raise ValueError(f"Unsupported timeframe {timeframe}")
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=months*30)
    since = int(start.timestamp()*1000)
    all_rows = []
    while True:
        batch = ex.fetch_ohlcv(symbol, timeframe=timeframe, since=since, limit=limit)
        if not batch:
            break
        all_rows += batch
        since = batch[-1][0] + TIMEFRAME_MIN[timeframe]*60*1000
        if batch[-1][0] >= int(end.timestamp()*1000):
            break
        time.sleep(ex.rateLimit/1000)
    if not all_rows:
        return pd.DataFrame()
    df = pd.DataFrame(all_rows, columns=["ts","open","high","low","close","volume"])
    df['timestamp'] = pd.to_datetime(df.ts, unit='ms', utc=True)
    df.drop_duplicates('timestamp', inplace=True)
    df.sort_values('timestamp', inplace=True)
    return df[['timestamp','open','high','low','close','volume']]
