"""Compare NSW and PSID earnings in the LaLonde data."""
from __future__ import annotations

import argparse
import json
import hashlib
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

def verify_source(path: Path) -> None:
    manifest = json.loads((ROOT / "data_provenance.json").read_text())
    if hashlib.sha256(path.read_bytes()).hexdigest() != manifest["sha256"]:
        raise ValueError("Source checksum changed. Review the upstream data before updating data_provenance.json.")


def load_data(path: Path | None) -> pd.DataFrame:
    if path:
        data = pd.read_csv(path)
    else:
        cache = ROOT / "data" / "lalonde.csv"
        cache.parent.mkdir(parents=True, exist_ok=True)
        if not cache.exists():
            with urlopen(DATA_URL, timeout=30) as response:
                cache.write_bytes(response.read())
        verify_source(cache)
        data = pd.read_csv(cache)
    if "black" not in data.columns and "race" in data.columns:
        data["black"] = data["race"].astype(str).str.lower().eq("black").astype(int)
    if "hispan" not in data.columns and "race" in data.columns:
        data["hispan"] = data["race"].astype(str).str.lower().eq("hispan").astype(int)
    required = {"treat", "re78", *BASELINE}
    missing = required - set(data.columns)
    if missing:
        raise ValueError(f"Dataset missing required columns: {sorted(missing)}")
    # Validate numeric fields before calculating group comparisons.
    for col in required:
        data[col] = pd.to_numeric(data[col], errors="raise")
    if np.isinf(data[list(required)].to_numpy(dtype=float)).any():
        raise ValueError("Infinite values are not permitted.")
    if not data["treat"].isin([0, 1]).all():
        raise ValueError("treat must contain only 0 and 1.")
    data = data.copy()
    data["treat"] = data["treat"].astype(int)
    return data

def analysis_sample(data: pd.DataFrame) -> pd.DataFrame:
    return data[["treat", "re78", *BASELINE]].dropna().copy()


def analyze(data: pd.DataFrame) -> dict:
    analysis = analysis_sample(data)
    treated = analysis.loc[analysis.treat == 1, "re78"].to_numpy()
    control = analysis.loc[analysis.treat == 0, "re78"].to_numpy()
    if len(treated) < 2 or len(control) < 2:
        raise ValueError("At least two complete observations per group are required.")
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
        "adjusted_ols_treatment_association": float(model.params["treat"]),
        "adjusted_ols_robust_se_HC2": float(model.bse["treat"]),
        "adjusted_ols_p_value": float(model.pvalues["treat"]),
        "adjusted_ols_95pct_ci": [float(x) for x in model.conf_int().loc["treat"]],
        "currency_units": "1978 US dollars (as recorded in source data)",
        "causal_interpretation": "Associational comparison: PSID units are not randomized NSW controls.",
    }

def diagnostics(data: pd.DataFrame) -> dict:
    """Check baseline differences and how the estimate changes across models."""
    sample = analysis_sample(data)
    baseline = []
    for col in BASELINE:
        t = sample.loc[sample.treat.eq(1), col]
        c = sample.loc[sample.treat.eq(0), col]
        denom = np.sqrt((t.var() + c.var()) / 2)
        baseline.append({"variable": col, "treated_mean": t.mean(), "comparison_mean": c.mean(),
                         "standardized_mean_difference": (t.mean()-c.mean()) / denom if denom > 0 else None})
    pd.DataFrame(baseline).to_csv(OUT / "baseline_balance.csv", index=False)
    specs = {
        "Unadjusted OLS": "re78 ~ treat",
        "Baseline adjusted": "re78 ~ treat + " + " + ".join(BASELINE),
        "Nonlinear baseline": "re78 ~ treat + " + " + ".join(BASELINE) + " + I(age ** 2) + I(educ ** 2) + I(re74 ** 2) + I(re75 ** 2)",
    }
    base = smf.ols(specs["Baseline adjusted"], data=sample).fit()
    cooks = base.get_influence().cooks_distance[0]
    rows = []
    for name, formula in specs.items():
        model = smf.ols(formula, data=sample).fit(cov_type="HC2")
        ci = model.conf_int().loc["treat"]
        rows.append({"specification": name, "estimate": float(model.params["treat"]), "ci_low": float(ci.iloc[0]), "ci_high": float(ci.iloc[1]), "n": len(sample)})
    trimmed = sample.loc[cooks <= 4 / len(sample)]
    model = smf.ols(specs["Baseline adjusted"], data=trimmed).fit(cov_type="HC2")
    ci = model.conf_int().loc["treat"]
    rows.append({"specification": "Influence sensitivity (Cook > 4/n excluded)", "estimate": float(model.params["treat"]), "ci_low": float(ci.iloc[0]), "ci_high": float(ci.iloc[1]), "n": len(trimmed)})
    pd.DataFrame(rows).to_csv(OUT / "specification_sensitivity.csv", index=False)
    fig, ax = plt.subplots(figsize=(10, 5))
    for i, row in enumerate(rows):
        ax.errorbar(row["estimate"], i, xerr=[[row["estimate"]-row["ci_low"]], [row["ci_high"]-row["estimate"]]], fmt="o", capsize=4)
    ax.set_yticks(range(len(rows)), [r["specification"] for r in rows])
    ax.axvline(0, color="gray", linestyle="--")
    ax.set(xlabel="Adjusted/unadjusted earnings difference (1978 USD), 95% HC2 intervals", title="Observational estimates depend on adjustment")
    fig.tight_layout(); fig.savefig(OUT / "specification_sensitivity.png", dpi=160); plt.close(fig)
    fig, axes = plt.subplots(2, 2, figsize=(10, 7))
    for col, ax in zip(["age", "educ", "re74", "re75"], axes.flat):
        values = sample[col]
        bins = np.histogram_bin_edges(values, bins=20)
        for group, label in [(0, "PSID"), (1, "NSW")]:
            ax.hist(sample.loc[sample.treat.eq(group), col], bins=bins, density=True, alpha=.45, label=label)
        ax.set(title=col, ylabel="Density")
        ax.legend()
    fig.suptitle("Baseline covariate overlap — common analysis sample")
    fig.tight_layout(); fig.savefig(OUT / "baseline_overlap.png", dpi=160); plt.close(fig)
    return {"baseline_balance": baseline, "specifications": rows,
            "influential_rows_above_4_over_n": int((cooks > 4 / len(sample)).sum()),
            "interpretation": "Sensitivity analyses are not causal identification. Excluding influential observations is a diagnostic, not a preferred estimate."}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, help="Optional local CSV path")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    df = load_data(args.data)
    result = analyze(df)
    result["diagnostics"] = diagnostics(df)
    plot_sample = analysis_sample(df)
    (OUT / "summary.json").write_text(json.dumps(result, indent=2) + chr(10))
    fig, ax = plt.subplots(figsize=(8, 5))
    groups = [plot_sample.loc[plot_sample.treat == 0, "re78"], plot_sample.loc[plot_sample.treat == 1, "re78"]]
    ax.boxplot(groups, tick_labels=["PSID comparison", "NSW treatment"], showfliers=False)
    ax.set(title="1978 earnings by comparison group", ylabel="Earnings (1978 USD)")
    fig.tight_layout()
    fig.savefig(OUT / "earnings_by_group.png", dpi=160)
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
