from flask import Flask, render_template
import json
import os

app = Flask(__name__)
LATEST_PACKETS_FILE = "/tmp/latest_packets.json"

@app.route('/')
def index():
    if os.path.exists(LATEST_PACKETS_FILE):
        with open(LATEST_PACKETS_FILE, "r") as f:
            try:
                packets = json.load(f)
            except json.JSONDecodeError:
                packets = []
    else:
        packets = []

    return render_template('main.html', packets=packets)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

