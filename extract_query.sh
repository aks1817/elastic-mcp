#!/bin/bash

# Helper script to extract JSON queries from mcphost output
# Usage: ./extract_query.sh or pipe mcphost output to it

# Extract JSON objects that look like queries
# Looks for patterns like {"query": ...} or {"index": ..., "query": ...}

grep -oE '\{[^}]*"query"[^}]*\}' | \
grep -oE '\{[^{}]*"query"[^{}]*\{[^}]*\}[^}]*\}' | \
python3 -c "
import sys
import json
import re

# Read all input
text = sys.stdin.read()

# Try to find JSON objects with 'query' key
# Look for complete JSON objects
pattern = r'\{[^{}]*"query"[^{}]*\{[^}]*\}[^}]*\}'
matches = re.findall(pattern, text)

# Also try to find multi-line JSON
lines = text.split('\n')
json_objects = []
current_obj = ''
brace_count = 0

for line in lines:
    for char in line:
        if char == '{':
            if brace_count == 0:
                current_obj = '{'
            else:
                current_obj += char
            brace_count += 1
        elif char == '}':
            current_obj += char
            brace_count -= 1
            if brace_count == 0:
                if 'query' in current_obj.lower():
                    json_objects.append(current_obj)
                current_obj = ''
        else:
            if brace_count > 0:
                current_obj += char

# Try to parse and pretty print
all_queries = matches + json_objects
for query_str in all_queries:
    try:
        # Clean up the string
        query_str = query_str.strip()
        if not query_str:
            continue
        # Try to parse
        query = json.loads(query_str)
        if 'query' in query:
            print(json.dumps(query, indent=2))
            print('---')
    except:
        pass

# If no queries found, print message
if not all_queries:
    print('No query JSON found in output.')
    print('Make sure the model outputs the query after completing tool calls.')
"

