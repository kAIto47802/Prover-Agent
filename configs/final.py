from prover_agent import (
    FixProofConfig,
    FormalizationConfig,
    InitialProofConfig,
    LemmaGenerationConfig,
    TaskConfig,
)

max_depth = 1

verifier = "lake"

# fmt: off

lean_header = (
    "import Mathlib\n"
    "import Aesop\n"
    "\n"
    "set_option maxHeartbeats 0\n"
    "\n"
    "open BigOperators Real Nat Topology Rat"
)

nl_proof = TaskConfig(
    model="deepseek-ai/DeepSeek-R1-0528-Qwen3-8B",
    filename="proof.txt",
    prompt=(
        "Your goal is to implement the following theorem, using Lean 4 and the mathlib library:\n"
        "\n"
        "```lean4\n"
        "{lean_header}\n"
        "\n"
        "\n"
        "{theorem}\n"
        "```\n"
        "\n"
        "First, provide a step-by-step proof in English.\n"
        "DO NOT write Lean code here yet--just write the proof in English.\n"
    ),
    runner_type="openai_api",
    messages=lambda prompt: [
        {"role": "user", "content": prompt},
    ],
    extract_output_format="all",
    output_start_marker="</think>",
    forbidden_strings=["```"],
    code_comment_type="code",
)

initial_proof = InitialProofConfig(
    model="Goedel-LM/Goedel-Prover-V2-8B",
    filename="Main.lean",
    prompt=(
        "Your goal is to implement the following theorem, using Lean 4 and the mathlib library:\n"
        "\n"
        "```lean4\n"
        "{lean_header}\n"
        "\n"
        "\n"
        "{theorem}\n"
        "```\n"
        "\n"
        "The English proof is as follows:\n"
        "```text\n"
        "{nl_proof}\n"
        "```\n"
        "\n"
        "Complete the following Lean 4 code:\n"
        "\n"
        "```lean4\n"
        "{lean_header}\n"
        "\n"
        "{theorem}\n"
        "```\n"
        "\n"
        "Before producing the Lean 4 code to formally prove the given theorem, provide a detailed proof plan outlining the main proof steps and strategies.\n"
        "The plan should highlight key ideas, intermediate lemmas, and proof structures that will guide the construction of the final formal proof."
    ),
    runner_type="openai_api",
    messages=lambda prompt: [
        {"role": "system", "content": "You are an expert in mathematics and Lean 4."},
        {"role": "user", "content": prompt},
    ],
    extract_output_format="code",
    output_prefix=(
        "{lean_header}\n"
        "\n"
        "\n"
    ),
    required_contents=[
        (
            "{lean_header}\n"
            "\n"
            "\n"
            "{theorem}"
        ),
    ],
    code_comment_type="code",
    num_selections=[100, 20],
)

fix_proof = FixProofConfig(
    model="Goedel-LM/Goedel-Prover-V2-8B",
    filename="fix.lean",
    prompt=(
        "Your goal is to implement the following theorem, using Lean 4 and the mathlib library:\n"
        "\n"
        "```lean4\n"
        "{lean_header}\n"
        "\n"
        "\n"
        "{theorem}\n"
        "```\n"
        "\n"
        "Your proof is as follows:\n"
        "```lean4\n"
        "{prev_code}\n"
        "```\n"
        "\n"
        "The proof failed to compile with errors.\n"
        "The error occurred at the following line(s):\n"
        "\n"
        "{error_line_messages}\n"
        "\n"
        "Fix these errors and complete the following Lean 4 code:\n"
        "\n"
        "```lean4\n"
        "{lean_header}\n"
        "\n"
        "\n"
        "{theorem}\n"
        "```\n"
        "\n"
        "Before producing the Lean 4 code to formally prove the given theorem, provide a detailed proof plan outlining the main proof steps and strategies.\n"
        "The plan should highlight key ideas, intermediate lemmas, and proof structures that will guide the construction of the final formal proof."
    ),
    error_line_message=(
        "Error line (line {error_line}):\n"
        "```lean4\n"
        "{error_code}\n"
        "```\n"
        "Error message:\n"
        "```lean4\n"
        "{error_message}\n"
        "```\n"
    ),
    runner_type="openai_api",
    messages=lambda prompt: [
        {"role": "system", "content": "You are an expert in mathematics and Lean 4."},
        {"role": "user", "content": prompt},
    ],
    extract_output_format="code",
    output_prefix=(
        "{lean_header}\n"
        "\n"
        "\n"
    ),
    required_contents=[
        (
            "{lean_header}\n"
            "\n"
            "\n"
            "{theorem}"
        ),
    ],
    max_fix_prompt_lines=300,
    max_fix_attempts=[100, 20],
    code_comment_type="code",
)


lemma_generation = LemmaGenerationConfig(
    model="deepseek-ai/DeepSeek-R1-0528-Qwen3-8B",
    filename="lemmas.txt",
    prompt=(
        "I am trying to code (prove) the following theorem in Lean 4.\n"
        "\n"
        "```lean4\n"
        "{lean_header}\n"
        "\n"
        "\n"
        "{theorem}\n"
        "```\n"
        "\n"
        "Derive {num_lemmas} lemmas related to the theorem.\n"
        "The related lemmas are those that could serve as subpropositions, subgoals, or specific cases for the theorem.\n"
        "For example, consider treating the case where a specific value is substituted for one of the variables appearing in the theorem as a lemma.\n"
        "For each lemma, clearly state the assumptions and the conclusion using mathematical expressions in English.\n"
        "Include any assumptions from the original theorem as needed in each lemma, "
        "so that each lemma contains all the necessary and sufficient assumptions to be provable on its own.\n"
        "You do not need to write the proofs or the Lean code for each lemma at this point.\n"
        "Follow the format below for each lemma:\n"
        "\n"
        "```\n"
        "### Lemma 1: <Lemma Name>\n"
        "**Assumptions**:\n"
        "<Assumptions in English>\n"
        "\n"
        "**Conclusion**:\n"
        "<Conclusion in English>\n"
        "```\n"
        "Do not include any explanations or additional text outside of the specified format."
    ),
    runner_type="openai_api",
    messages=lambda prompt: [
        {"role": "user", "content": prompt},
    ],
    extract_output_format="all",
    output_start_marker="</think>",
    forbidden_strings=["```"],
)

formalization = FormalizationConfig(
    model="Goedel-LM/Goedel-Formalizer-V2-8B",
    filename="lemma.lean",
    prompt=(
        "Please autoformalize the following natural language problem statement in Lean 4. "
        "Use the following theorem name: {problem_name}\n"
        "The natural language statement is: \n"
        "{nl_statement}"
        "\n"
        "Think before you provide the lean statement."
    ),
    runner_type="openai_api",
    messages=lambda prompt: [
        {"role": "system", "content": "You are an expert in mathematics and Lean 4."},
        {"role": "user", "content": prompt},
    ],
    split_marker="### Lemma",
    extract_output_format="code",
    lemma_format=(
        "{lean_header}\n"
        "\n"
        "\n"
        "{lemma}"
    ),
)

integration = InitialProofConfig(
    model="Goedel-LM/Goedel-Prover-V2-8B",
    filename="Main.lean",
    prompt=(
        "Based on these lemmas, construct and complete the following Lean 4 code:"
        "\n"
        "```lean4\n"
        "{lean_header}\n"
        "\n"
        "\n"
        "{lemmas}\n"
        "\n"
        "{theorem}\n"
        "```\n"
        "\n"
        "Before producing the Lean 4 code to formally prove the given theorem, provide a detailed proof plan outlining the main proof steps and strategies.\n"
        "The plan should highlight key ideas, intermediate lemmas, and proof structures that will guide the construction of the final formal proof."
    ),
    runner_type="openai_api",
    messages=lambda prompt: [
        {"role": "system", "content": "You are an expert in mathematics and Lean 4."},
        {"role": "user", "content": prompt},
    ],
    extract_output_format="code",
    output_prefix=(
        "{lean_header}\n"
        "\n"
        "\n"
        "{lemmas}\n"
        "\n"
    ),
    required_contents=[
        "{lean_header}",
        "{theorem}"
    ],
    num_selections=100,
    code_comment_type="code",
)

fix_integration = FixProofConfig(
    model="Goedel-LM/Goedel-Prover-V2-8B",
    filename="fix.lean",
    prompt=(
        "Your goal is to implement the following theorem, using Lean 4 and the mathlib library:\n"
        "\n"
        "```lean4\n"
        "{lean_header}\n"
        "\n"
        "\n"
        "{theorem}\n"
        "```\n"
        "\n"
        "Based on lemmas, you are trying to construct the proof for the theorem.\n"
        "Your proof is as follows:\n"
        "```lean4\n"
        "{prev_code}\n"
        "```\n"
        "\n"
        "The proof failed to compile with errors.\n"
        "The error occurred at the following line(s):\n"
        "\n"
        "{error_line_messages}\n"
        "\n"
        "Fix the errors and complete the following Lean 4 code\n"
        "\n"
        "```lean4\n"
        "{lean_header}\n"
        "\n"
        "\n"
        "{lemmas}\n"
        "\n"
        "{theorem}\n"
        "```\n"
        "\n"
        "Before producing the Lean 4 code to formally prove the given theorem, provide a detailed proof plan outlining the main proof steps and strategies.\n"
        "The plan should highlight key ideas, intermediate lemmas, and proof structures that will guide the construction of the final formal proof."
    ),
    error_line_message=(
        "Error line (line {error_line}):\n"
        "```lean4\n"
        "{error_code}\n"
        "```\n"
        "Error message:\n"
        "```lean4\n"
        "{error_message}\n"
        "```\n"
    ),
    runner_type="openai_api",
    messages=lambda prompt: [
        {"role": "system", "content": "You are an expert in mathematics and Lean 4."},
        {"role": "user", "content": prompt},
    ],
    extract_output_format="code",
    output_prefix=(
        "{lean_header}\n"
        "\n"
        "\n"
        "{lemmas}\n"
        "\n"
    ),
    required_contents=[
        "{lean_header}",
        "{theorem}"
    ],
    max_fix_attempts=100,
    max_fix_prompt_lines=300,
    code_comment_type="code",
)
