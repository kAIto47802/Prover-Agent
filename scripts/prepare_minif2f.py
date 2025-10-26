# This script loads the preprocessed MiniF2F dataset, which we uploaded to Hugging Face Datasets for convenience,
# as suggested in https://github.com/kAIto47802/Prover-Agent/issues/1.
# It produces the same output as _prepare_minif2f_from_original.py
# See _prepare_minif2f_from_original.py for the preprocessing details.

import json
from pathlib import Path

from datasets import load_dataset

data = load_dataset(
    "kAIto47802/minif2f-test",
    split="test",
).to_dict()["formal_statement"]


out_dir = Path("data/miniF2F")
out_dir.mkdir(parents=True, exist_ok=True)

(out_dir / "test.json").write_text(json.dumps(data, indent=2))

print(f"MiniF2F dataset prepared successfully and saved to {out_dir / 'test.json'}")
