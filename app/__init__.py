from flask import Flask, render_template
import json


app = Flask(__name__)

app.config["UPLOAD_FOLDER"] = "static"


@app.route("/")
def index():
    with open("data/latest.json", "r") as f:
        data = json.load(f)
    return render_template("better_style.html", data=data)
