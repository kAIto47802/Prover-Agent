#!/bin/bash

# Start the vLLM server
./serve.sh &
sleep 180 # Wait for the server to be ready

# Start the LiteLLM proxy server
litellm --config server_config.yaml &
sleep 10 # Wait for the server to be ready

# Run Prover Agent on the MiniF2F benchmark
python dispatch_benchmark.py \
  --benchmark miniF2F \
  --phase test \
  --num_workers 16 # Adjust according to your machine specifications