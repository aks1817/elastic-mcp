import asyncio
import json
import sys
import requests
import os
import fnmatch
import re

# Ensure unbuffered output for MCP communication
sys.stdout.reconfigure(line_buffering=True) if hasattr(sys.stdout, 'reconfigure') else None
os.environ['PYTHONUNBUFFERED'] = '1'

ES_URL = "http://localhost:9200"

class MCPServer:
    def __init__(self):
        self.tools = {
            "list_indices": {
                "name": "list_indices",
                "description": "List all Elasticsearch indices. CRITICAL: Pass arguments as a SINGLE JSON object like {\"index_pattern\": \"*\"}. NEVER concatenate multiple JSON objects.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "index_pattern": {"type": "string", "description": "Pattern to match indices, e.g., '*'. Pass as a SINGLE JSON object: {\"index_pattern\": \"*\"}. Do NOT concatenate with other JSON objects."}
                    },
                    "required": ["index_pattern"],
                    "examples": [
                        {"index_pattern": "*"}
                    ],
                    "additionalProperties": False
                }
            },
            "get_mappings": {
                "name": "get_mappings",
                "description": "Get mapping for ONE index only. CRITICAL: Make ONE call at a time. Pass arguments as a SINGLE JSON object like {\"index\": \"vehicles\"}. Call this tool ONCE per index, WAIT for response, then make the NEXT call. NEVER pass multiple indices like {\"index\": \"vehicles\"}{\"index\": \"people\"} - that is INVALID JSON and will fail. SEQUENTIAL CALLS REQUIRED: Call 1 → wait → Call 2 → wait → Call 3.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "index": {"type": "string", "description": "ONE index name only (e.g., 'vehicles'). Pass as SINGLE JSON object: {\"index\": \"vehicles\"}. To query multiple indices, make SEPARATE SEQUENTIAL tool calls - one call per index, wait for response, then next call. NEVER concatenate like {\"index\": \"vehicles\"}{\"index\": \"people\"} or \"index\":\"vehicles\"}{\"index\":\"people\"."}
                    },
                    "required": ["index"],
                    "examples": [
                        {"index": "vehicles"},
                        {"index": "people"},
                        {"index": "registrations"}
                    ],
                    "additionalProperties": False
                }
            },
            "sample_docs": {
                "name": "sample_docs",
                "description": "Get sample documents from ONE index only. CRITICAL: Make ONE call at a time. Pass arguments as a SINGLE JSON object like {\"index\": \"vehicles\", \"size\": 5}. Call this tool ONCE per index, WAIT for response, then make the NEXT call. NEVER pass multiple indices like {\"index\": \"vehicles\"}{\"index\": \"people\"} - that is INVALID JSON and will fail. SEQUENTIAL CALLS REQUIRED.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "index": {"type": "string", "description": "ONE index name only. Pass as SINGLE JSON object: {\"index\": \"vehicles\"} or {\"index\": \"vehicles\", \"size\": 5}. To query multiple indices, make SEPARATE SEQUENTIAL tool calls - one call per index, wait for response, then next call. NEVER concatenate multiple JSON objects."},
                        "size": {"type": "integer", "description": "Number of sample documents to return", "default": 5}
                    },
                    "required": ["index"],
                    "examples": [
                        {"index": "vehicles", "size": 5},
                        {"index": "people", "size": 5}
                    ],
                    "additionalProperties": False
                }
            },
            "search": {
                "name": "search",
                "description": "Search an index with query. CRITICAL: Pass arguments as a SINGLE JSON object like {\"index\": \"vehicles\", \"query_body\": {...}}. NEVER concatenate multiple JSON objects.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "index": {"type": "string", "description": "Index name. Pass as part of a SINGLE JSON object."},
                        "query_body": {"type": "object", "description": "Query DSL JSON object. Pass as part of a SINGLE JSON object with index."}
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
            args = params.get("arguments", {})
            try:
                # Validate and normalize arguments
                if isinstance(args, str):
                    # Check for missing opening brace OR concatenated JSON (common error where model generates "index":"value"}{...)
                    if not args.strip().startswith('{') and ('}' in args or '"index"' in args):
                        # Try to find where JSON should start
                        if '"index"' in args:
                            index_matches = re.findall(r'"index"\s*:\s*"([^"]+)"', args)
                            if index_matches:
                                if len(index_matches) > 1:
                                    # Multiple indices detected - very clear error
                                    error_msg = ("CRITICAL ERROR: You are trying to pass " + str(len(index_matches)) + 
                                               " indices in ONE tool call: " + ", ".join(index_matches) + 
                                               ". This is FORBIDDEN. You MUST make SEPARATE tool calls - ONE call per index. " +
                                               "Example: Call 1 with {\"index\": \"" + index_matches[0] + "\"}, " +
                                               "then wait for response, then Call 2 with {\"index\": \"" + index_matches[1] + "\"}. " +
                                               "NEVER combine them like \"index\":\"" + index_matches[0] + "\"}{\"index\":\"" + index_matches[1] + "\"}.")
                                else:
                                    correct_format = '{"index": "' + index_matches[0] + '"}'
                                    error_msg = ("ERROR: Invalid JSON - missing opening brace. You generated: \"index\":\"" + 
                                               index_matches[0] + "\"}{...}. This is INVALID. Each tool call must start with { and end with }. " +
                                               "CORRECT: " + correct_format + ". Make SEPARATE calls for each index.")
                                raise ValueError(error_msg)
                    
                    # Check for multiple JSON objects concatenated (common error)
                    if args.count('{') > 1 and args.count('}') > 1:
                        # Try to extract the first valid JSON object
                        brace_count = 0
                        first_end = -1
                        for i, char in enumerate(args):
                            if char == '{':
                                brace_count += 1
                            elif char == '}':
                                brace_count -= 1
                                if brace_count == 0:
                                    first_end = i + 1
                                    break
                        
                        if first_end > 0 and first_end < len(args):
                            # Extract just the first JSON object
                            first_json = args[:first_end].strip()
                            remaining = args[first_end:].strip()
                            
                            # Check if it looks like MCP response format was included
                            if '"content"' in remaining or '"text"' in remaining:
                                raise ValueError(f"ERROR: Invalid JSON format. You're including MCP response content in tool arguments. Tool arguments must be ONLY the parameters. CORRECT format: {{\"index\": \"vehicles\"}}. WRONG format: {{\"index\": \"vehicles\"}}{{\"content\": [...]}}. Call {tool_name} with ONLY the parameter, nothing else.")
                            
                            # Check if remaining looks like more index parameters
                            if '"index"' in remaining and tool_name in ["get_mappings", "sample_docs"]:
                                # Try to extract indices from the full string
                                index_matches = re.findall(r'"index"\s*:\s*"([^"]+)"', args)
                                if index_matches and len(index_matches) > 1:
                                    raise ValueError(f"ERROR: Invalid JSON - multiple indices in one call. You passed {len(index_matches)} indices: {', '.join(index_matches)}. You MUST make SEPARATE tool calls - one call per index. CORRECT: Call 1 with {{\"index\": \"{index_matches[0]}\"}}, then Call 2 with {{\"index\": \"{index_matches[1]}\"}}, etc. WRONG: {{\"index\": \"{index_matches[0]}\"}}{{\"index\": \"{index_matches[1]}\"}} - this is invalid JSON.")
                                else:
                                    raise ValueError(f"ERROR: Invalid JSON - multiple JSON objects detected. You're concatenating JSON objects like {{\"index\": \"vehicles\"}}{{\"index\": \"people\"}}. This is INVALID. Make SEPARATE tool calls. CORRECT: First call {{\"index\": \"vehicles\"}}, then second call {{\"index\": \"people\"}}.")
                            else:
                                raise ValueError(f"ERROR: Invalid JSON - multiple JSON objects detected. You're concatenating JSON objects. Make SEPARATE tool calls. CORRECT: First call {{\"index\": \"vehicles\"}}, then second call {{\"index\": \"people\"}}. WRONG: {{\"index\": \"vehicles\"}}{{\"index\": \"people\"}}.")
                    
                    # Check for MCP response format in arguments (common mistake)
                    if '"content"' in args or '"text"' in args or '"type":"text"' in args:
                        raise ValueError(f"ERROR: Invalid JSON - MCP response format detected in tool arguments. Tool arguments must be ONLY the parameters. CORRECT: {{\"index\": \"vehicles\"}}. WRONG: {{\"index\": \"vehicles\"}}{{\"content\": [...]}} or {{\"text\": \"...\"}}. Use ONLY parameter values, not response objects.")
                    
                    # Try to parse if it's a string
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError as e:
                        error_msg = str(e)
                        if "after top-level value" in error_msg or args.count('{') > 1:
                            # Try to extract indices from the malformed JSON
                            index_matches = re.findall(r'"index"\s*:\s*"([^"]+)"', args)
                            if index_matches and len(index_matches) > 1:
                                raise ValueError(f"ERROR: Invalid JSON - 'after top-level value' error. You're concatenating {len(index_matches)} JSON objects: {', '.join(index_matches)}. This is INVALID JSON. You MUST make SEPARATE tool calls. CORRECT: Call 1 with {{\"index\": \"{index_matches[0]}\"}}, Call 2 with {{\"index\": \"{index_matches[1]}\"}}, etc. WRONG: {{\"index\": \"{index_matches[0]}\"}}{{\"index\": \"{index_matches[1]}\"}} - this causes the 'after top-level value' error.")
                            raise ValueError(f"ERROR: Invalid JSON - 'after top-level value' error. You're concatenating multiple JSON objects. This is INVALID. Make SEPARATE tool calls. CORRECT: First call {{\"index\": \"vehicles\"}}, then second call {{\"index\": \"people\"}}. WRONG: {{\"index\": \"vehicles\"}}{{\"index\": \"people\"}} - this causes the error.")
                        raise ValueError(f"ERROR: Invalid JSON arguments: {error_msg}. You must pass a SINGLE JSON object per tool call. CORRECT: {{\"index\": \"vehicles\"}}. WRONG: Multiple objects concatenated together. Make separate tool calls for each index/parameter.")
                elif not isinstance(args, dict):
                    raise ValueError(f"Arguments must be a dictionary, got {type(args)}")
                
                result = await self.call_tool(tool_name, args)
                # MCP protocol requires result.content array
                result_text = json.dumps(result, indent=2)
                return {
                    "jsonrpc": "2.0",
                    "id": message["id"],
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": result_text
                            }
                        ]
                    }
                }
            except json.JSONDecodeError as e:
                return {
                    "jsonrpc": "2.0",
                    "id": message["id"],
                    "error": {
                        "code": -32602,
                        "message": f"ERROR: Invalid JSON arguments: {str(e)}. You must provide a SINGLE JSON object per tool call. CORRECT: {{\"index\": \"vehicles\"}}. WRONG: Multiple objects like {{\"index\": \"vehicles\"}}{{\"index\": \"people\"}}. Make separate tool calls for each index."
                    }
                }
            except Exception as e:
                return {
                    "jsonrpc": "2.0",
                    "id": message["id"],
                    "error": {
                        "code": -32603,
                        "message": f"Tool execution error: {str(e)}"
                    }
                }
        return {"jsonrpc": "2.0", "id": message["id"], "error": {"code": -32601, "message": "Method not found"}}

    async def call_tool(self, name, args):
        # Handle tool name with or without prefix (elasticsearch__list_indices or list_indices)
        tool_name = name.replace("elasticsearch__", "") if name.startswith("elasticsearch__") else name
        
        if tool_name == "list_indices":
            index_pattern = args.get("index_pattern", "*")
            r = requests.get(f"{ES_URL}/_cat/indices?format=json&h=index")
            all_indices = [i["index"] for i in r.json()]
            # Filter by pattern if needed (simple wildcard matching)
            if index_pattern == "*":
                indices = all_indices
            else:
                indices = [idx for idx in all_indices if fnmatch.fnmatch(idx, index_pattern)]
            return {"indices": indices}
        elif tool_name == "get_mappings":
            index = args.get("index")
            if not index:
                raise ValueError("index parameter is required")
            # Check if index looks like it contains multiple indices (malformed input)
            if isinstance(index, str) and "}{" in index:
                raise ValueError(f"Invalid index parameter: '{index}'. This looks like multiple JSON objects concatenated together. Please call get_mappings separately for each index (e.g., call once with index='vehicles', then again with index='people', etc.).")
            
            # First check if index exists
            try:
                r = requests.get(f"{ES_URL}/_cat/indices/{index}?format=json")
                if r.status_code == 404 or not r.json():
                    available_indices = requests.get(f"{ES_URL}/_cat/indices?format=json&h=index").json()
                    index_names = [idx["index"] for idx in available_indices]
                    raise ValueError(f"Index '{index}' not found. Available indices: {', '.join(index_names)}")
            except requests.exceptions.RequestException:
                pass  # Continue to try the mapping request
            
            r = requests.get(f"{ES_URL}/{index}/_mapping")
            if r.status_code == 404:
                available_indices = requests.get(f"{ES_URL}/_cat/indices?format=json&h=index").json()
                index_names = [idx["index"] for idx in available_indices]
                raise ValueError(f"Index '{index}' not found (404). Available indices: {', '.join(index_names)}")
            r.raise_for_status()
            return r.json()
        elif tool_name == "sample_docs":
            index = args.get("index")
            if not index:
                raise ValueError("index parameter is required")
            size = args.get("size", 5)
            r = requests.get(f"{ES_URL}/{index}/_search", json={"size": size})
            if r.status_code == 404:
                available_indices = requests.get(f"{ES_URL}/_cat/indices?format=json&h=index").json()
                index_names = [idx["index"] for idx in available_indices]
                raise ValueError(f"Index '{index}' not found (404). Available indices: {', '.join(index_names)}")
            r.raise_for_status()
            return r.json()["hits"]["hits"]
        elif tool_name == "search":
            index = args.get("index")
            query_body = args.get("query_body")
            if not index:
                raise ValueError("index parameter is required")
            if not query_body:
                raise ValueError("query_body parameter is required")
            
            # Validate query_body is a dict
            if not isinstance(query_body, dict):
                raise ValueError(f"query_body must be a JSON object/dict, got {type(query_body)}")
            
            r = requests.post(f"{ES_URL}/{index}/_search", json=query_body)
            if r.status_code == 404:
                available_indices = requests.get(f"{ES_URL}/_cat/indices?format=json&h=index").json()
                index_names = [idx["index"] for idx in available_indices]
                raise ValueError(f"Index '{index}' not found (404). Available indices: {', '.join(index_names)}")
            elif r.status_code == 400:
                error_detail = r.text
                try:
                    error_json = r.json()
                    root_cause = error_json.get("error", {})
                    if isinstance(root_cause, dict):
                        error_detail = root_cause.get("root_cause", [{}])[0].get("reason", root_cause.get("reason", error_detail))
                    else:
                        error_detail = str(root_cause)
                except:
                    pass
                
                # Get available fields from mapping to help debug
                try:
                    mapping_r = requests.get(f"{ES_URL}/{index}/_mapping")
                    if mapping_r.status_code == 200:
                        mapping_data = mapping_r.json()
                        index_mapping = mapping_data.get(list(mapping_data.keys())[0], {}).get("mappings", {}).get("properties", {})
                        available_fields = list(index_mapping.keys())
                        error_detail += f" Available fields in '{index}': {', '.join(available_fields)}"
                except:
                    pass
                
                raise ValueError(f"Bad Request (400) for index '{index}': {error_detail}. Use ONLY fields that exist in the index mapping.")
            r.raise_for_status()
            return r.json()
        else:
            raise ValueError(f"Tool not found: {tool_name}")

async def main():
    server = MCPServer()
    loop = asyncio.get_event_loop()
    while True:
        try:
            line = await loop.run_in_executor(None, sys.stdin.readline)
            if not line:
                break
            if not line.strip():
                continue
            try:
                message = json.loads(line.strip())
                response = await server.handle_message(message)
                print(json.dumps(response), flush=True)
                sys.stdout.flush()
            except json.JSONDecodeError as e:
                # Send error response for invalid JSON
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": f"Parse error: {str(e)}"}
                }
                print(json.dumps(error_response), flush=True)
                sys.stdout.flush()
        except Exception as e:
            # Log error but continue
            error_response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32603, "message": f"Internal error: {str(e)}"}
            }
            print(json.dumps(error_response), flush=True)
            sys.stdout.flush()

if __name__ == "__main__":
    asyncio.run(main())