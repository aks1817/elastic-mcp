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

Run mcphost with the MCP server and system prompt:

```bash
mcphost -m ollama:qwen2.5 --config ./elastic-mcp-config.json --system-prompt "Elasticsearch expert. For queries: 1. Call list_indices with index_pattern='*'. 2. Call get_mappings for each index. 3. Call sample_docs for each index. 4. Based on schema, output ONLY the query DSL JSON(s) for _search. No execution."
```

This starts an interactive session.

### Example Queries

Type these prompts and get DSL outputs:

1. **List indices**:

   ```
   Show me all indices
   ```

   Output: Indices list.

2. **Simple query**:

   ```
   Find all Tesla vehicles
   ```

   Output:

   ```json
   {
     "query": {
       "match": {
         "make": "Tesla"
       }
     }
   }
   ```

3. **Complex relational query**:

   ```
   Find people who own cars worth 40k or more
   ```

   Output (multiple DSLs):

   ```json
   // 1. Find vehicles over $40k
   {
     "query": {
       "range": {
         "price": {
           "gt": 40000
         }
       }
     }
   }

   // 2. Find registrations for those vehicle_ids
   {
     "query": {
       "terms": {
         "vehicle_id": [1, 4]
       }
     }
   }

   // 3. Find people for those person_ids
   {
     "query": {
       "terms": {
         "id": [1, 2, 4]
       }
     }
   }
   ```

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
- **mcphost errors**: Ensure PATH and config file.
- **Tool call errors**: The custom MCP server avoids Docker issues.
- **No data**: Re-run `python3 seed_data.py`.
- **Storage issues**: Use smaller ES heap or remove unused Ollama models.

## Extending

- Add more data in `seed_data.py`.
- Modify `mcp_server.py` for custom tools.
- Integrate with UI (e.g., Streamlit) to run DSL automatically.

For issues, check logs or refer to [MCP docs](https://modelcontextprotocol.io).</content>
