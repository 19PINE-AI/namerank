"""
t1_1: Gold-answer length / fact-density confound check for the credential-treadmill thesis.

Steps:
  1) Build per-entity gold metrics (chars, words, named_facts).
  2) Within-cohort regressions of NameRank on gold metrics (cohorts with n>=50).
  3) Cross-cohort linear model NameRank ~ gold_chars + gold_named_facts + cohort FE,
     then construct adjusted cohort means relative to the OpenAlex long-tail baseline.
  4) Matched-pairs (gold_chars +/- 50): IMO gold vs long_tail_researcher_openalex (50 pairs).
  5) Discussion is written into README.md.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path('/home/ubuntu/namerank')
OUT = ROOT / 'experiments' / 't1_1_gold_length'
OUT.mkdir(parents=True, exist_ok=True)

CREDENTIAL_COHORTS = [
    'imo_gold', 'ioi_gold', 'cmo_china_gold', 'rhodes_scholar',
    'msra_phd_fellowship', 'cpho_china_first_prize', 'noi_china_gold',
    'icpc_world_finals_gold', 'putnam_fellow',
]
BASELINE_COHORT = 'long_tail_researcher_openalex'

# ----------------------------------------------------------------------------
# Load data
# ----------------------------------------------------------------------------
with open(ROOT / 'data/inputs/pilot_entities.json') as fh:
    entities = json.load(fh)
with open(ROOT / 'data/inputs/gold_answers.json') as fh:
    gold = json.load(fh)
nr = pd.read_csv(ROOT / 'data/analysis/namerank_per_entity.csv')

ent_df = pd.DataFrame(entities)[['id', 'name', 'cohort']].rename(columns={'id': 'entity_id'})

# ----------------------------------------------------------------------------
# 1) gold metrics
# ----------------------------------------------------------------------------
WORD_RE = re.compile(r"\b[\w'-]+\b", re.UNICODE)
# Capitalized multi-word tokens (proper noun phrases). Use ASCII-ish heuristic so
# that Chinese strings in gold answers don't dominate the count.
NAMED_FACTS_RE = re.compile(r"\b(?:[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)+)\b")
SENT_SPLIT_RE = re.compile(r"[.!?]+\s+")


def named_facts_count(text: str) -> int:
    if not text:
        return 0
    return len(NAMED_FACTS_RE.findall(text))


def sentence_count(text: str) -> int:
    if not text:
        return 0
    parts = [p for p in SENT_SPLIT_RE.split(text.strip()) if p.strip()]
    return max(1, len(parts))


rows = []
for e in entities:
    eid = e['id']
    g = gold.get(eid, '') or ''
    rows.append({
        'entity_id': eid,
        'cohort': e['cohort'],
        'gold_chars': len(g),
        'gold_words': len(WORD_RE.findall(g)),
        'gold_named_facts': named_facts_count(g),
        'gold_sentences': sentence_count(g),
    })
gm = pd.DataFrame(rows)
df = gm.merge(nr[['entity_id', 'namerank']], on='entity_id', how='left')
df = df.dropna(subset=['namerank']).copy()

# Choose between named_facts and sentence_count: whichever correlates higher
# with NameRank within the long_tail_researcher_openalex cohort (sanity proxy).
oa = df[df['cohort'] == BASELINE_COHORT]
r_nf = oa[['gold_named_facts', 'namerank']].corr().iloc[0, 1]
r_sc = oa[['gold_sentences', 'namerank']].corr().iloc[0, 1]
print(f"[OA proxy] corr(namerank, gold_named_facts)={r_nf:.4f}, corr(gold_sentences)={r_sc:.4f}")
use_facts = abs(r_nf) >= abs(r_sc)
if not use_facts:
    df['gold_named_facts'] = df['gold_sentences']
    gm['gold_named_facts'] = gm['gold_sentences']
print(f"Chosen 'gold_named_facts' definition: {'capitalized-bigram count' if use_facts else 'sentence count'}")

gm[['entity_id', 'cohort', 'gold_chars', 'gold_words', 'gold_named_facts', 'gold_sentences']].to_csv(
    OUT / 'gold_metrics.csv', index=False,
)

# ----------------------------------------------------------------------------
# 2) within-cohort regressions
# ----------------------------------------------------------------------------
def ols_with_stats(X: np.ndarray, y: np.ndarray):
    """OLS with intercept, returning (beta, se, r2). Adds intercept column."""
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float)
    Xi = np.column_stack([np.ones(len(X)), X])
    beta, *_ = np.linalg.lstsq(Xi, y, rcond=None)
    yhat = Xi @ beta
    resid = y - yhat
    sse = float(resid @ resid)
    sst = float(((y - y.mean()) ** 2).sum())
    r2 = 1.0 - sse / sst if sst > 0 else np.nan
    n, k = Xi.shape
    dof = max(n - k, 1)
    sigma2 = sse / dof
    XtXi = np.linalg.pinv(Xi.T @ Xi)
    cov = sigma2 * XtXi
    se = np.sqrt(np.clip(np.diag(cov), 0, None))
    return beta, se, r2, n


within = []
for cohort, sub in df.groupby('cohort'):
    if len(sub) < 50:
        continue
    X = sub[['gold_chars', 'gold_named_facts']].values
    y = sub['namerank'].values
    beta, se, r2, n = ols_with_stats(X, y)
    # standardized betas for comparability
    sx = sub[['gold_chars', 'gold_named_facts']].std(ddof=0).values
    sy = sub['namerank'].std(ddof=0)
    std_beta_chars = beta[1] * (sx[0] / sy) if sy > 0 else np.nan
    std_beta_facts = beta[2] * (sx[1] / sy) if sy > 0 else np.nan
    # rough t-stats
    t_chars = beta[1] / se[1] if se[1] > 0 else np.nan
    t_facts = beta[2] / se[2] if se[2] > 0 else np.nan
    within.append({
        'cohort': cohort,
        'n': n,
        'mean_namerank': sub['namerank'].mean(),
        'mean_gold_chars': sub['gold_chars'].mean(),
        'mean_gold_named_facts': sub['gold_named_facts'].mean(),
        'r2': r2,
        'beta_gold_chars': beta[1],
        'beta_gold_named_facts': beta[2],
        'std_beta_gold_chars': std_beta_chars,
        'std_beta_gold_named_facts': std_beta_facts,
        't_gold_chars': t_chars,
        't_gold_named_facts': t_facts,
    })
within_df = pd.DataFrame(within).sort_values('cohort')
within_df.to_csv(OUT / 'within_cohort_regressions.csv', index=False)

# ----------------------------------------------------------------------------
# 3) Cross-cohort fixed-effects model
# ----------------------------------------------------------------------------
cohorts_all = sorted(df['cohort'].unique())
# Reference category = BASELINE_COHORT
non_ref = [c for c in cohorts_all if c != BASELINE_COHORT]
fe = pd.get_dummies(df['cohort'], drop_first=False).reindex(columns=cohorts_all, fill_value=0)
fe = fe.drop(columns=[BASELINE_COHORT])

X = np.column_stack([df['gold_chars'].values, df['gold_named_facts'].values, fe.values])
y = df['namerank'].values
Xi = np.column_stack([np.ones(len(X)), X])
beta, *_ = np.linalg.lstsq(Xi.astype(float), y.astype(float), rcond=None)
intercept = beta[0]
b_chars = beta[1]
b_facts = beta[2]
fe_betas = dict(zip(fe.columns, beta[3:]))

# Goodness-of-fit
yhat = Xi.astype(float) @ beta
sse = float(((y - yhat) ** 2).sum())
sst = float(((y - y.mean()) ** 2).sum())
r2_full = 1.0 - sse / sst
print(f"Cross-cohort model R^2 = {r2_full:.4f}; b_chars={b_chars:.3e}, b_facts={b_facts:.3e}")

# Baseline-anchored adjusted cohort means.
# Idea: each cohort's raw mean = mean of namerank in that cohort. The model says
# E[NR | cohort=c] = intercept + b_chars*mean_chars_c + b_facts*mean_facts_c
#                     + FE_c (where FE_baseline = 0).
# The "FE_c" is the cohort-mean NameRank net of the gold-metric distribution
# (anchored so that the baseline cohort has FE = 0). We report
#     adjusted_mean = baseline_raw_mean + FE_c,
# i.e. what each cohort's NameRank would average if every cohort had the same
# gold-metric distribution as the OpenAlex baseline.
baseline_raw_mean = df[df['cohort'] == BASELINE_COHORT]['namerank'].mean()

# Auxiliary specification: identify the gold-metric slopes from the OpenAlex
# baseline cohort only (so the slope is not contaminated by between-cohort
# entity-quality variation that may correlate with gold length). Then transport
# those slopes to adjust every cohort to OpenAlex-equivalent gold metrics.
oa_sub = df[df['cohort'] == BASELINE_COHORT].copy()
Xoa = np.column_stack([oa_sub['gold_chars'].values, oa_sub['gold_named_facts'].values])
yoa = oa_sub['namerank'].values
beta_oa, se_oa, r2_oa, _ = ols_with_stats(Xoa, yoa)
b_chars_oa = float(beta_oa[1])
b_facts_oa = float(beta_oa[2])
oa_mean_chars = float(oa_sub['gold_chars'].mean())
oa_mean_facts = float(oa_sub['gold_named_facts'].mean())
print(f"\n[OA-baseline slope spec] b_chars_oa={b_chars_oa:.3e}, b_facts_oa={b_facts_oa:.3e}, R^2_oa={r2_oa:.4f}")

rows = []
for c in cohorts_all:
    sub = df[df['cohort'] == c]
    raw = sub['namerank'].mean()
    fe_c = 0.0 if c == BASELINE_COHORT else fe_betas[c]
    adjusted_fe = baseline_raw_mean + fe_c
    # OA-baseline slope adjustment: raw + b_chars_oa*(oa_mean_chars - mean_chars_c) + b_facts_oa*(oa_mean_facts - mean_facts_c)
    adj_oa = (raw
              + b_chars_oa * (oa_mean_chars - sub['gold_chars'].mean())
              + b_facts_oa * (oa_mean_facts - sub['gold_named_facts'].mean()))
    rows.append({
        'cohort': c,
        'n': len(sub),
        'mean_gold_chars': sub['gold_chars'].mean(),
        'mean_gold_named_facts': sub['gold_named_facts'].mean(),
        'raw_mean_namerank': raw,
        'fe_vs_openalex_baseline': fe_c,
        'adjusted_mean_namerank_fe': adjusted_fe,
        'adjusted_mean_namerank_oa_slope': adj_oa,
        'shift_fe': adjusted_fe - raw,
        'shift_oa_slope': adj_oa - raw,
    })
adj = pd.DataFrame(rows).sort_values('raw_mean_namerank')
adj.to_csv(OUT / 'adjusted_cohort_means.csv', index=False)

# Focus table for credential cohorts
focus_cohorts = CREDENTIAL_COHORTS + [BASELINE_COHORT]
focus = adj[adj['cohort'].isin(focus_cohorts)].copy()
focus_sorted_raw = focus.sort_values('raw_mean_namerank').reset_index(drop=True)
focus_sorted_fe = focus.sort_values('adjusted_mean_namerank_fe').reset_index(drop=True)
focus_sorted_oa = focus.sort_values('adjusted_mean_namerank_oa_slope').reset_index(drop=True)
print('\nFocus cohorts -- raw ranking:')
print(focus_sorted_raw[['cohort','n','raw_mean_namerank','adjusted_mean_namerank_fe','adjusted_mean_namerank_oa_slope']].to_string(index=False))
print('\nFocus cohorts -- FE-adjusted ranking:')
print(focus_sorted_fe[['cohort','n','raw_mean_namerank','adjusted_mean_namerank_fe']].to_string(index=False))
print('\nFocus cohorts -- OA-slope-adjusted ranking:')
print(focus_sorted_oa[['cohort','n','raw_mean_namerank','adjusted_mean_namerank_oa_slope']].to_string(index=False))

# ----------------------------------------------------------------------------
# 4) Matched-pairs check (IMO gold vs long-tail OpenAlex), 50 pairs, |dchars| <= 50
# ----------------------------------------------------------------------------
# CRITICAL: IMO golds are 359-392 chars; OpenAlex long-tail golds are 662-789
# chars. The two distributions have ZERO overlap (gap ~270 chars). A strict
# |delta_chars| <= 50 match therefore yields zero pairs. We report this directly
# and also compute relaxed-tolerance and nearest-neighbor variants.
left_full = df[df['cohort'] == 'imo_gold'][['entity_id', 'gold_chars', 'namerank']].copy()
right_full = df[df['cohort'] == BASELINE_COHORT][['entity_id', 'gold_chars', 'namerank']].copy()


def greedy_match(left: pd.DataFrame, right: pd.DataFrame, tol: float, k: int = 50, seed: int = 20260525):
    left = left.sample(frac=1.0, random_state=seed).reset_index(drop=True)
    right_used = np.zeros(len(right), dtype=bool)
    rch = right['gold_chars'].values
    rec = []
    for _, lrow in left.iterrows():
        diffs = np.abs(rch - lrow['gold_chars'])
        diffs = np.where(right_used, np.inf, diffs)
        j = int(np.argmin(diffs))
        if diffs[j] <= tol:
            right_used[j] = True
            rrow = right.iloc[j]
            rec.append({
                'imo_entity_id': lrow['entity_id'],
                'imo_gold_chars': int(lrow['gold_chars']),
                'imo_namerank': lrow['namerank'],
                'openalex_entity_id': rrow['entity_id'],
                'openalex_gold_chars': int(rrow['gold_chars']),
                'openalex_namerank': rrow['namerank'],
                'delta_chars': int(lrow['gold_chars'] - rrow['gold_chars']),
                'delta_namerank_imo_minus_openalex': lrow['namerank'] - rrow['namerank'],
            })
        if len(rec) >= k:
            break
    return pd.DataFrame(rec)


# 4a) Strict (paper-specified) tolerance: 50 chars.
pairs_strict = greedy_match(left_full, right_full, tol=50.0, k=50)

# 4b) Nearest-neighbor (no tolerance, smallest |delta_chars|).
pairs_nn = greedy_match(left_full, right_full, tol=np.inf, k=50)
pairs_nn = pairs_nn.assign(match_kind='nearest_neighbor')

# 4c) Demonstrative: pair IMO with a cohort that *does* overlap in chars
# (cmo_china_gold), using |delta_chars| <= 50. This tells us whether IMO scores
# look low even at matched gold length, against a sister credential cohort.
right_cmo = df[df['cohort'] == 'cmo_china_gold'][['entity_id', 'gold_chars', 'namerank']]
pairs_cmo = greedy_match(left_full, right_cmo, tol=50.0, k=50)

# Compose output file. Primary block = strict (per spec). Secondary blocks are
# clearly labeled.
if len(pairs_strict):
    pairs_strict = pairs_strict.assign(match_kind='strict_tol_50chars')
else:
    pairs_strict = pd.DataFrame(
        columns=['imo_entity_id','imo_gold_chars','imo_namerank',
                 'openalex_entity_id','openalex_gold_chars','openalex_namerank',
                 'delta_chars','delta_namerank_imo_minus_openalex','match_kind']
    )

pairs_nn = pairs_nn.assign(match_kind='nearest_neighbor_no_tol_IMO_vs_OpenAlex')
pairs_cmo = pairs_cmo.assign(match_kind='IMO_vs_CMO_tol_50chars')
pairs_cmo = pairs_cmo.rename(columns={
    'openalex_entity_id': 'partner_entity_id',
    'openalex_gold_chars': 'partner_gold_chars',
    'openalex_namerank': 'partner_namerank',
    'delta_namerank_imo_minus_openalex': 'delta_namerank_imo_minus_partner',
})
pairs_nn = pairs_nn.rename(columns={
    'openalex_entity_id': 'partner_entity_id',
    'openalex_gold_chars': 'partner_gold_chars',
    'openalex_namerank': 'partner_namerank',
    'delta_namerank_imo_minus_openalex': 'delta_namerank_imo_minus_partner',
})
pairs_strict = pairs_strict.rename(columns={
    'openalex_entity_id': 'partner_entity_id',
    'openalex_gold_chars': 'partner_gold_chars',
    'openalex_namerank': 'partner_namerank',
    'delta_namerank_imo_minus_openalex': 'delta_namerank_imo_minus_partner',
})
all_pairs = pd.concat([pairs_strict, pairs_nn, pairs_cmo], ignore_index=True)
all_pairs.to_csv(OUT / 'matched_pairs_imo_openalex.csv', index=False)


def summarize_pairs(p, label):
    if len(p) == 0:
        print(f"\n[{label}] n=0 (no eligible pairs)")
        return {'n': 0}
    n = len(p)
    di = p['delta_namerank_imo_minus_partner'].values
    se = di.std(ddof=1) / np.sqrt(n) if n > 1 else np.nan
    t = di.mean() / se if se and se > 0 else np.nan
    print(f"\n[{label}] n={n}, mean_imo={p['imo_namerank'].mean():.4f}, "
          f"mean_partner={p['partner_namerank'].mean():.4f}, "
          f"delta={di.mean():+.4f}, paired t={t:.2f}, "
          f"mean|dchars|={p['delta_chars'].abs().mean():.1f}")
    return {
        'n': int(n),
        'mean_imo': float(p['imo_namerank'].mean()),
        'mean_partner': float(p['partner_namerank'].mean()),
        'delta': float(di.mean()),
        'paired_t': float(t) if not pd.isna(t) else None,
        'mean_abs_dchars': float(p['delta_chars'].abs().mean()),
    }


mp_strict_summary = summarize_pairs(pairs_strict, 'IMO vs OpenAlex, strict tol=50')
mp_nn_summary = summarize_pairs(pairs_nn, 'IMO vs OpenAlex, nearest neighbor (no tol)')
mp_cmo_summary = summarize_pairs(pairs_cmo, 'IMO vs CMO, tol=50 (sister credential cohort, overlaps in chars)')

# Persist key numbers for the README writer
summary = {
    'gold_named_facts_definition': 'capitalized_multiword_bigrams' if use_facts else 'sentence_count',
    'oa_corr_named_facts': float(r_nf),
    'oa_corr_sentences': float(r_sc),
    'cross_model_r2': float(r2_full),
    'b_gold_chars': float(b_chars),
    'b_gold_named_facts': float(b_facts),
    'baseline_raw_mean': float(baseline_raw_mean),
    'matched_pairs_strict_tol_50': mp_strict_summary,
    'matched_pairs_nearest_neighbor': mp_nn_summary,
    'matched_pairs_imo_vs_cmo': mp_cmo_summary,
    'imo_gold_chars_range': [int(df[df['cohort']=='imo_gold']['gold_chars'].min()),
                              int(df[df['cohort']=='imo_gold']['gold_chars'].max())],
    'openalex_gold_chars_range': [int(df[df['cohort']==BASELINE_COHORT]['gold_chars'].min()),
                                   int(df[df['cohort']==BASELINE_COHORT]['gold_chars'].max())],
    'oa_slope_spec': {
        'b_chars_oa': b_chars_oa,
        'b_facts_oa': b_facts_oa,
        'r2_oa': float(r2_oa),
        'oa_mean_chars': oa_mean_chars,
        'oa_mean_facts': oa_mean_facts,
    },
    'focus_raw': focus_sorted_raw.to_dict(orient='records'),
    'focus_adj_fe': focus_sorted_fe.to_dict(orient='records'),
    'focus_adj_oa_slope': focus_sorted_oa.to_dict(orient='records'),
}
with open(OUT / 'summary.json', 'w') as fh:
    json.dump(summary, fh, indent=2)

print('\nWrote outputs to', OUT)
