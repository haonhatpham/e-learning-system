from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
import cloudinary
from urllib.parse import quote


app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://root:%s@localhost/ecoursedb?charset=utf8mb4" % quote("1234")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = True
app.config["PAGE_SIZE"] = 9
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['SECRET_KEY'] = 'HJGGHD*^&R$YGFGHDYTRER&*TRTYCHG^R&^T'

# Cấu hình email
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = 'thongbaocuahang@gmail.com'  # Thay bằng email Gmail của bạn
app.config['MAIL_PASSWORD'] = 'awoq uxis jtdb dyca'     # Thay bằng App Password từ Google
app.config['MAIL_DEFAULT_SENDER'] = 'thongbaocuahang@gmail.com'


db = SQLAlchemy(app) 
login = LoginManager(app=app)
mail = Mail(app)

cloudinary.config(cloud_name='dtcxjo4ns',
                  api_key="172464483393764",
                  api_secret="1yivw8eviVI7BBQ7q9S909OS2mU",
                  secure=True
                  )

# Import và khởi tạo Flask-Admin
from app.admin import admin