from flask import Flask
from threading import Thread
import os

app = Flask('')

@app.route('/')
def home():
    return "Silk is Online!"

def run_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def run():
    t = Thread(target=run_server)
    t.start()
