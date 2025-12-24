# Natural Language to Elasticsearch with MCP

This project sets up a system that allows you to query Elasticsearch using natural language prompts via an LLM (Ollama) and MCP (Model Context Protocol). The LLM understands the schema and generates Elasticsearch DSL queries without manual coding.

## Features

- **Natural Language Queries**: Ask questions like "Find people who own cars over $40k" and get Elasticsearch DSL.
- **Complex Relations**: Handles multi-index data with foreign keys (e.g., vehicles, people, registrations).
- **MCP Integration**: Uses MCP for tool-calling to inspect schemas dynamically.
- **Local Setup**: Runs entirely on your machine with Docker and Ollama.

## Prerequisites

- **macOS** (M1/M2/M3 supported)
- **Homebrew** installed
- **Docker Desktop** (with Apple Silicon support)
- **Python 3.8+**
- **curl** and **jq** for testing
- At least 12GB free storage

## Installation

### 1. Install Docker

Download and install Docker Desktop for Mac from [docker.com](https://www.docker.com/products/docker-desktop). Start Docker and ensure it's running.

### 2. Install Ollama

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

Pull the required model:

```bash
ollama pull qwen2.5
```

### 3. Install mcphost

Download the mcphost binary from the [MCP repository](https://github.com/modelcontextprotocol) or build from source. Place it in `~/go/bin/` and add to PATH:

```bash
export PATH="$HOME/go/bin:$PATH"
```

Verify:

```bash
mcphost --help
```

### 4. Clone or Set Up Project

Create a workspace folder:

```bash
mkdir ~/elastic-mcp
cd ~/elastic-mcp
```

Copy the following files into the folder:

- `docker-compose.yml`
- `mcp_server.py`
- `seed_data.py`
- `elastic-mcp-config.json`

## Setup

### 1. Start Elasticsearch

```bash
docker compose up -d
```

Wait for it to be ready (check logs: `docker compose logs`).

### 2. Seed Data

Run the seed script to populate with complex relational data:

```bash
python3 seed_data.py
```

This creates three indices:

- `vehicles`: Cars with id, make, model, year, type, price
- `people`: Owners with id, name, age, city
- `registrations`: Links vehicles to people with vehicle_id, person_id, reg_date, status

### 3. Verify Setup

Check indices:

```bash
curl -s http://localhost:9200/_cat/indices
```

Sample data:

```bash
curl -s http://localhost:9200/vehicles/_search?size=3 | jq
```

## Usage

### Start the System

**Option 1: Use the startup script (recommended)** - This pre-loads the model to avoid hanging:

```bash
./start_mcphost.sh
```

**Option 2: Manual start** - Run mcphost directly:

```bash
mcphost -m ollama:qwen2.5 --config ./elastic-mcp-config.json --system-prompt "Elasticsearch query generator. Steps: 1) list_indices with index_pattern='*'. 2) get_mappings for each index (call separately). 3) sample_docs for each index (call separately). 4) Analyze schema. 5) Output ONLY JSON query DSL. STRICT RULES: Output ONLY valid JSON. No explanations. No text. No markdown. No code blocks. No comments. Just pure JSON. Format: {\"index\": \"name\", \"query\": {...}} or {\"query\": {...}}. One query per line if multiple."
```

**Option 3: Use prompt file** - If you want to use the detailed prompt file:

```bash
mcphost -m ollama:qwen2.5 --config ./elastic-mcp-config.json --system-prompt "$(cat system_prompt.txt)"
```

**Note**: If mcphost gets stuck at "Loading Ollama Model...", pre-load the model first:
```bash
curl -s http://localhost:11434/api/generate -d '{"model": "qwen2.5", "prompt": "test", "stream": false}' > /dev/null
```

This starts an interactive session.

### Example Queries

Type these prompts and get DSL outputs. **Note**: The system will output ONLY JSON, no explanations.

1. **Simple query**:

   ```
   Find all Tesla vehicles
   ```

   Expected Output (ONLY JSON, no text):

   ```json
   {"index": "vehicles", "query": {"match": {"make": "Tesla"}}}
   ```

2. **Complex relational query**:

   ```
   Find people who own cars worth 40k or more
   ```

   Expected Output (ONLY JSON, one query per line):

   ```json
   {"index": "vehicles", "query": {"range": {"price": {"gte": 40000}}}}
   {"index": "registrations", "query": {"terms": {"vehicle_id": [1, 4]}}}
   {"index": "people", "query": {"terms": {"id": [1, 2, 4]}}}
   ```

**Important**: The system is configured to output ONLY JSON. All explanations, comments, and extra text are suppressed. You will receive pure query DSL JSON only.

### Manual Execution

Copy the DSL and run:

```bash
curl -X POST "http://localhost:9200/vehicles/_search" -H "Content-Type: application/json" -d '{"query": {"match": {"make": "Tesla"}}}'
```

## Files Overview

- `docker-compose.yml`: Elasticsearch container
- `mcp_server.py`: Custom MCP server (tools for ES operations)
- `seed_data.py`: Script to seed complex data
- `elastic-mcp-config.json`: MCP client config

## Troubleshooting

- **Elasticsearch not starting**: Check Docker and ports (9200).
- **Ollama model not loading**: `ollama list` and `ollama pull qwen2.5`.
- **mcphost stuck at "Loading Ollama Model..."**: 
  - This is a common issue where mcphost hangs while trying to load the model.
  - **Solution 1**: Pre-load the model before running mcphost:
    ```bash
    curl -s http://localhost:11434/api/generate -d '{"model": "qwen2.5", "prompt": "test", "stream": false}' > /dev/null
    mcphost -m ollama:qwen2.5 --config ./elastic-mcp-config.json --system-prompt "..."
    ```
  - **Solution 2**: Use the provided startup script:
    ```bash
    ./start_mcphost.sh
    ```
  - **Solution 3**: Try using the full model name:
    ```bash
    mcphost -m ollama:qwen2.5:latest --config ./elastic-mcp-config.json --system-prompt "..."
    ```
  - **Solution 4**: Ensure Ollama is running and accessible:
    ```bash
    curl http://localhost:11434/api/tags
    ```
  - **Solution 5**: If still hanging, try a smaller model variant:
    ```bash
    ollama pull qwen2.5:3b
    mcphost -m ollama:qwen2.5:3b --config ./elastic-mcp-config.json --system-prompt "..."
    ```
- **mcphost errors**: Ensure PATH and config file.
- **Tool call errors**: The custom MCP server avoids Docker issues.
- **No data**: Re-run `python3 seed_data.py`.
- **Storage issues**: Use smaller ES heap or remove unused Ollama models.

## Extending

- Add more data in `seed_data.py`.
- Modify `mcp_server.py` for custom tools.
- Integrate with UI (e.g., Streamlit) to run DSL automatically.

For issues, check logs or refer to [MCP docs](https://modelcontextprotocol.io).</content>
