# Employment Program Evaluation — LaLonde

An observational analysis of historical employment-program participation and earnings, inspired by WQU DS 07 skills. It uses public data and original code; it does not reproduce WQU's private applicant dataset or notebook.

## Research question

How did 1978 earnings differ between participants in the National Supported Work (NSW) program and a PSID comparison group?

## Data

The LaLonde dataset from the R MatchIt package includes NSW program participants and PSID comparison units. The PSID group was not randomized, so these results are adjusted comparisons, not causal estimates.

Outcome: re78 (1978 earnings). Group indicator: treat (1=NSW participant, 0=PSID comparison). Baseline variables are used for descriptive summaries and regression adjustment.

The script downloads the CSV from a public GitHub mirror when needed. A local CSV can be passed with --data.

## Reproduce

    python -m venv .venv
    source .venv/bin/activate  # Windows: .venv\Scripts\activate
    pip install -r requirements-lock.txt
    python analyze.py

The script writes a JSON summary and earnings plot to outputs/. The current run produced an unadjusted difference of -$635 (Welch p=0.349) and baseline-adjusted OLS estimate of +$1,548 (HC2 robust p=0.037). Earnings are skewed, and the adjusted result should not be interpreted causally because the PSID comparison group was not randomized.

## Interpretation limits

This is a historical employment-program evaluation, not university admissions data. Differences may reflect selection and unmeasured confounding. Results should not be generalized automatically to current programs. Statistical significance is not practical importance; no causal subgroup claims are made.

## Data provenance

- LaLonde (1986), “Evaluating the Econometric Evaluations of Training Programs with Experimental Data,” American Economic Review, 76(4), 604–620.
- Dataset: MatchIt package, lalonde, distributed via https://raw.githubusercontent.com/robjellis/lalonde/master/lalonde_data.csv

Please preserve upstream attribution if redistributing the CSV.

## Findings and robustness

- The 614-person sample includes 185 NSW participants and 429 PSID comparison observations. The raw earnings difference is −$635; baseline adjustment changes it to +$1,548 (95% HC2 interval: $94 to $3,003).
- The groups start substantially different: mean 1974 earnings are $2,096 versus $5,619, and the standardized difference in the source's Black indicator is 1.668. These imbalances help explain why adjustment changes the comparison; they do not prove that adjustment eliminates confounding.
- Adding quadratic baseline terms reduces the estimate to +$993 (95% interval: −$376 to $2,362). The conclusion is specification-sensitive. A separate influence diagnostic excludes 37 rows above Cook's distance 4/n; it is not the preferred analysis.

![Specification sensitivity](reports/specification_sensitivity.png)

![Baseline covariate overlap](reports/baseline_overlap.png)

The unadjusted chart interval uses HC2 OLS; the summary's Welch interval uses Welch's t degrees of freedom, so their endpoints differ slightly. Every main plot and model uses the same complete-case sample. The influence sensitivity intentionally uses a smaller sample.

## Engineering and verification

- `data_provenance.json` records the downloaded mirror's SHA-256, size, source, and retrieval date. Cached and new downloads must match; custom `--data` files instead undergo schema/value validation.
- `requirements-lock.txt` records the tested Python 3.12 Linux dependency environment. `requirements.txt` lists direct minimum versions.
- `python -m unittest discover -s tests -v` checks missing groups, invalid input, and complete-case consistency. GitHub Actions runs tests and the full analysis.
- `reports/` contains checked-in results and charts. Regenerate with `python analyze.py`; review and copy outputs into `reports/` when intentionally updating published results. The root `summary.json` is retained as a compatibility snapshot.

This project evaluates associations in an employment-program comparison; it is not a randomized applicant A/B test. The existing repository URL is preserved to avoid breaking portfolio links.
