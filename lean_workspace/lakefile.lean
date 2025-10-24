import Lake
open Lake DSL

-- Using the same mathlib commit hash as the following repositories:
-- - https://github.com/deepseek-ai/DeepSeek-Prover-V1.5
-- - https://github.com/Goedel-LM/Goedel-Prover
-- - https://github.com/Goedel-LM/Goedel-Prover-V2
require mathlib from git
  "https://github.com/xinhjBrant/mathlib4" @ "2f65ba7f1a9144b20c8e7358513548e317d26de1"


package «LeanWorkspace»

@[default_target]
lean_exe «LeanWorkspace» where
  root := `Main
