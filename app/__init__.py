from flask import Flask, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
import cloudinary
from urllib.parse import quote


app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://admin:%s@database.c4tmq86mca9u.us-east-1.rds.amazonaws.com/db1?charset=utf8mb4" % quote("123456789a")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = True
app.config["PAGE_SIZE"] = 9
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['SECRET_KEY'] = 'HJGGHD*^&R$YGFGHDYTRER&*TRTYCHG^R&^T'

# Cookie/session settings to preserve login after returning from third-party payment pages
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = False
app.config['REMEMBER_COOKIE_SAMESITE'] = 'Lax'
app.config['REMEMBER_COOKIE_SECURE'] = False

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

# Cấu hình Flask-Login: chuyển hướng đến trang đăng nhập nếu chưa đăng nhập
login.login_view = 'login_user_route'
login.login_message = 'Vui lòng đăng nhập để tiếp tục.'
login.login_message_category = 'warning'

@login.unauthorized_handler
def handle_unauthorized():
    flash('Vui lòng đăng nhập để tiếp tục.', 'warning')
    # Nếu người dùng đi vào các route yêu cầu login liên quan đến thanh toán/checkout,
    # chuyển hướng đăng nhập với next trỏ về trang chi tiết khóa học tương ứng.
    path = request.path or ''
    next_url = request.url
    try:
        course_id = None
        if path.startswith('/checkout/'):
            parts = path.strip('/').split('/')
            if len(parts) >= 2:
                course_id = int(parts[1])
        elif path.startswith('/vnpay-form/'):
            parts = path.strip('/').split('/')
            if len(parts) >= 2:
                course_id = int(parts[1])
        elif path.startswith('/payment/vnpay/create/'):
            parts = path.strip('/').split('/')
            if len(parts) >= 4:
                course_id = int(parts[3])
        elif path.startswith('/payment/momo/create/'):
            parts = path.strip('/').split('/')
            if len(parts) >= 4:
                course_id = int(parts[3])

        if course_id:
            next_url = url_for('course_detail', course_id=course_id, _external=False)
        elif request.referrer:
            next_url = request.referrer
    except Exception:
        if request.referrer:
            next_url = request.referrer
    return redirect(url_for('login_user_route', next=next_url))

# Import và khởi tạo Flask-Admin
from app.admin import admin

# Config VNPAY
app.config["VNPAY_TMN_CODE"] = "WH45MXV7"
app.config["VNPAY_PAYMENT_URL"] = "https://sandbox.vnpayment.vn/paymentv2/vpcpay.html"
app.config["VNPAY_HASH_SECRET_KEY"]= "P34HA4469TCJFT321PS8DLNQMC1XFDQ2"
app.config["VNPAY_RETURN_URL"] = "http://localhost:5000/payment_return"

# Config MoMo Sandbox
app.config["MOMO_PARTNER_CODE"] = "MOMO"
app.config["MOMO_ACCESS_KEY"] = "F8BBA842ECF85"
app.config["MOMO_SECRET_KEY"] = "K951B6PE1waDMi640xX08PD3vg6EkVlz"
app.config["MOMO_ENDPOINT"] = "https://test-payment.momo.vn"
app.config["MOMO_RETURN_URL"] = "http://localhost:5000/momo_return"
app.config["MOMO_IPN_URL"] = "http://localhost:5000/momo_ipn"