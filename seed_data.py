import requests

ES_URL = "http://localhost:9200"

# Create indices with more complex data and relations
indices = {
    "vehicles": [
        {"id": 1, "make": "Tesla", "model": "Model 3", "year": 2022, "type": "electric car", "price": 45000},
        {"id": 2, "make": "Toyota", "model": "Corolla", "year": 2020, "type": "sedan", "price": 20000},
        {"id": 3, "make": "Ford", "model": "Mustang", "year": 2018, "type": "sports car", "price": 35000},
        {"id": 4, "make": "BMW", "model": "X5", "year": 2021, "type": "SUV", "price": 60000},
        {"id": 5, "make": "Honda", "model": "Civic", "year": 2019, "type": "sedan", "price": 22000}
    ],
    "people": [
        {"id": 1, "name": "Alice Johnson", "age": 30, "city": "New York"},
        {"id": 2, "name": "Bob Smith", "age": 45, "city": "Los Angeles"},
        {"id": 3, "name": "Charlie Brown", "age": 28, "city": "Chicago"},
        {"id": 4, "name": "Diana Prince", "age": 35, "city": "Houston"},
        {"id": 5, "name": "Eve Adams", "age": 40, "city": "Phoenix"}
    ],
    "registrations": [
        {"vehicle_id": 1, "person_id": 1, "reg_date": "2022-05-10", "status": "active"},
        {"vehicle_id": 2, "person_id": 2, "reg_date": "2020-03-15", "status": "active"},
        {"vehicle_id": 3, "person_id": 3, "reg_date": "2018-07-20", "status": "expired"},
        {"vehicle_id": 4, "person_id": 4, "reg_date": "2021-11-05", "status": "active"},
        {"vehicle_id": 5, "person_id": 5, "reg_date": "2019-09-12", "status": "active"},
        {"vehicle_id": 1, "person_id": 2, "reg_date": "2023-01-08", "status": "active"}  # Alice sold to Bob
    ]
}

for index, docs in indices.items():
    # Create index
    requests.put(f"{ES_URL}/{index}", json={"settings": {"number_of_shards": 1}})
    # Insert documents
    for i, doc in enumerate(docs, start=1):
        requests.post(f"{ES_URL}/{index}/_doc/{i}", json=doc)

print("Complex sample data with relations seeded successfully.")
