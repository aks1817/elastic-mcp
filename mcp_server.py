import asyncio
import json
import sys
import requests

ES_URL = "http://localhost:9200"

class MCPServer:
    def __init__(self):
        self.tools = {
            "list_indices": {
                "name": "list_indices",
                "description": "List all Elasticsearch indices",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "index_pattern": {"type": "string", "description": "Pattern to match indices, e.g., '*'"}
                    },
                    "required": ["index_pattern"]
                }
            },
            "get_mappings": {
                "name": "get_mappings",
                "description": "Get mapping for an index",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "index": {"type": "string", "description": "Index name"}
                    },
                    "required": ["index"]
                }
            },
            "sample_docs": {
                "name": "sample_docs",
                "description": "Get sample documents from an index",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "index": {"type": "string", "description": "Index name"},
                        "size": {"type": "integer", "description": "Number of docs", "default": 5}
                    },
                    "required": ["index"]
                }
            },
            "search": {
                "name": "search",
                "description": "Search an index with query",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "index": {"type": "string", "description": "Index name"},
                        "query_body": {"type": "object", "description": "Query DSL JSON"}
                    },
                    "required": ["index", "query_body"]
                }
            }
        }

    async def handle_message(self, message):
        if message.get("method") == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": message["id"],
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "elastic-mcp", "version": "1.0"}
                }
            }
        elif message.get("method") == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": message["id"],
                "result": {"tools": list(self.tools.values())}
            }
        elif message.get("method") == "tools/call":
            params = message["params"]
            tool_name = params["name"]
            args = params["arguments"]
            result = await self.call_tool(tool_name, args)
            return {
                "jsonrpc": "2.0",
                "id": message["id"],
                "result": result
            }
        return {"jsonrpc": "2.0", "id": message["id"], "error": {"code": -32601, "message": "Method not found"}}

    async def call_tool(self, name, args):
        if name == "list_indices":
            r = requests.get(f"{ES_URL}/_cat/indices?format=json&h=index")
            indices = [i["index"] for i in r.json()]
            return {"indices": indices}
        elif name == "get_mappings":
            index = args["index"]
            r = requests.get(f"{ES_URL}/{index}/_mapping")
            return r.json()
        elif name == "sample_docs":
            index = args["index"]
            size = args.get("size", 5)
            r = requests.get(f"{ES_URL}/{index}/_search", json={"size": size})
            return r.json()["hits"]["hits"]
        elif name == "search":
            index = args["index"]
            query = args["query_body"]
            r = requests.post(f"{ES_URL}/{index}/_search", json=query)
            return r.json()
        return {"error": "Tool not found"}

async def main():
    server = MCPServer()
    loop = asyncio.get_event_loop()
    while True:
        line = await loop.run_in_executor(None, sys.stdin.readline)
        if not line:
            break
        try:
            message = json.loads(line.strip())
            response = await server.handle_message(message)
            print(json.dumps(response), flush=True)
        except json.JSONDecodeError:
            continue

if __name__ == "__main__":
    asyncio.run(main())