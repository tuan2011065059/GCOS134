# Nơi chạy chính chương trình
from flask import Flask
from Controllers.home_controller import home_blueprint
import os

app = Flask(__name__, template_folder='View', static_folder='Static')
app.register_blueprint(home_blueprint)
app.secret_key = os.environ.get("SECRET_KEY", "ntnqplnvtc")

if __name__ == '__main__':
    app.run(debug=True)




from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("agent_movement.html")

@app.route("/agent-info")
def agent_info():
    return render_template("tree.html")  

@app.route("/agent-movement")
def agent_movement():
    return render_template("agent_movement.html")

@app.route("/commission")
def commission():
    return render_template("commission.html")

@app.route("/monthly-bonus")
def monthly_bonus():
    return render_template("monthly.html")
