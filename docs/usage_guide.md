<h1 align="center">
  <a href="https://github.com/kAIto47802/Prover-Agent/blob/main/docs/usage_guide.md">
    <img width="94%" height="14px" src="_images/titleLine3t.svg">
  </a>
  <div>📘 Usage Guide for Prover Agent 📘<div>
  <a href="https://github.com/kAIto47802/Prover-Agent/blob/main/docs/usage_guide.md">
    <img width="94%" height="6px" src="_images/titleLine3b.svg">
  </a>
</h1>

<h2 align="center">
  <div>📌　Run on a Specific Theorem　📌</div>
  <a href="https://github.com/kAIto47802/Prover-Agent/blob/main/README.md">
    <img width="80%" height="15px" src="_images/line2.svg" />
  </a>
</h2>

If you'd like to run Prover Agent on a specific theorem rather than on a benchmark set, please set the `theorem` variable in the configuration file (e.g., `config/final.py`). For example:

```python
# config/final.py

theorem = """
import Mathlib
import Aesop

set_option maxHeartbeats 0

open BigOperators Real Nat Topology Rat

theorem mathd_algebra_478 (b h v : ℝ) (h₀ : 0 < b ∧ 0 < h ∧ 0 < v) (h₁ : v = 1 / 3 * (b * h))
    (h₂ : b = 30) (h₃ : h = 13 / 2) : v = 65 := by
    sorry
""".strip()
```

Once you've set the theorem and started the LLM servers as described in the [README](../README.md), you can run Prover Agent as follows:

```bash
python -m prover_agent.pipelines.whole_process
```

<h2 align="center">
  <div>✂️　Run on a Specific Stage of the Workflow　✂️</div>
  <a href="https://github.com/kAIto47802/Prover-Agent/blob/main/README.md">
    <img width="80%" height="15px" src="_images/line2.svg" />
  </a>
</h2>

If you'd like to run a specific stage in the Prover Agent workflow, you can use the following entry points:

```bash
# Run only the direct proving stage
python -m prover_agent.pipelines.proof

# Run only the lemma generation stage
python -m prover_agent.pipelines.lemma_generation

# Run only the final synthesis stage
python -m prover_agent.pipelines.integration
```

To execute these stages on a benchmark set, specify the corresponding entry function as follows:

```bash
# Run only the direct proving stage
python dispatch_benchmark.py --dispatch_fn make_proof

# Run only the lemma generation stage
python dispatch_benchmark.py --dispatch_fn generate_lemmas

# Run only the final synthesis stage
python dispatch_benchmark.py --dispatch_fn integrate_lemmas
```

Note that you must either set the proved lemmas in the `lemmas` variable (`list[str]`) within the configuration file (e.g., `config/final.py`),
or specify the log directories that contain the proved lemmas to resume from.



<h2 align="center">
  <div>🎯 Other Options You Can Specify　🎯</div>
  <a href="https://github.com/kAIto47802/Prover-Agent/blob/main/README.md">
    <img width="80%" height="15px" src="_images/line2.svg" />
  </a>
</h2>

For more information on additional options, refer to the help message of each entry point:

```bash
# Help message for the whole process pipeline
python -m prover_agent.pipelines.whole_process --help

# Help message for the benchmark dispatch script
python dispatch_benchmark.py --help
```
