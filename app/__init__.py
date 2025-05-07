from flask import Flask, render_template
import json


app = Flask(__name__)

app.config["UPLOAD_FOLDER"] = "static"


@app.route("/")
def index():
    with open("data/stats.json", "r") as f:
        data = json.load(f)
    return render_template("2025.html", data=data)
