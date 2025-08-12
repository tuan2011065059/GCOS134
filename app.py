# Nơi chạy chính chương trình
from flask import Flask
from Controllers.home_controller import home_blueprint

app = Flask(__name__, template_folder='View', static_folder='Static')
app.register_blueprint(home_blueprint)

if __name__ == '__main__':
    app.run(debug=True)
