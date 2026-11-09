# Experimentation and Decision-Making: Applicant Support Intervention

An original analysis project inspired by WQU DS 07 skills. It uses public data and original code; it does not reproduce WQU's private applicant dataset or notebook.

## Research question

How did 1978 earnings differ between participants in the National Supported Work (NSW) program and a PSID comparison group?

## Data

The LaLonde dataset from the R MatchIt package includes NSW program participants and PSID comparison units. The PSID group was not randomized, so these results are adjusted comparisons, not causal estimates.

Outcome: re78 (1978 earnings). Group indicator: treat (1=NSW participant, 0=PSID comparison). Baseline variables are used for descriptive summaries and regression adjustment.

The script downloads the CSV from a public GitHub mirror when needed. A local CSV can be passed with --data.

## Reproduce

    python -m venv .venv
    source .venv/bin/activate  # Windows: .venv\Scripts\activate
    pip install -r requirements.txt
    python analyze.py

The script writes a JSON summary and earnings plot to outputs/. The current run produced an unadjusted difference of -$635 (Welch p=0.349) and baseline-adjusted OLS estimate of +$1,548 (HC2 robust p=0.037). Earnings are skewed, and the adjusted result should not be interpreted causally because the PSID comparison group was not randomized.

## Interpretation limits

This is a historical employment-program evaluation, not university admissions data. Differences may reflect selection and unmeasured confounding. Results should not be generalized automatically to current programs. Statistical significance is not practical importance; no causal subgroup claims are made.

## Data provenance

- LaLonde (1986), “Evaluating the Econometric Evaluations of Training Programs with Experimental Data,” American Economic Review, 76(4), 604–620.
- Dataset: MatchIt package, lalonde, distributed via https://raw.githubusercontent.com/robjellis/lalonde/master/lalonde_data.csv

Please preserve upstream attribution if redistributing the CSV.
