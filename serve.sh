#!/bin/bash

for i in {0..2}; do
    CUDA_VISIBLE_DEVICES=$((i*2)) vllm serve \
        "deepseek-ai/DeepSeek-R1-0528-Qwen3-8B" \
        --port $((8000+i*2)) \
        --max-num-batched-tokens 16384 \
        --max-model-len 16384 \
        --tensor-parallel-size 1 &

    CUDA_VISIBLE_DEVICES=$((i*2+1)) vllm serve \
        "Goedel-LM/Goedel-Prover-V2-8B" \
        --port $((8001+i*2)) \
        --max-num-batched-tokens 16384 \
        --max-model-len 16384 \
        --tensor-parallel-size 1 &

    sleep 5
done

CUDA_VISIBLE_DEVICES=6 vllm serve \
    "deepseek-ai/DeepSeek-R1-0528-Qwen3-8B" \
    --port 8006 \
    --max-num-batched-tokens 16384 \
    --max-model-len 16384 \
    --tensor-parallel-size 1 &

CUDA_VISIBLE_DEVICES=7 vllm serve \
    "Goedel-LM/Goedel-Formalizer-V2-8B" \
    --port 8007 \
    --max-num-batched-tokens 16384 \
    --max-model-len 16384 \
    --tensor-parallel-size 1 &

wait
