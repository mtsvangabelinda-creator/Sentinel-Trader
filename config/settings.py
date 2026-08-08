"""
Loads btc_config.yaml into a plain dict. Kept intentionally dumb: no validation
magic, no defaults hidden in code. If a key is missing, it should fail loudly
rather than silently substitute something that changes risk behavior.
"""
import yaml
from pathlib import Path

CONFIG_PATH = Path(__file__).parent / "btc_config.yaml"


def load_config(path: Path = CONFIG_PATH) -> dict:
    with open(path, "r") as f:
        config = yaml.safe_load(f)
    _validate(config)
    return config


def _validate(config: dict) -> None:
    required_top_level = [
        "capital", "risk", "regime", "sentinel",
        "trend_following", "mean_reversion", "momentum_burst", "fees",
    ]
    missing = [k for k in required_top_level if k not in config]
    if missing:
        raise ValueError(f"btc_config.yaml is missing required sections: {missing}")

    pools = config["capital"]["pools"]
    pool_sum = sum(pools.values())
    if abs(pool_sum - config["capital"]["total"]) > 0.01:
        raise ValueError(
            f"Strategy pools ({pool_sum}) do not sum to total capital "
            f"({config['capital']['total']})"
        )


if __name__ == "__main__":
    cfg = load_config()
    print("Config loaded OK. Pools:", cfg["capital"]["pools"])
