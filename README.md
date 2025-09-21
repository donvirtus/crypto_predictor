# Trade Predictor (Refactored Modular Pipeline)

Modern, modular pipeline for collecting market data, engineering features (enhanced multi‑deviation Bollinger Bands, momentum, volatility, ratios, lags), merging optional external fundamentals (CoinGecko, CoinMetrics, Dune placeholder), labeling supervised learning targets, and persisting a unified feature dataset for downstream modeling.

## 1. High‑Level Architecture
```
scripts/collect_preprocess.py  (thin CLI wrapper)
 → pipeline.build_dataset.build()
         ├─ data.binance_fetch (raw OHLCV)
         ├─ features.indicators (price & technical indicators)
         ├─ features.derivatives (ratios, lags, derived features)
         ├─ data.external.(coingecko|coinmetrics|dune) (optional enrich)
         ├─ features.targets (future direction + volatility regime labels)
         └─ sqlite sink (features, metadata)
```

Each step is isolated for clarity, testability, and future extension (e.g., new exchanges, alternative targets, new external signals).

## 2. Key Directories
```
trade_predictor/
   utils/        # logging + typed config loader
   data/         # exchange + external data fetchers
   features/     # indicators, derivative transforms, labeling
   pipeline/     # orchestration (build_dataset.py)
   scripts/      # CLI entry (collect_preprocess.py)
config/config.yaml
```

## 3. Configuration (`config/config.yaml`)
Core fields (already populated with defaults):
```
pairs: [BTCUSDT]
timeframes: [5m]
months: 6                # look‑back window (approximate)
bb_periods: [48, 96]
bb_devs: [1.0, 2.0]
ma_periods: [6]
adx_period: 14
rsi_period: 14
volatility_period: 5
price_range_period: 5
lagged_periods: [2]

target:
   horizon: 20                 # candles ahead for direction label
   sideways_threshold_pct: 1.0 # ± threshold for 'sideways'

external:
   enable_coingecko: true
   coin_id: bitcoin
   enable_coinmetrics: false
   coinmetrics_asset: btc
   coinmetrics_metrics: [AdrActCnt]
   enable_dune: false
   dune_query_ids: []

output:
   sqlite_db: data/db/preprocessed.sqlite
   logs_dir: data/logs
   plots_dir: data/plots
```

Update values as needed; leave unused external sources disabled to avoid network calls.

## 4. Environment Variables
Provide secrets (if enabling certain external sources) by copying `.env.example` to `.env`:
```
COINMETRICS_API_KEY=your_key_here
DUNE_API_KEY=optional_key
```
CoinGecko public endpoints currently need no key (light cached snapshot implemented).

## 5. Running the Pipeline
Create / update configuration, then run:
```
python -m trade_predictor.scripts.collect_preprocess \
   --config config/config.yaml \
   --output-db data/db/preprocessed.sqlite
```
Outputs:
* SQLite DB at `data/db/preprocessed.sqlite` with tables:
   - `features` (engineered dataset)
   - `metadata` (run descriptors)
* Logs via unified logger (console + file if configured)

Return value of `build()` is a pandas DataFrame (also persisted), enabling interactive exploration.

## 6. Feature Engineering Summary
Indicators (per timeframe & pair):
* Multi‑deviation Bollinger Bands (upper/lower/middle + percent_b, bandwidth, squeeze flag)
* SMA set (from `ma_periods`)
* RSI, ADX, MACD (fast/slow/signal from config `macd_params` if present – planned extension)
* Volatility (rolling std) + price range
* Volume normalization (planned extension placeholder)
Derivatives:
* Lagged close returns (for each `lagged_periods`)
* Ratios: close / MA, close / BB middle, width normalization
Targets:
* `direction` in {-1,0,1} mapped to {Down, Sideways, Up} using future horizon & sideways threshold
* `vol_regime` categorical volatility regime from rolling std (low/medium/high heuristic)

## 7. External Data Enrichment
Joined on calendar date (daily) then forward‑filled to intraday candles:
* CoinGecko: market_cap, total_volume, circulating_supply, fdv (approx)
* CoinMetrics: arbitrary metrics list (if key provided)
* Dune: placeholder returning empty DataFrame (future SQL query integration)

Disable sources you do not need for faster, deterministic runs.

## 8. Extending the System
Add new indicator:
1. Implement in `features/indicators.py` (pure function; avoid side effects).
2. Add config toggle or period list if parameterized.
3. Re‑run pipeline; new columns appear automatically in `features` table.

Add a new target label:
1. Create function in `features/targets.py`.
2. Invoke inside `build_dataset.build()` after indicators/derivatives.

Integrate new external API:
1. Create module under `data/external/` returning DataFrame with `date` column.
2. Register merge in `merge_external()`.
3. Add enable flag + settings in config.

## 9. Data Schema (Core Columns)
```
timestamp, open, high, low, close, volume, pair, timeframe,
bb_{period}_upper_{dev}, bb_{period}_lower_{dev}, bb_{period}_middle,
bb_{period}_percent_b, bb_{period}_bandwidth, bb_{period}_squeeze,
ma_{period}, rsi_{rsi_period}, adx_{adx_period}, volatility_{volatility_period}, price_range_{price_range_period},
<derivative columns>, direction, vol_regime
```
External columns (prefixed / raw names) appended when enabled.

## 10. Minimal Example (Programmatic Usage)
```python
from trade_predictor.pipeline.build_dataset import build
df = build(cfg_path="config/config.yaml", output_db="data/db/preprocessed.sqlite")
print(df.head())
```

## 11. Testing & Validation (Suggested Next Steps)
Planned (not yet included):
* Unit tests for each feature module (deterministic indicator calculations on synthetic data)
* Schema validator to assert required columns exist before saving
* CLI dry‑run flag (fetch limited rows)

## 12. Roadmap Ideas
* Add MACD & OBV implementation to indicators module
* Add caching layer for Binance fetch (local parquet)
* Introduce proper unit tests (pytest + fixtures)
* Integrate model training phase as new pipeline stage (CatBoost / XGBoost)
* Add config schema validation (pydantic) and type hints everywhere
* Add Dockerfile for reproducible environment

## 13. Troubleshooting
Empty dataset: ensure `pairs` and `timeframes` valid and network access to Binance.
Missing external fields: check enable flags and environment variables.
DB not created: ensure parent directory exists or adjust `output.sqlite_db` path.

## 14. License
TBD

---
Refactor status: legacy monolith removed; modular pipeline operational. See `scripts/collect_preprocess.py` for entrypoint.
