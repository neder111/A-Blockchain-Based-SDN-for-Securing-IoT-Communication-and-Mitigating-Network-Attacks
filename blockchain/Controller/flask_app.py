from flask import Flask, render_template
import json
import os

app = Flask(__name__)
BLOCKCHAIN_FILE = "/tmp/blockchain.json"

@app.route('/')
def index():
    if os.path.exists(BLOCKCHAIN_FILE):
        with open(BLOCKCHAIN_FILE, "r") as f:
            chain = json.load(f)
    else:
        chain = []
    return render_template('index.html', chain=chain)

if __name__ == '__main__':
    app.run(debug=True, port=5000)

