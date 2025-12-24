#!/bin/bash

echo "Testing MCP server connection..."
echo ""

# Test 1: Check if MCP server can be started
echo "Test 1: Starting MCP server directly..."
timeout 2 python3 mcp_server.py <<EOF
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}
{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}
EOF
echo ""
echo "MCP server test completed."
echo ""

# Test 2: Check if mcphost can connect to Ollama without config
echo "Test 2: Testing mcphost without config (should work)..."
echo "test" | timeout 5 /Users/iram/go/bin/mcphost -m ollama:qwen2.5 2>&1 | grep -E "(Model loaded|tools|error|Error)" | head -5
echo ""

# Test 3: Check config file
echo "Test 3: Checking config file..."
python3 -c "import json; config = json.load(open('elastic-mcp-config.json')); print('Config valid:', json.dumps(config, indent=2))"
echo ""

echo "If Test 2 shows 'Model loaded' but 'Loaded 0 tools', the MCP server isn't connecting."
echo "If mcphost hangs at 'Loading Ollama Model...', it might actually be stuck on MCP server initialization."

