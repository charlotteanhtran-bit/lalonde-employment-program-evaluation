"""Reproducible analysis of the MatchIt LaLonde employment-program comparison."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.request import urlopen

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats

ROOT = Path(__file__).resolve().parent
DATA_URL = "https://raw.githubusercontent.com/robjellis/lalonde/master/lalonde_data.csv"
OUT = ROOT / "outputs"
BASELINE = ["age", "educ", "black", "hispan", "married", "nodegree", "re75", "re74"]

def load_data(path: Path | None) -> pd.DataFrame:
    if path:
        data = pd.read_csv(path)
    else:
        cache = ROOT / "data" / "lalonde.csv"
        cache.parent.mkdir(parents=True, exist_ok=True)
        if not cache.exists():
            with urlopen(DATA_URL, timeout=30) as response:
                cache.write_bytes(response.read())
        data = pd.read_csv(cache)
    if "black" not in data.columns and "race" in data.columns:
        data["black"] = data["race"].astype(str).str.lower().eq("black").astype(int)
    if "hispan" not in data.columns and "race" in data.columns:
        data["hispan"] = data["race"].astype(str).str.lower().eq("hispan").astype(int)
    required = {"treat", "re78", *BASELINE}
    missing = required - set(data.columns)
    if missing:
        raise ValueError(f"Dataset missing required columns: {sorted(missing)}")
    # MatchIt pairs NSW-treated units with PSID comparison units.
    data = data.loc[data["treat"].isin([0, 1])].copy()
    data["treat"] = data["treat"].astype(int)
    return data

def analyze(data: pd.DataFrame) -> dict:
    analysis = data[["treat", "re78", *BASELINE]].dropna().copy()
    treated = analysis.loc[analysis.treat == 1, "re78"].to_numpy()
    control = analysis.loc[analysis.treat == 0, "re78"].to_numpy()
    if not len(treated) or not len(control):
        raise ValueError("Both treatment and comparison groups must be present.")
    diff = float(treated.mean() - control.mean())
    test = stats.ttest_ind(treated, control, equal_var=False)
    se = float(np.sqrt(treated.var(ddof=1) / len(treated) + control.var(ddof=1) / len(control)))
    margin = float(stats.t.ppf(0.975, float(test.df)) * se)
    formula = "re78 ~ treat + " + " + ".join(BASELINE)
    model = smf.ols(formula, data=analysis).fit(cov_type="HC2")
    return {
        "n": int(len(analysis)),
        "n_treatment": int(len(treated)),
        "n_control": int(len(control)),
        "missing_rows_removed": int(len(data) - len(analysis)),
        "treatment_mean_1978_earnings": float(treated.mean()),
        "control_mean_1978_earnings": float(control.mean()),
        "unadjusted_mean_difference": diff,
        "welch_95pct_ci": [diff - margin, diff + margin],
        "welch_t_statistic": float(test.statistic),
        "welch_p_value": float(test.pvalue),
        "adjusted_ols_treatment_effect": float(model.params["treat"]),
        "adjusted_ols_robust_se_HC2": float(model.bse["treat"]),
        "adjusted_ols_p_value": float(model.pvalues["treat"]),
        "adjusted_ols_95pct_ci": [float(x) for x in model.conf_int().loc["treat"]],
        "currency_units": "1978 US dollars (as recorded in source data)",
        "causal_interpretation": "Associational comparison: PSID units are not randomized NSW controls.",
    }

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, help="Optional local CSV path")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    df = load_data(args.data)
    result = analyze(df)
    (OUT / "summary.json").write_text(json.dumps(result, indent=2) + chr(10))
    fig, ax = plt.subplots(figsize=(8, 5))
    groups = [df.loc[df.treat == 0, "re78"], df.loc[df.treat == 1, "re78"]]
    ax.boxplot(groups, tick_labels=["PSID comparison", "NSW treatment"], showfliers=False)
    ax.set(title="1978 earnings by comparison group", ylabel="Earnings (1978 USD)")
    fig.tight_layout()
    fig.savefig(OUT / "earnings_by_group.png", dpi=160)
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
