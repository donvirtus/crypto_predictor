from dataclasses import dataclass
import yaml


@dataclass
class Config:
    pairs: list
    timeframes: list
    months: int
    bb_periods: list
    bb_devs: list
    ma_periods: list
    price_range_period: int
    volatility_period: int
    adx_period: int
    rsi_period: int
    macd_params: list
    lagged_periods: list
    target: dict
    database: dict
    paths: dict
    external: dict


def load_config(path: str) -> Config:
    with open(path, "r") as f:
        raw = yaml.safe_load(f) or {}
    return Config(**raw)


def save_config(cfg: Config, path: str):
    with open(path, "w") as f:
        yaml.dump(cfg.__dict__, f)
