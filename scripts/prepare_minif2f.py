import json
import re
from pathlib import Path

from datasets import load_dataset

data = load_dataset(
    "AI-MO/minif2f_test",
    split="train",
    revision="5def318348521dfc34875045a9ecddf729a2b49f",
).to_dict()["formal_statement"]


# Rename theorems that contain unintelligible parts.
# See Apendix D.1 of our paper for more details:
# - https://arxiv.org/abs/2506.19923
rename_map = {
    "numbertheory_4x3m7y3neq2003": "numbertheory",
    "algebra_sqineq_unitcircatbpabsamblt1": "algebra",
    "numbertheory_x5neqy2p4": "numbertheory",
    "induction_12dvd4expnp1p20": "induction",
    "induction_nfactltnexpnm1ngt3": "induction",
    "numbertheory_notequiv2i2jasqbsqdiv8": "numbertheory",
    "algebra_sqineq_at2malt1": "algebra",
    "algebra_apbmpcneq0_aeq0anbeq0anceq0": "algebra",
    "numbertheory_fxeq4powxp6powxp9powx_f2powmdvdf2pown": "numbertheory",
    "algebra_abpbcpcageq3_sumaonsqrtapbgeq3onsqrt2": "algebra",
    "algebra_2varlineareq_fp3zeq11_3tfm1m5zeqn68_feqn10_zeq7": "algebra",
    "induction_pord1p1on2powklt5on2": "induction",
    "numbertheory_2pownm1prime_nprime": "numbertheory",
    "induction_prod1p1onk3le3m1onn": "induction",
    "induction_sumkexp3eqsumksq": "induction",
    "algebra_bleqa_apbon2msqrtableqambsqon8b": "algebra",
    "algebra_sum1onsqrt2to1onsqrt10000lt198": "algebra",
    "algebra_others_exirrpowirrrat": "algebra",
    "algebra_9onxpypzleqsum2onxpy": "algebra",
    "algebra_absapbon1pabsapbleqsumabsaon1pabsa": "algebra",
    "algebra_sqineq_unitcircatbpamblt1": "algebra",
    "induction_pprime_pdvdapowpma": "induction",
    "algebra_ineq_nto1onlt2m1on": "algebra",
    "algebra_amgm_sumasqdivbgeqsuma": "algebra",
    "induction_1pxpownlt1pnx": "induction",
    "induction_11div10tonmn1ton": "induction",
    "algebra_amgm_sum1toneqn_prod1tonleq1": "algebra",
    "algebra_cubrtrp1oncubrtreq3_rcubp1onrcubeq5778": "algebra",
    "numbertheory_3pow2pownm1mod2pownp3eq2pownp2": "numbertheory",
    "algebra_apbpceq2_abpbcpcaeq1_aleq1on3anbleq1ancleq4on3": "algebra",
    "algebra_apbon2pownleqapownpbpowon2": "algebra",
    "numbertheory_aoddbdiv4asqpbsqmod8eq1": "numbertheory",
    "algebra_absxm1pabsxpabsxp1eqxp2_0leqxleq1": "algebra",
    "numbertheory_exk2powkeqapb2mulbpa2_aeq1": "numbertheory",
}

processed = [
    d.replace(name, rename_map[name]).strip()
    if (m := re.search(r"theorem\s+([A-Za-z0-9_']+)\b", d))
    and (name := m.group(1)) in rename_map
    else d.strip()
    for d in data
]

out_dir = Path("data/miniF2F")
out_dir.mkdir(parents=True, exist_ok=True)

(out_dir / "test.json").write_text(json.dumps(processed, indent=2))

print(f"MiniF2F dataset prepared successfully and saved to {out_dir / 'test.json'}")
