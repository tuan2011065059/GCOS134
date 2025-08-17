# Nơi chạy chính chương trình
from flask import Flask
from Controllers.home_controller import home_blueprint
import os

app = Flask(__name__, template_folder='View', static_folder='Static')
app.register_blueprint(home_blueprint)
app.secret_key = os.environ.get("SECRET_KEY", "ntnqplnvtc")

if __name__ == '__main__':
    app.run(debug=True)
