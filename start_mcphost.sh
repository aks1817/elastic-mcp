#!/bin/bash

# Change to the script's directory
cd "$(dirname "$0")"

# Pre-load the Ollama model to avoid hanging
echo "Pre-loading Ollama model qwen2.5..."
curl -s http://localhost:11434/api/generate -d '{"model": "qwen2.5", "prompt": "test", "stream": false}' > /dev/null

if [ $? -eq 0 ]; then
    echo "Model pre-loaded successfully. Starting mcphost..."
    echo ""
    # Run mcphost with debug mode to see what's happening
    # Remove --debug if you don't want verbose output
    mcphost --debug -m ollama:qwen2.5 --config ./elastic-mcp-config.json --system-prompt "$(cat explicit_prompt.txt)"
else
    echo "Error: Failed to pre-load model. Make sure Ollama is running."
    echo "Start Ollama with: ollama serve"
    exit 1
fi

