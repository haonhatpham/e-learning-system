from flask import Flask
from flask_sqlalchemy import SQLAlchemy
# from flask_login import LoginManager  # Tạm thời comment lại
import cloudinary
from urllib.parse import quote


app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://root:%s@localhost/ecoursedb?charset=utf8mb4" % quote("1234")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = True
app.config["PAGE_SIZE"] = 9
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['SECRET_KEY'] = 'HJGGHD*^&R$YGFGHDYTRER&*TRTYCHG^R&^T'


db = SQLAlchemy(app) #Tạo dữ liệu và đối tượng truy vấn
# login = LoginManager(app=app)

cloudinary.config(cloud_name='dtcxjo4ns',
                  api_key="172464483393764",
                  api_secret="1yivw8eviVI7BBQ7q9S909OS2mU",
                  secure=True
                  )