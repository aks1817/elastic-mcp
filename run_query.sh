#!/bin/bash

# Script to run the Elasticsearch queries
# Based on the schema: vehicles -> registrations -> people

echo "Step 1: Find vehicles with price >= 40000"
echo "=========================================="
curl -X POST "http://localhost:9200/vehicles/_search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "range": {
        "price": {
          "gte": 40000
        }
      }
    }
  }' | python3 -m json.tool | head -30

echo ""
echo ""
echo "Step 2: Get vehicle_ids from step 1, then find registrations"
echo "============================================================="
echo "Note: Replace [1, 4] with actual vehicle_ids from step 1"
curl -X POST "http://localhost:9200/registrations/_search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "terms": {
        "vehicle_id": [1, 4]
      }
    }
  }' | python3 -m json.tool | head -30

echo ""
echo ""
echo "Step 3: Get person_ids from step 2, then find people"
echo "====================================================="
echo "Note: Replace [1, 2, 4] with actual person_ids from step 2"
curl -X POST "http://localhost:9200/people/_search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "terms": {
        "id": [1, 2, 4]
      }
    }
  }' | python3 -m json.tool | head -30

