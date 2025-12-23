from flask import Flask, request, jsonify
import requests

app = Flask(__name__)
ES_URL = "http://localhost:9200"

@app.route("/list_indices", methods=["GET"])
def list_indices():
    r = requests.get(f"{ES_URL}/_cat/indices?format=json")
    indices = [i["index"] for i in r.json()]
    return jsonify(indices)

@app.route("/get_mapping/<index>", methods=["GET"])
def get_mapping(index):
    r = requests.get(f"{ES_URL}/{index}/_mapping")
    return jsonify(r.json())

@app.route("/sample_docs/<index>", methods=["GET"])
def sample_docs(index):
    size = int(request.args.get("size", 5))
    r = requests.get(f"{ES_URL}/{index}/_search", json={"size": size})
    return jsonify(r.json()["hits"]["hits"])

@app.route("/search/<index>", methods=["POST"])
def search(index):
    query = request.json
    r = requests.post(f"{ES_URL}/{index}/_search", json=query)
    return jsonify(r.json())

if __name__ == "__main__":
    app.run(port=5000)
