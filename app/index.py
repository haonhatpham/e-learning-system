from flask import render_template, request, redirect, url_for, flash, jsonify
from app import app, dao, db
from app import login
from app.dao import load_categories, load_featured_courses, search_courses
from flask_login import login_user, logout_user, current_user, login_required
from app.utils import send_welcome_email, send_registration_confirmation
from app.models import UserRole, UserStatus, Course, CourseStatus, CourseLevel, Lesson, LessonType, Enrollment, Payment, PaymentMethod, PaymentStatus
from app import admin
from datetime import datetime
from decimal import Decimal
import time
import urllib.parse
import hmac
import hashlib
import json
import requests


@app.route("/")
def index():
    categories = load_categories()
    featured_courses = load_featured_courses(limit=6)
        

    return render_template('index.html',categories=categories,featured_courses=featured_courses)
# Trang tìm kiếm khóa học
@app.route("/search")
def search():
    keyword = request.args.get("q", "")
    category_id = request.args.get("category_id", type=int)
    price_min = request.args.get("price_min", type=float)
    price_max = request.args.get("price_max", type=float)

    courses = dao.search_courses(keyword, category_id, price_min, price_max)
    categories = dao.load_categories()

    return render_template(
        "search.html",
        q=keyword,
        courses=courses,
        categories=categories,
        selected_category=category_id,
        price_min=price_min,
        price_max=price_max
    )


# Trang chi tiết khóa học
@app.route("/course/<int:course_id>")
def course_detail(course_id):
    course = Course.query.get_or_404(course_id)
    prev_url = request.referrer or url_for("search")
    user_enrolled = False
    user_is_owner = False
    user_is_admin = False
    if current_user.is_authenticated:
        user_enrolled = Enrollment.query.filter_by(user_id=current_user.id, course_id=course_id).first() is not None
        user_is_owner = (course.instructor_id == current_user.id)
        user_is_admin = (current_user.role == UserRole.ADMIN)
    return render_template("course_detail.html", course=course, prev_url=prev_url,
                           user_enrolled=user_enrolled, user_is_owner=user_is_owner, user_is_admin=user_is_admin)


def can_view_lesson(lesson: Lesson, course: Course) -> bool:
    if lesson.is_preview:
        return True
    if current_user.is_authenticated:
        if current_user.role == UserRole.ADMIN:
            return True
        if course.instructor_id == current_user.id:
            return True
        if Enrollment.query.filter_by(user_id=current_user.id, course_id=course.id).first():
            return True
    return False


@app.route('/course/<int:course_id>/lesson/<int:lesson_id>')
def view_lesson(course_id, lesson_id):
    course = Course.query.get_or_404(course_id)
    lesson = Lesson.query.filter_by(id=lesson_id, course_id=course.id).first_or_404()
    if not can_view_lesson(lesson, course):
        flash('Bạn cần đăng ký khóa học để xem bài học này (trừ preview).', 'warning')
        return redirect(url_for('course_detail', course_id=course.id))
    embed_url = None
    if lesson.type == LessonType.VIDEO:
        embed_url = dao.to_embeddable_video_url(lesson.content_url)
    return render_template('lesson_view.html', course=course, lesson=lesson, embed_url=embed_url)




    return render_template('index.html', categories=categories, featured_courses=featured_courses)

@app.route("/login-admin", methods=['post'])
def login_admin_process():
    username = request.form.get('username')
    password = request.form.get('password')

    u = dao.auth_user(username=username, password=password, role=UserRole.ADMIN)
    if u:
        login_user(u)
        print("XX")
    return redirect('/admin')

@app.route('/login', methods=['GET', 'POST'])
def login_user_route():
    if request.method.__eq__('POST'):
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember') == 'on'

        # Kiểm tra đăng nhập bằng username
        user = dao.auth_user_by_username(username=username, password=password)
        if user:
            login_user(user, remember=remember)
            flash('Đăng nhập thành công!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page if next_page else '/')
        else:
            user_check = dao.get_user_by_username(username)
            if user_check:
                if user_check.status == UserStatus.PENDING_APPROVAL:
                    flash('Tài khoản giảng viên đang chờ admin duyệt! Vui lòng liên hệ admin để được kích hoạt.', 'warning')
                elif user_check.status == UserStatus.REJECTED:
                    flash('Tài khoản giảng viên đã bị từ chối! Vui lòng liên hệ admin để biết thêm chi tiết.', 'error')
                elif user_check.status == UserStatus.INACTIVE:
                    flash('Tài khoản đã bị khóa! Vui lòng liên hệ admin để được hỗ trợ.', 'error')
                else:
                    flash('Mật khẩu không chính xác!', 'error')
            else:
                flash('Tên đăng nhập không tồn tại!', 'error')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        role = request.form.get('role')
        phone = request.form.get('phone')
        avatar_file = request.files.get('avatar') if 'avatar' in request.files else None

        # Gọi dao.py để xử lý logic
        new_user, message = dao.create_user_with_validation(
            full_name=full_name,
            username=username,
            email=email,
            password=password,
            confirm_password=confirm_password,
            role=role,
            phone=phone,
            avatar_file=avatar_file
        )

        if new_user:
            send_welcome_email(new_user)
            send_registration_confirmation(new_user)

            if role == 'instructor':
                flash('Đăng ký giảng viên thành công! Tài khoản đang chờ admin duyệt. Bạn sẽ nhận được email thông báo khi được kích hoạt.', 'warning')
            else:
                flash('Đăng ký thành công! Email chào mừng đã được gửi đến hộp thư của bạn.', 'success')

            return redirect(url_for('login_user_route'))
        else:
            flash(message, 'error')
    return render_template('register.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html')

@app.route('/my-courses')
@login_required
def my_courses():
    return render_template('my_courses.html')


@app.route('/checkout/<int:course_id>')
@login_required
def checkout(course_id):
    course = Course.query.get_or_404(course_id)
    
    # Kiểm tra đã ghi danh chưa
    existing_enrollment = Enrollment.query.filter_by(user_id=current_user.id, course_id=course_id).first()
    if existing_enrollment:
        flash('Bạn đã đăng ký khóa học này rồi.', 'warning')
        return redirect(url_for('course_detail', course_id=course_id))
    
    return render_template('checkout.html', course=course)


@app.route('/checkout/<int:course_id>', methods=['POST'])
@login_required
def process_checkout(course_id):
    course = Course.query.get_or_404(course_id)
    payment_method = request.form.get('payment_method')
    
    if payment_method == 'vnpay':
        return redirect(url_for('vnpay_form', course_id=course_id))
    elif payment_method == 'momo':
        return redirect(url_for('create_momo_payment', course_id=course_id))
    else:
        flash('Vui lòng chọn phương thức thanh toán.', 'error')
        return redirect(url_for('checkout', course_id=course_id))


@app.route('/vnpay-form/<int:course_id>')
@login_required
def vnpay_form(course_id):
    course = Course.query.get_or_404(course_id)
    return render_template('vnpay_form.html', course=course)


def create_vnpay_url(course_id, user_id, amount, bank_code='', language='vn'):
    params = {
        'vnp_Version': '2.1.0',
        'vnp_Command': 'pay',
        'vnp_TmnCode': app.config.get('VNPAY_TMN_CODE'),
        'vnp_Amount': int(amount * 100),  # VNPAY yêu cầu nhân 100
        'vnp_CurrCode': 'VND',
        'vnp_TxnRef': f"{course_id}-{user_id}-{int(time.time())}",
        'vnp_OrderInfo': f'Thanh toan khoa hoc {course_id}',
        'vnp_OrderType': 'other',
        'vnp_Locale': language,
        # Dùng URL động theo host hiện tại để không mất session khi quay về
        'vnp_ReturnUrl': url_for('payment_return', _external=True),
        'vnp_IpAddr': request.remote_addr or '127.0.0.1',
        'vnp_CreateDate': datetime.now().strftime('%Y%m%d%H%M%S')
    }
    

    if bank_code and bank_code.strip():
        params['vnp_BankCode'] = bank_code.strip()
    

    filtered_params = {k: v for k, v in params.items() if v is not None and str(v).strip() != ''}

    sorted_params = sorted(filtered_params.items())
    

    sign_parts = []
    for k, v in sorted_params:
        encoded_v = urllib.parse.quote_plus(str(v))
        sign_parts.append(f"{k}={encoded_v}")
    sign_string = '&'.join(sign_parts)
    
    # Tạo chữ ký HMAC-SHA512
    secret_key = app.config.get('VNPAY_HASH_SECRET_KEY')
    signature = hmac.new(
        secret_key.encode('utf-8'),
        sign_string.encode('utf-8'),
        hashlib.sha512
    ).hexdigest()
    

    query_parts = []
    for k, v in sorted_params:
        encoded_v = urllib.parse.quote_plus(str(v))
        query_parts.append(f"{k}={encoded_v}")
    
    query_string = '&'.join(query_parts)
    payment_url = f"{app.config.get('VNPAY_PAYMENT_URL')}?{query_string}&vnp_SecureHash={signature}"
    
    return payment_url


@app.route('/payment/vnpay/create/<int:course_id>', methods=['POST'])
@login_required
def create_vnpay_payment(course_id):
    """Tạo thanh toán VNPAY"""
    course = Course.query.get_or_404(course_id)

    # Kiểm tra đã ghi danh chưa
    existing_enrollment = Enrollment.query.filter_by(user_id=current_user.id, course_id=course_id).first()
    if existing_enrollment:
        flash('Bạn đã đăng ký khóa học này rồi.', 'warning')
        return redirect(url_for('course_detail', course_id=course_id))

    # khóa học miễn phí
    try:
        price = Decimal(str(course.price))
    except Exception:
        price = Decimal('0')

    if price == 0:
        #ghi trực tiếp
        enrollment = Enrollment(user_id=current_user.id, course_id=course_id)
        db.session.add(enrollment)
        db.session.commit()
        flash('Đăng ký khóa học miễn phí thành công!', 'success')
        return redirect(url_for('my_courses'))

    # Lấy thông tin từ form
    bank_code = request.form.get('bank_code', '').strip()
    language = request.form.get('language', 'vn')

    # Tạo URL thanh toán VNPAY
    payment_url = create_vnpay_url(
        course_id=course_id,
        user_id=current_user.id,
        amount=price,
        bank_code=bank_code,
        language=language
    )

    return redirect(payment_url)

# Momo
def momo_sign(raw_signature: str, secret_key: str) -> str:
    return hmac.new(secret_key.encode('utf-8'), raw_signature.encode('utf-8'), hashlib.sha256).hexdigest()


@app.route('/payment/momo/create/<int:course_id>', methods=['GET', 'POST'])
@login_required
def create_momo_payment(course_id):
    course = Course.query.get_or_404(course_id)

    # Chặn ghi danh trùng
    if Enrollment.query.filter_by(user_id=current_user.id, course_id=course_id).first():
        flash('Bạn đã đăng ký khóa học này rồi.', 'warning')
        return redirect(url_for('course_detail', course_id=course_id))

    try:
        amount = int(Decimal(str(course.price)))
    except Exception:
        amount = 0

    if amount == 0:
        enrollment = Enrollment(user_id=current_user.id, course_id=course_id)
        db.session.add(enrollment)
        db.session.commit()
        flash('Đăng ký khóa học miễn phí thành công!', 'success')
        return redirect(url_for('my_courses'))

    partner_code = app.config.get('MOMO_PARTNER_CODE')
    access_key = app.config.get('MOMO_ACCESS_KEY')
    secret_key = app.config.get('MOMO_SECRET_KEY')
    endpoint = app.config.get('MOMO_ENDPOINT')
    # Dùng URL động theo host hiện tại để tránh lệch domain làm mất cookie đăng nhập
    return_url = url_for('momo_return', _external=True)
    ipn_url = url_for('momo_ipn', _external=True)

    order_id = f"{course_id}-{current_user.id}-{int(time.time())}"
    request_id = f"REQ-{int(time.time()*1000)}"
    order_info = f"Thanh toan khoa hoc {course_id}"
    request_type = 'captureWallet'
    extra_data = ''

    raw_signature = (
        f"accessKey={access_key}&amount={amount}&extraData={extra_data}"
        f"&ipnUrl={ipn_url}&orderId={order_id}&orderInfo={order_info}"
        f"&partnerCode={partner_code}&redirectUrl={return_url}"
        f"&requestId={request_id}&requestType={request_type}"
    )
    signature = momo_sign(raw_signature, secret_key)

    payload = {
        "partnerCode": partner_code,
        "partnerName": "MoMo",
        "storeId": "MoMoTestStore",
        "requestId": request_id,
        "amount": amount,
        "orderId": order_id,
        "orderInfo": order_info,
        "redirectUrl": return_url,
        "ipnUrl": ipn_url,
        "lang": "vi",
        "requestType": request_type,
        "extraData": extra_data,
        "signature": signature
    }

    try:
        resp = requests.post(f"{endpoint}/v2/gateway/api/create", json=payload, timeout=20)
        data = resp.json()
        if data.get('resultCode') == 0 and data.get('payUrl'):
            return redirect(data['payUrl'])
        else:
            flash(f"MoMo error: {data}", 'error')
            return redirect(url_for('checkout', course_id=course_id))
    except Exception as e:
        flash(f"MoMo request error: {e}", 'error')
        return redirect(url_for('checkout', course_id=course_id))


@app.route('/momo_return')
def momo_return():
    params = {k: v for k, v in request.args.items()}
    partner_code = app.config.get('MOMO_PARTNER_CODE')
    access_key = app.config.get('MOMO_ACCESS_KEY')
    secret_key = app.config.get('MOMO_SECRET_KEY')

    # Raw signature theo tài liệu MoMo (return route)
    raw_signature = (
        f"accessKey={access_key}&amount={params.get('amount','')}"
        f"&extraData={params.get('extraData','')}"
        f"&message={params.get('message','')}"
        f"&orderId={params.get('orderId','')}"
        f"&orderInfo={params.get('orderInfo','')}"
        f"&orderType={params.get('orderType','')}"
        f"&partnerCode={params.get('partnerCode','')}"
        f"&payType={params.get('payType','')}"
        f"&requestId={params.get('requestId','')}"
        f"&responseTime={params.get('responseTime','')}"
        f"&resultCode={params.get('resultCode','')}"
        f"&transId={params.get('transId','')}"
    )
    signature = momo_sign(raw_signature, secret_key)

    is_valid = signature == params.get('signature')

    course_id = user_id = None
    try:
        parts = (params.get('orderId') or '').split('-')
        if len(parts) >= 2:
            course_id = int(parts[0])
            user_id = int(parts[1])
    except Exception:
        pass

    if is_valid and params.get('resultCode') == '0' and course_id and user_id:
        amount_vnd = Decimal(int(params.get('amount','0')))
        enrollment = Enrollment.query.filter_by(user_id=user_id, course_id=course_id).first()
        if not enrollment:
            enrollment = Enrollment(user_id=user_id, course_id=course_id)
            db.session.add(enrollment)
            db.session.flush()

        payment = Payment(
            enrollment_id=enrollment.id,
            amount=amount_vnd,
            payment_method=PaymentMethod.MOMO,
            transaction_id=str(params.get('transId') or params.get('orderId')),
            status=PaymentStatus.COMPLETED
        )
        db.session.add(payment)
        db.session.commit()

        course = Course.query.get(course_id)
        payment_info = {
            'transaction_id': str(params.get('transId') or params.get('orderId')),
            'course_title': course.title if course else 'Không xác định',
            'amount': amount_vnd,
            'payment_method': 'MOMO',
            'payment_date': datetime.now()
        }
        return render_template('payment_return.html', success=True, payment_info=payment_info)
    else:
        flash('Thanh toán MoMo thất bại hoặc chữ ký sai.', 'error')
        return redirect(url_for('checkout', course_id=course_id or 0))


@app.route('/momo_ipn', methods=['POST'])
def momo_ipn():
    params = request.get_json(force=True, silent=True) or {}
    access_key = app.config.get('MOMO_ACCESS_KEY')
    secret_key = app.config.get('MOMO_SECRET_KEY')

    raw_signature = (
        f"accessKey={access_key}&amount={params.get('amount','')}"
        f"&extraData={params.get('extraData','')}"
        f"&message={params.get('message','')}"
        f"&orderId={params.get('orderId','')}"
        f"&orderInfo={params.get('orderInfo','')}"
        f"&orderType={params.get('orderType','')}"
        f"&partnerCode={params.get('partnerCode','')}"
        f"&payType={params.get('payType','')}"
        f"&requestId={params.get('requestId','')}"
        f"&responseTime={params.get('responseTime','')}"
        f"&resultCode={params.get('resultCode','')}"
        f"&transId={params.get('transId','')}"
    )
    signature = momo_sign(raw_signature, secret_key)
    is_valid = signature == params.get('signature')

    if is_valid and str(params.get('resultCode')) == '0':
        # Có thể thực hiện cập nhật trạng thái giao dịch tại đây (idempotency)
        return jsonify({'resultCode': 0, 'message': 'OK'})
    else:
        return jsonify({'resultCode': 1, 'message': 'Invalid signature'}), 400


@app.route('/payment_return')
def payment_return():
    response_data = {k: v for k, v in request.args.items()}
    

    response_code = request.args.get('vnp_ResponseCode')
    txn_ref = request.args.get('vnp_TxnRef')
    amount_str = request.args.get('vnp_Amount', '0')
    transaction_no = request.args.get('vnp_TransactionNo')

    # Parse course_id và user_id từ txn_ref
    course_id = None
    user_id = None
    parts = (txn_ref or '').split('-')
    if len(parts) >= 2:
        course_id = int(parts[0])
        user_id = int(parts[1])

    if response_code == '00' and course_id and user_id:
        # Thanh toán thành công
        try:
            amount_vnd = Decimal(int(amount_str) / 100)
        except Exception:
            amount_vnd = Decimal('0')

        # Tạo enrollment nếu chưa có
        enrollment = Enrollment.query.filter_by(user_id=user_id, course_id=course_id).first()
        if not enrollment:
            enrollment = Enrollment(user_id=user_id, course_id=course_id)
            db.session.add(enrollment)
            db.session.flush()

        # Tạo payment record
        payment = Payment(
            enrollment_id=enrollment.id,
            amount=amount_vnd,
            payment_method=PaymentMethod.VNPAY,
            transaction_id=str(transaction_no or txn_ref),
            status=PaymentStatus.COMPLETED
        )
        db.session.add(payment)
        db.session.commit()

        # Lấy thông tin để hiển thị
        course = Course.query.get(course_id)
        payment_info = {
            'transaction_id': str(transaction_no or txn_ref),
            'course_title': course.title if course else 'Không xác định',
            'amount': amount_vnd,
            'payment_method': 'VNPAY',
            'payment_date': datetime.now()
        }

        return render_template('payment_return.html', success=True, payment_info=payment_info)
    else:
        # Thanh toán thất bại
        error_message = 'Thanh toán thất bại hoặc bị hủy.'
        return render_template('payment_return.html', success=False, error_message=error_message)


@login.user_loader
def load_user(user_id):
    return dao.get_user_by_id(user_id)


# danh cho admin
@app.route('/api/admin/approve-instructor', methods=['POST'])
@login_required
def api_approve_instructor():
    """API duyệt giảng viên"""
    # Kiểm tra quyền admin
    if current_user.role != UserRole.ADMIN:
        return jsonify({
            'success': False,
            'message': 'Không có quyền thực hiện hành động này'
        }), 403

    try:
        data = request.get_json()
        user_id = data.get('user_id')

        if not user_id:
            return jsonify({
                'success': False,
                'message': 'Thiếu user_id'
            }), 400

        # Gọi dao để duyệt giảng viên
        success, message = dao.approve_instructor(user_id)

        if success:
            return jsonify({
                'success': True,
                'message': f'Đã duyệt giảng viên: {message}',
                'user_id': user_id
            })
        else:
            return jsonify({
                'success': False,
                'message': f'Lỗi khi duyệt: {message}'
            }), 400

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Lỗi hệ thống: {str(e)}'
        }), 500


@app.route('/api/admin/reject-instructor', methods=['POST'])
@login_required
def api_reject_instructor():
    """API từ chối giảng viên"""
    # Kiểm tra quyền admin
    if current_user.role != UserRole.ADMIN:
        return jsonify({
            'success': False,
            'message': 'Không có quyền thực hiện hành động này'
        }), 403

    try:
        data = request.get_json()
        user_id = data.get('user_id')

        if not user_id:
            return jsonify({
                'success': False,
                'message': 'Thiếu user_id'
            }), 400

        # Gọi dao để từ chối giảng viên
        success, message = dao.reject_instructor(user_id)

        if success:
            return jsonify({
                'success': True,
                'message': f'Đã từ chối giảng viên: {message}',
                'user_id': user_id
            })
        else:
            return jsonify({
                'success': False,
                'message': f'Lỗi khi từ chối: {message}'
            }), 400

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Lỗi hệ thống: {str(e)}'
        }), 500


def require_instructor_active():
    if not current_user.is_authenticated:
        return redirect(url_for('login_user_route'))
    if current_user.role != UserRole.INSTRUCTOR or current_user.status != UserStatus.ACTIVE:
        flash('Chỉ giảng viên đã được duyệt mới có thể truy cập.', 'error')
        return redirect(url_for('index'))
    return None


@app.route('/instructor/courses')
@login_required
def instructor_courses():
    guard = require_instructor_active()
    if guard:
        return guard
    courses = Course.query.filter_by(instructor_id=current_user.id).order_by(Course.created_at.desc()).all()
    return render_template('instructor/courses.html', courses=courses, CourseStatus=CourseStatus)


@app.route('/instructor/courses/create', methods=['GET', 'POST'])
@login_required
def instructor_create_course():
    guard = require_instructor_active()
    if guard:
        return guard
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        price = request.form.get('price', type=float) or 0.0
        level = request.form.get('level') or CourseLevel.BEGINNER.value
        status_val = request.form.get('status') or CourseStatus.DRAFT.value
        cover_file = request.files.get('cover_image')

        cover_url = None
        if cover_file and cover_file.filename:
            cover_url = dao.upload_image_to_cloudinary(cover_file, 'e-learning/course_covers', f"course_{current_user.id}")

        course = Course(
            title=title,
            description=description,
            price=price,
            level=CourseLevel(level),
            status=CourseStatus(status_val),
            cover_image=cover_url,
            instructor_id=current_user.id
        )
        db.session.add(course)
        db.session.commit()
        flash('Tạo khóa học thành công!', 'success')
        return redirect(url_for('instructor_courses'))

    return render_template('instructor/course_form.html', course=None, CourseStatus=CourseStatus, CourseLevel=CourseLevel)


@app.route('/instructor/courses/<int:course_id>/edit', methods=['GET', 'POST'])
@login_required
def instructor_edit_course(course_id):
    guard = require_instructor_active()
    if guard:
        return guard
    course = Course.query.filter_by(id=course_id, instructor_id=current_user.id).first_or_404()
    if request.method == 'POST':
        course.title = request.form.get('title')
        course.description = request.form.get('description')
        course.price = request.form.get('price', type=float) or 0.0
        course.level = CourseLevel(request.form.get('level') or CourseLevel.BEGINNER.value)
        course.status = CourseStatus(request.form.get('status') or CourseStatus.DRAFT.value)
        cover_file = request.files.get('cover_image')
        if cover_file and cover_file.filename:
            cover_url = dao.upload_image_to_cloudinary(cover_file, 'e-learning/course_covers', f"course_{course.id}")
            if cover_url:
                course.cover_image = cover_url
        db.session.commit()
        flash('Cập nhật khóa học thành công!', 'success')
        return redirect(url_for('instructor_courses'))
    return render_template('instructor/course_form.html', course=course, CourseStatus=CourseStatus, CourseLevel=CourseLevel)


@app.route('/instructor/courses/<int:course_id>/delete', methods=['POST'])
@login_required
def instructor_delete_course(course_id):
    guard = require_instructor_active()
    if guard:
        return guard
    course = Course.query.filter_by(id=course_id, instructor_id=current_user.id).first_or_404()

    Lesson.query.filter_by(course_id=course.id).delete()
    db.session.delete(course)
    db.session.commit()
    flash('Đã xóa khóa học.', 'success')
    return redirect(url_for('instructor_courses'))


@app.route('/instructor/courses/<int:course_id>/lessons')
@login_required
def instructor_lessons(course_id):
    guard = require_instructor_active()
    if guard:
        return guard
    course = Course.query.filter_by(id=course_id, instructor_id=current_user.id).first_or_404()
    lessons = Lesson.query.filter_by(course_id=course.id).order_by(Lesson.lesson_order.asc()).all()
    return render_template('instructor/lessons.html', course=course, lessons=lessons, LessonType=LessonType)


@app.route('/instructor/courses/<int:course_id>/lessons/create', methods=['GET', 'POST'])
@login_required
def instructor_create_lesson(course_id):
    guard = require_instructor_active()
    if guard:
        return guard
    course = Course.query.filter_by(id=course_id, instructor_id=current_user.id).first_or_404()
    if request.method == 'POST':
        title = request.form.get('title')
        lesson_type = request.form.get('type')
        content_url = request.form.get('content_url')
        content_data_raw = request.form.get('content_data')
        lesson_order = request.form.get('lesson_order', type=int) or 0
        duration_seconds = request.form.get('duration_seconds', type=int) or 0
        is_preview = True if request.form.get('is_preview') == 'on' else False

        try:
            content_data = json.loads(content_data_raw) if content_data_raw else None
        except Exception:
            content_data = None

        # Normalize video URLs to embeddable format (e.g., YouTube)
        if lesson_type and lesson_type.lower() == 'video' and content_url:
            content_url = dao.normalize_video_url(content_url)

        lesson = Lesson(
            title=title,
            type=LessonType(lesson_type),
            content_url=content_url,
            content_data=content_data,
            course_id=course.id,
            lesson_order=lesson_order,
            duration_seconds=duration_seconds,
            is_preview=is_preview
        )
        db.session.add(lesson)
        db.session.commit()
        flash('Tạo bài học thành công!', 'success')
        return redirect(url_for('instructor_lessons', course_id=course.id))

    return render_template('instructor/lesson_form.html', course=course, lesson=None, LessonType=LessonType)


@app.route('/instructor/lessons/<int:lesson_id>/edit', methods=['GET', 'POST'])
@login_required
def instructor_edit_lesson(lesson_id):
    guard = require_instructor_active()
    if guard:
        return guard
    lesson = Lesson.query.get_or_404(lesson_id)
    course = Course.query.filter_by(id=lesson.course_id, instructor_id=current_user.id).first_or_404()
    if request.method == 'POST':
        lesson.title = request.form.get('title')
        lesson.type = LessonType(request.form.get('type'))
        content_url = request.form.get('content_url')
        content_data_raw = request.form.get('content_data')
        try:
            lesson.content_data = json.loads(content_data_raw) if content_data_raw else None
        except Exception:
            lesson.content_data = None
        lesson.lesson_order = request.form.get('lesson_order', type=int) or 0
        lesson.duration_seconds = request.form.get('duration_seconds', type=int) or 0
        lesson.is_preview = True if request.form.get('is_preview') == 'on' else False

        # Normalize video URLs to embeddable format (e.g., YouTube)
        if lesson.type == LessonType.VIDEO and content_url:
            content_url = dao.normalize_video_url(content_url)
        lesson.content_url = content_url
        db.session.commit()
        flash('Cập nhật bài học thành công!', 'success')
        return redirect(url_for('instructor_lessons', course_id=course.id))
    return render_template('instructor/lesson_form.html', course=course, lesson=lesson, LessonType=LessonType)


@app.route('/instructor/lessons/<int:lesson_id>/delete', methods=['POST'])
@login_required
def instructor_delete_lesson(lesson_id):
    guard = require_instructor_active()
    if guard:
        return guard
    lesson = Lesson.query.get_or_404(lesson_id)
    course = Course.query.filter_by(id=lesson.course_id, instructor_id=current_user.id).first_or_404()
    db.session.delete(lesson)
    db.session.commit()
    flash('Đã xóa bài học.', 'success')
    return redirect(url_for('instructor_lessons', course_id=course.id))


if __name__ == "__main__":
    app.run(debug=True)
