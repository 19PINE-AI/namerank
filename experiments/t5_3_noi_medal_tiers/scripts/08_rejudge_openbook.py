"""Re-judge the complete NOI 2009 medal roster under the ADOPTED judge — the
tightened open-book recognition judge (anti-confabulation; correct for a
competition cohort). Responses are reused from the retained probe checkpoint
(no re-probe). Also judges the protocol-matched synthetic-NOI floor (the t6
fictional NOI medalists) so the noise floor the appendix flagged as
"not yet quoted" can be reported.

Metric: NameRank-detect(medalist) = fraction of the 36-model panel that
recognizes the person (refusals = not recognized).

Writes outputs/tier_openbook_per_entity.csv, outputs/tier_openbook_summary.json
"""
from __future__ import annotations

import json
import os
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
from google import genai
from google.genai import types as genai_types

HERE = Path(__file__).resolve().parent.parent
REPO = HERE.parent.parent
T6 = REPO / "experiments" / "t6_v2_protocol"
TPL = (T6 / "inputs" / "judge_prompt_v3_tightened.txt").read_text()

SCHEMA = {"type": "object", "properties": {
    "recognized": {"type": "boolean"}, "coverage": {"type": "number"},
    "accuracy": {"type": "number"}, "rationale": {"type": "string"}},
    "required": ["recognized", "coverage", "accuracy", "rationale"]}
SYS = ("You are an objective grader judging whether a language model genuinely "
       "recognizes a specific named entity. Use knowledge freely to refute, but "
       "credit only positively-verified non-guessable facts; for competition "
       "participants you lack reliable per-individual memory, so credit only "
       "gold-present facts or major widely-documented achievements — never "
       "confabulated verification.")
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])


def judge(name, ctx, gold, resp):
    for a in range(4):
        try:
            r = client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=TPL.format(name=name, context=ctx, gold_answer=gold,
                                    response=resp),
                config=genai_types.GenerateContentConfig(
                    system_instruction=SYS, temperature=0.0,
                    response_mime_type="application/json", response_schema=SCHEMA))
            return bool(json.loads(r.text)["recognized"])
        except Exception:
            if a == 3:
                return None
            time.sleep(2 * (a + 1))


def cliffs_delta(a, b):
    a, b = np.array(a), np.array(b)
    gt = sum((x > b).sum() for x in a)
    lt = sum((x < b).sum() for x in a)
    return (gt - lt) / (len(a) * len(b))


def main():
    ents = {e["id"]: e for e in json.loads(
        (HERE / "inputs" / "tier_entities.json").read_text())}
    gold = json.loads((HERE / "outputs" / "canonical_golds_norm.json").read_text())
    gold = {k: (v if isinstance(v, str) else v.get("gold", "")) for k, v in gold.items()}
    # responses from retained checkpoint
    resp = json.loads((HERE / "outputs" / "_rejudge_v2_ckpt.json").read_text())

    # synthetic NOI floor entities from t6
    syn_e = {e["id"]: e for e in json.loads(
        (T6 / "inputs" / "pilot_entities_v2.json").read_text())
        if e.get("cohort") == "synthetic_noi_v2"}
    syn_gold = json.loads((T6 / "inputs" / "gold_answers_v2.json").read_text())
    syn_resp = []
    for line in open(T6 / "outputs" / "full_v2_results.jsonl"):
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        if r["entity_id"] in syn_e:
            syn_resp.append(r)

    out_path = HERE / "outputs" / "_openbook_ckpt.json"
    done = json.loads(out_path.read_text()) if out_path.exists() else {}

    NOI = {"noi_china_gold", "noi_china_silver", "noi_china_bronze"}
    tasks = []
    # NOI roster: only 2009 entities (exclude the 9 non-2009 gold controls to
    # match the "complete NOI 2009 roster" framing) — keep those with _2009 id
    for r in resp:
        e = ents.get(r["entity_id"])
        if not e or e["cohort"] not in NOI:
            continue
        key = f"{r['entity_id']}|{r['model_id']}"
        if key in done:
            continue
        if r["is_refusal"]:
            done[key] = 0
        elif r["entity_id"] in gold:
            tasks.append(("noi", r, e, gold[r["entity_id"]]))
    for r in syn_resp:
        e = syn_e[r["entity_id"]]
        key = f"{r['entity_id']}|{r['model_id']}"
        if key in done:
            continue
        if r["is_refusal"]:
            done[key] = 0
        else:
            tasks.append(("syn", r, e, syn_gold[r["entity_id"]]))
    print(f"re-judging {len(tasks)} answered records (tightened open-book)")

    def work(item):
        _, r, e, g = item
        rec = judge(e["name"], e["context"], g, r["response"])
        return f"{r['entity_id']}|{r['model_id']}", (0 if rec is None else int(rec))

    n = 0
    with ThreadPoolExecutor(max_workers=8) as ex:
        for fut in as_completed([ex.submit(work, t) for t in tasks]):
            k, v = fut.result()
            done[k] = v
            n += 1
            if n % 300 == 0:
                out_path.write_text(json.dumps(done))
                print(f"  {n}/{len(tasks)}", flush=True)
    out_path.write_text(json.dumps(done))

    # per-entity panel recognition
    def panel(eid, allmods):
        got = [done.get(f"{eid}|{m}", 0) for m in allmods]
        return np.mean(got) if got else np.nan
    mods_of = defaultdict(set)
    for r in resp:
        mods_of[r["entity_id"]].add(r["model_id"])
    for r in syn_resp:
        mods_of[r["entity_id"]].add(r["model_id"])

    rows = []
    for eid, e in ents.items():
        if e["cohort"] not in NOI or not eid.endswith("_2009"):
            continue
        m = mods_of.get(eid)
        if not m or len(m) < 30:
            continue
        rows.append({"entity_id": eid, "name": e["name"],
                     "tier": e["cohort"].split("_")[-1],
                     "recognition": panel(eid, m)})
    import csv
    with open(HERE / "outputs" / "tier_openbook_per_entity.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["entity_id", "name", "tier", "recognition"])
        w.writeheader(); w.writerows(rows)

    tiers = {t: [r["recognition"] for r in rows if r["tier"] == t]
             for t in ("gold", "silver", "bronze")}
    syn_vals = [panel(eid, mods_of[eid]) for eid in syn_e if eid in mods_of]

    summ = {"floor_synthetic_noi": float(np.mean(syn_vals)) if syn_vals else None,
            "n_synthetic": len(syn_vals), "tiers": {}}
    for t, v in tiers.items():
        v = [x for x in v if not np.isnan(x)]
        summ["tiers"][t] = {"n": len(v), "mean": float(np.mean(v)),
                            "median": float(np.median(v)),
                            "silent_zero": int(sum(x == 0 for x in v)),
                            "recognized_any": int(sum(x > 0 for x in v))}
    try:
        from scipy import stats as st
        H, p = st.kruskal(tiers["gold"], tiers["silver"], tiers["bronze"])
        summ["kruskal_H"], summ["kruskal_p"] = float(H), float(p)
        summ["cliff_gold_silver"] = float(cliffs_delta(tiers["gold"], tiers["silver"]))
        summ["cliff_silver_bronze"] = float(cliffs_delta(tiers["silver"], tiers["bronze"]))
        summ["mwu_silver_bronze_p"] = float(
            st.mannwhitneyu(tiers["silver"], tiers["bronze"], alternative="two-sided")[1])
    except Exception as e:  # noqa: BLE001
        summ["stats_error"] = str(e)
    (HERE / "outputs" / "tier_openbook_summary.json").write_text(
        json.dumps(summ, indent=2))
    print(json.dumps(summ, indent=2))
    top = sorted(rows, key=lambda r: -r["recognition"])[:8]
    print("\ntop recognized medalists:")
    for r in top:
        print(f"  {r['name']:26s} {r['tier']:6s} {r['recognition']:.3f}")


if __name__ == "__main__":
    main()
