from flask import render_template, request, redirect, url_for, flash, jsonify, session
from app import app, dao, db
from app import login
from app.dao import load_categories, load_featured_courses, search_courses, get_user_progress
from flask_login import login_user, logout_user, current_user, login_required
from app.utils import send_welcome_email, send_registration_confirmation
from app.models import UserRole, UserStatus, Course, CourseStatus, CourseLevel, Lesson, LessonType, Enrollment, Payment, \
    PaymentMethod, PaymentStatus, Progress, User, ForumComment
from app.permissions import require_instructor, require_admin, require_student
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
    return render_template('index.html', categories=categories, featured_courses=featured_courses)

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
    # Admin dùng giao diện quản trị riêng (/admin), không tương tác ở giao diện học viên
    if current_user.is_authenticated and current_user.role == UserRole.ADMIN:
        return redirect('/admin')
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

#Theo dõi tiến độ học tập
@app.route("/progress")
@login_required
def progress():
    enrollments = Enrollment.query.filter_by(user_id=current_user.id).all()

    courses_progress = []
    for e in enrollments:
        course = Course.query.get(e.course_id)
        percent = get_user_progress(current_user.id, course.id)

        courses_progress.append({
            "id": course.id,
            "name": course.title,             # ✅ dùng title thay cho name
            "image": course.cover_image,      # ✅ dùng cover_image thay cho image_url
            "progress": percent
        })

    return render_template("progress.html",
                           student_name=current_user.full_name,
                           courses=courses_progress)

# Tiến độ chi tiết của một khóa học
@app.route("/course/<int:course_id>/progress")
@login_required
def course_progress(course_id):
    course = Course.query.get_or_404(course_id)
    
    # Kiểm tra user đã đăng ký khóa học chưa
    enrollment = Enrollment.query.filter_by(user_id=current_user.id, course_id=course_id).first()
    if not enrollment:
        flash('Bạn chưa đăng ký khóa học này!', 'error')
        return redirect(url_for('course_detail', course_id=course_id))
    
    # Lấy danh sách bài học đã sắp xếp theo thứ tự
    lessons = Lesson.query.filter_by(course_id=course_id).order_by(Lesson.lesson_order).all()
    
    # Lấy tiến độ của user cho từng bài học
    lesson_progress = []
    total_lessons = len(lessons)
    completed_lessons = 0
    
    for lesson in lessons:
        progress = Progress.query.filter_by(user_id=current_user.id, lesson_id=lesson.id).first()
        is_completed = progress.is_completed if progress else False
        
        if is_completed:
            completed_lessons += 1
            
        lesson_progress.append({
            'lesson': lesson,
            'is_completed': is_completed,
            'completed_at': progress.completed_at if progress else None
        })
    
    # Tính phần trăm hoàn thành
    progress_percentage = (completed_lessons / total_lessons * 100) if total_lessons > 0 else 0
    
    return render_template('course_progress.html',
                         course=course,
                         enrollment=enrollment,
                         lesson_progress=lesson_progress,
                         total_lessons=total_lessons,
                         completed_lessons=completed_lessons,
                         progress_percentage=progress_percentage)


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
    text_content = None
    questions = None

    if lesson.type == LessonType.VIDEO:
        embed_url = dao.to_embeddable_video_url(lesson.content_url)
    elif (lesson.type == LessonType.TEXT) and lesson.content_data:
        try:
            if isinstance(lesson.content_data, dict):
                text_content = lesson.content_data.get('html', '')
            else:
                text_content = lesson.content_data
        except:
            text_content = ''
    elif lesson.type == LessonType.QUIZ and lesson.content_data:
        try:
            if isinstance(lesson.content_data, dict):
                questions = lesson.content_data.get('questions', [])
                # Add index to questions for form handling
                for i, q in enumerate(questions):
                    q['index'] = i
            else:
                questions = []
        except:
            questions = []

    user_progress = None
    assignment_submission = None
    all_lessons_progress = {}
    if current_user.is_authenticated:
        user_progress = Progress.query.filter_by(user_id=current_user.id, lesson_id=lesson.id).first()
        
        # Lấy progress của tất cả bài học trong khóa học
        all_progress = Progress.query.join(Lesson).filter(
            Progress.user_id == current_user.id,
            Lesson.course_id == course.id
        ).all()
        for p in all_progress:
            all_lessons_progress[p.lesson_id] = p

    return render_template('lesson_view.html',
                           course=course,
                           lesson=lesson,
                           embed_url=embed_url,
                           text_content=text_content,
                           questions=questions,
                           user_progress=user_progress,
                           assignment_submission=assignment_submission,
                           all_lessons_progress=all_lessons_progress)




@app.route('/course/<int:course_id>/lesson/<int:lesson_id>/submit-quiz', methods=['POST'])
@login_required
def submit_quiz(course_id, lesson_id):
    course = Course.query.get_or_404(course_id)
    lesson = Lesson.query.filter_by(id=lesson_id, course_id=course.id).first_or_404()
    if not can_view_lesson(lesson, course):
        flash('Bạn không có quyền nộp bài cho bài học này.', 'error')
        return redirect(url_for('course_detail', course_id=course.id))

    if lesson.type != LessonType.QUIZ or not lesson.content_data:
        flash('Bài học không phải quiz hoặc thiếu dữ liệu.', 'error')
        return redirect(url_for('view_lesson', course_id=course.id, lesson_id=lesson.id))

    questions = lesson.content_data.get('questions', []) if isinstance(lesson.content_data, dict) else []
    total = len(questions)
    correct = 0
    for idx, q in enumerate(questions):
        try:
            selected = request.form.get(f'q{idx}')
            expected = q.get('answer')
            if selected is not None and expected is not None and int(selected) == int(expected):
                correct += 1
        except Exception:
            pass

    progress = Progress.query.filter_by(user_id=current_user.id, lesson_id=lesson.id).first()
    if not progress:
        progress = Progress(user_id=current_user.id, lesson_id=lesson.id)
        db.session.add(progress)
    progress.score = correct
    progress.is_completed = True
    progress.completed_at = datetime.now()
    db.session.commit()

    flash(f'Bạn đã nộp quiz. Điểm: {correct}/{total}', 'success')
    return redirect(url_for('view_lesson', course_id=course.id, lesson_id=lesson.id))


@app.route('/course/<int:course_id>/lesson/<int:lesson_id>/mark-complete', methods=['POST'])
@login_required
def mark_lesson_complete(course_id, lesson_id):
    course = Course.query.get_or_404(course_id)
    lesson = Lesson.query.filter_by(id=lesson_id, course_id=course.id).first_or_404()
    
    if not can_view_lesson(lesson, course):
        flash('Bạn không có quyền đánh dấu hoàn thành bài học này.', 'error')
        return redirect(url_for('course_detail', course_id=course.id))

    # Chỉ cho phép đánh dấu hoàn thành bài TEXT và VIDEO
    if lesson.type == LessonType.QUIZ:
        flash('Bài quiz được đánh dấu hoàn thành khi nộp bài.', 'warning')
        return redirect(url_for('view_lesson', course_id=course.id, lesson_id=lesson.id))

    # Tạo hoặc cập nhật progress
    progress = Progress.query.filter_by(user_id=current_user.id, lesson_id=lesson.id).first()
    if not progress:
        progress = Progress(user_id=current_user.id, lesson_id=lesson.id)
        db.session.add(progress)
    
    progress.is_completed = True
    progress.completed_at = datetime.now()
    db.session.commit()

    flash('Đã đánh dấu hoàn thành bài học!', 'success')
    return redirect(url_for('view_lesson', course_id=course.id, lesson_id=lesson.id))


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
                    flash('Tài khoản giảng viên đang chờ admin duyệt! Vui lòng liên hệ admin để được kích hoạt.',
                          'warning')
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
                flash(
                    'Đăng ký giảng viên thành công! Tài khoản đang chờ admin duyệt. Bạn sẽ nhận được email thông báo khi được kích hoạt.',
                    'warning')
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


# Hộp thư chat cho giảng viên: chọn khóa học để vào phòng chat
@app.route('/instructor/chats')
@login_required
def instructor_chats():
    if current_user.role != UserRole.INSTRUCTOR:
        return redirect(url_for('index'))
    # các khóa do giảng viên tạo
    courses = Course.query.filter_by(instructor_id=current_user.id).all()
    return render_template('instructor/chats.html', courses=courses)


# Thảo luận khóa học
@app.route('/course/<int:course_id>/forum', methods=['GET', 'POST'])
@login_required
def course_forum(course_id):
    course = Course.query.get_or_404(course_id)

    # Tạo chủ đề mới
    if request.method == 'POST':
        content_text = request.form.get('content', '').strip()
        lesson_id = request.form.get('lesson_id', type=int)
        parent_id = request.form.get('parent_id', type=int)

        if not content_text:
            flash('Vui lòng nhập nội dung.', 'warning')
            return redirect(url_for('course_forum', course_id=course.id, lesson_id=lesson_id or None))

        # Lưu theo định dạng JSON đơn giản để có thể filter theo bài học
        payload = { 'type': 'discussion', 'text': content_text }
        if lesson_id:
            payload['lesson_id'] = lesson_id

        db.session.add(ForumComment(
            course_id=course.id,
            user_id=current_user.id,
            content=json.dumps(payload, ensure_ascii=False),
            parent_comment_id=parent_id
        ))
        db.session.commit()
        flash('Đã đăng bình luận.', 'success')
        return redirect(url_for('course_forum', course_id=course.id, lesson_id=lesson_id or None))

    # Filter theo bài học nếu có
    filter_lesson_id = request.args.get('lesson_id', type=int)

    comments = ForumComment.query.filter_by(course_id=course.id).order_by(ForumComment.created_at.asc()).all()
    parsed_comments = []
    for c in comments:
        try:
            data = json.loads(c.content)
            text = data.get('text') if isinstance(data, dict) else c.content
            lesson_tag = data.get('lesson_id') if isinstance(data, dict) else None
        except Exception:
            text = c.content
            lesson_tag = None
        if filter_lesson_id and lesson_tag != filter_lesson_id:
            continue
        parsed_comments.append({
            'id': c.id,
            'user': c.user,
            'text': text,
            'lesson_id': lesson_tag,
            'created_at': c.created_at,
            'parent_id': c.parent_comment_id
        })

    # Xây cây bình luận
    by_parent = {}
    for pc in parsed_comments:
        by_parent.setdefault(pc['parent_id'], []).append(pc)

    def build_tree(parent_id=None):
        nodes = by_parent.get(parent_id, [])
        for n in nodes:
            n['replies'] = build_tree(n['id'])
        return nodes

    tree = build_tree(None)

    lessons_sorted = course.lessons.order_by(Lesson.lesson_order).all() if hasattr(course.lessons, 'order_by') else sorted(course.lessons, key=lambda l: l.lesson_order)

    return render_template('course_forum.html', course=course, comments_tree=tree, lessons=lessons_sorted, selected_lesson_id=filter_lesson_id)


@app.route('/course/<int:course_id>/chat')
@login_required
def course_chat(course_id):
    course = Course.query.get_or_404(course_id)
    lesson_id = request.args.get('lesson_id', type=int)

    # Chỉ cho phép học viên đã ghi danh, giảng viên chủ khóa hoặc admin
    is_owner = current_user.is_authenticated and course.instructor_id == current_user.id
    is_admin = current_user.is_authenticated and current_user.role == UserRole.ADMIN
    is_enrolled = Enrollment.query.filter_by(user_id=current_user.id, course_id=course.id).first() is not None
    if not (is_owner or is_admin or is_enrolled):
        flash('Bạn cần đăng ký khóa học để sử dụng chat.', 'warning')
        return redirect(url_for('course_detail', course_id=course.id))

    # Danh sách học viên đã ghi danh (để giảng viên chủ động bắt đầu chat)
    enrolled_students = []
    if current_user.role == UserRole.INSTRUCTOR and current_user.id == course.instructor_id:
        enrolled_students = (
            db.session.query(User)
            .join(Enrollment, Enrollment.user_id == User.id)
            .filter(Enrollment.course_id == course.id, User.role == UserRole.STUDENT)
            .all()
        )

    firebase_config = {
        "apiKey": "AIzaSyBs0wj3BDAFu6eeosagQfnZM4p25C3xUCM",
        "authDomain": "ecourse-d6de4.firebaseapp.com",
        "projectId": "ecourse-d6de4",
        "appId": "1:459535957510:web:5bf6f28e1d91daa625cd87"
    }
    return render_template('course_chat.html', course=course, lesson_id=lesson_id, firebase_config=firebase_config, enrolled_students=enrolled_students)

@app.route('/checkout/<int:course_id>')
@login_required
def checkout(course_id):
    course = Course.query.get_or_404(course_id)
    # Chặn giảng viên đăng ký khóa học của chính mình
    if course.instructor_id == current_user.id:
        flash('Bạn là giảng viên của khóa học này, không thể tự đăng ký.', 'warning')
        return redirect(url_for('course_detail', course_id=course_id))

    # Kiểm tra đã ghi danh chưa
    existing_enrollment = Enrollment.query.filter_by(user_id=current_user.id, course_id=course_id).first()
    if existing_enrollment:
        flash('Bạn đã đăng ký khóa học này rồi.', 'warning')
        return redirect(url_for('course_detail', course_id=course_id))

    # Nếu khóa học miễn phí (0đ) thì ghi danh luôn, không qua thanh toán
    try:
        price = course.price or 0
        is_free = False
        if isinstance(price, (int, float)):
            is_free = float(price) <= 0
        else:
            # price có thể là Decimal
            is_free = float(price) <= 0
    except Exception:
        is_free = False

    if is_free:
        enr = Enrollment(user_id=current_user.id, course_id=course_id, enroll_date=datetime.now())
        db.session.add(enr)
        db.session.commit()
        flash('Đăng ký thành công khóa học miễn phí!', 'success')
        return redirect(url_for('course_detail', course_id=course_id))

    return render_template('checkout.html', course=course)


@app.route('/checkout/<int:course_id>', methods=['POST'])
@login_required
def process_checkout(course_id):
    course = Course.query.get_or_404(course_id)
    # Chặn giảng viên đăng ký khóa học của chính mình
    if course.instructor_id == current_user.id:
        flash('Bạn là giảng viên của khóa học này, không thể tự đăng ký.', 'warning')
        return redirect(url_for('course_detail', course_id=course_id))
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
        # ghi trực tiếp
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
    request_id = f"REQ-{int(time.time() * 1000)}"
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
        f"accessKey={access_key}&amount={params.get('amount', '')}"
        f"&extraData={params.get('extraData', '')}"
        f"&message={params.get('message', '')}"
        f"&orderId={params.get('orderId', '')}"
        f"&orderInfo={params.get('orderInfo', '')}"
        f"&orderType={params.get('orderType', '')}"
        f"&partnerCode={params.get('partnerCode', '')}"
        f"&payType={params.get('payType', '')}"
        f"&requestId={params.get('requestId', '')}"
        f"&responseTime={params.get('responseTime', '')}"
        f"&resultCode={params.get('resultCode', '')}"
        f"&transId={params.get('transId', '')}"
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
        amount_vnd = Decimal(int(params.get('amount', '0')))
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
        f"accessKey={access_key}&amount={params.get('amount', '')}"
        f"&extraData={params.get('extraData', '')}"
        f"&message={params.get('message', '')}"
        f"&orderId={params.get('orderId', '')}"
        f"&orderInfo={params.get('orderInfo', '')}"
        f"&orderType={params.get('orderType', '')}"
        f"&partnerCode={params.get('partnerCode', '')}"
        f"&payType={params.get('payType', '')}"
        f"&requestId={params.get('requestId', '')}"
        f"&responseTime={params.get('responseTime', '')}"
        f"&resultCode={params.get('resultCode', '')}"
        f"&transId={params.get('transId', '')}"
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


@app.route('/instructor/courses')
@login_required
def instructor_courses():
    guard = require_instructor()
    if guard:
        return guard
    courses = Course.query.filter_by(instructor_id=current_user.id).order_by(Course.created_at.desc()).all()
    return render_template('instructor/courses.html', courses=courses, CourseStatus=CourseStatus)


@app.route('/instructor/courses/create', methods=['GET', 'POST'])
@login_required
def instructor_create_course():
    guard = require_instructor()
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
            cover_url = dao.upload_image_to_cloudinary(cover_file, 'e-learning/course_covers',
                                                       f"course_{current_user.id}")

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

    return render_template('instructor/course_form.html', course=None, CourseStatus=CourseStatus,
                           CourseLevel=CourseLevel)


@app.route('/instructor/courses/<int:course_id>/edit', methods=['GET', 'POST'])
@login_required
def instructor_edit_course(course_id):
    guard = require_instructor()
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
    return render_template('instructor/course_form.html', course=course, CourseStatus=CourseStatus,
                           CourseLevel=CourseLevel)


@app.route('/instructor/courses/<int:course_id>/delete', methods=['POST'])
@login_required
def instructor_delete_course(course_id):
    guard = require_instructor()
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
    guard = require_instructor()
    if guard:
        return guard
    course = Course.query.filter_by(id=course_id, instructor_id=current_user.id).first_or_404()
    lessons = Lesson.query.filter_by(course_id=course.id).order_by(Lesson.lesson_order.asc()).all()
    return render_template('instructor/lessons.html', course=course, lessons=lessons, LessonType=LessonType)


@app.route('/instructor/courses/<int:course_id>/lessons/create', methods=['GET', 'POST'])
@login_required
def instructor_create_lesson(course_id):
    guard = require_instructor()
    if guard:
        return guard
    course = Course.query.filter_by(id=course_id, instructor_id=current_user.id).first_or_404()
    if request.method == 'POST':
        title = request.form.get('title')
        lesson_type = request.form.get('type')
        content_url = request.form.get('content_url')
        content_data_raw = request.form.get('content_data')
        video_file = request.files.get('video_file')
        lesson_order = request.form.get('lesson_order', type=int) or 0
        duration_seconds = request.form.get('duration_seconds', type=int) or 0
        is_preview = True if request.form.get('is_preview') == 'on' else False

        try:
            content_data = json.loads(content_data_raw) if content_data_raw else None
        except Exception:
            content_data = None

        # Handle video upload or normalize URL
        if lesson_type and lesson_type.lower() == 'video':
            if video_file and video_file.filename:
                uploaded_url = dao.upload_video_to_cloudinary(video_file, 'e-learning/videos',
                                                              f"course_{course.id}_lesson")
                if uploaded_url:
                    content_url = uploaded_url
            elif content_url:
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
    guard = require_instructor()
    if guard:
        return guard
    lesson = Lesson.query.get_or_404(lesson_id)
    course = Course.query.filter_by(id=lesson.course_id, instructor_id=current_user.id).first_or_404()
    if request.method == 'POST':
        lesson.title = request.form.get('title')
        lesson.type = LessonType(request.form.get('type'))
        content_url = request.form.get('content_url')
        content_data_raw = request.form.get('content_data')
        video_file = request.files.get('video_file')
        try:
            lesson.content_data = json.loads(content_data_raw) if content_data_raw else None
        except Exception:
            lesson.content_data = None
        lesson.lesson_order = request.form.get('lesson_order', type=int) or 0
        lesson.duration_seconds = request.form.get('duration_seconds', type=int) or 0
        lesson.is_preview = True if request.form.get('is_preview') == 'on' else False

        # Handle video upload or normalize URL
        if lesson.type == LessonType.VIDEO:
            if video_file and video_file.filename:
                uploaded_url = dao.upload_video_to_cloudinary(video_file, 'e-learning/videos',
                                                              f"course_{course.id}_lesson_{lesson.id}")
                if uploaded_url:
                    content_url = uploaded_url
            elif content_url:
                content_url = dao.normalize_video_url(content_url)
        lesson.content_url = content_url
        db.session.commit()
        flash('Cập nhật bài học thành công!', 'success')
        return redirect(url_for('instructor_lessons', course_id=course.id))
    return render_template('instructor/lesson_form.html', course=course, lesson=lesson, LessonType=LessonType)


@app.route('/instructor/lessons/<int:lesson_id>/delete', methods=['POST'])
@login_required
def instructor_delete_lesson(lesson_id):
    guard = require_instructor()
    if guard:
        return guard
    lesson = Lesson.query.get_or_404(lesson_id)
    course = Course.query.filter_by(id=lesson.course_id, instructor_id=current_user.id).first_or_404()
    db.session.delete(lesson)
    db.session.commit()
    flash('Đã xóa bài học.', 'success')
    return redirect(url_for('instructor_lessons', course_id=course.id))




@app.route("/instructor/stats")
@login_required
def instructor_stats():
    if current_user.role != UserRole.INSTRUCTOR:
        return "Chỉ giảng viên mới xem được thống kê", 403

    month = request.args.get("month", type=int)
    year = request.args.get("year", default=datetime.now().year, type=int)

    # Lấy thống kê từ DAO
    stats_data = dao.get_instructor_course_stats(current_user.id, month=month, year=year)
    stats = stats_data['stats']
    labels = stats_data['labels']
    student_counts = stats_data['student_counts']
    revenues = stats_data['revenues']
    total_revenue = stats_data['total_revenue']

    return render_template(
        "chart_instructor.html",
        labels=labels,
        student_counts=student_counts,
        revenues=revenues,
        stats=stats,
        total_revenue=total_revenue,
        month=month,
        year=year
    )


if __name__ == "__main__":
    app.run(debug=True,host="0.0.0.0",port=80)
