from flask import render_template, request, redirect, url_for, flash, session, jsonify
from app import app, dao
from app import login
from app.dao import load_categories, load_featured_courses, search_courses, get_course_by_id
from flask_login import login_user, logout_user, current_user, login_required
from app.utils import send_welcome_email, send_registration_confirmation
from app.models import UserRole, UserStatus, Course # Thêm Course
from app import admin


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
    return render_template("course_detail.html", course=course, prev_url=prev_url)




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
            # Kiểm tra lý do thất bại để hiển thị thông báo cụ thể
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
        # Lấy dữ liệu từ form
        full_name = request.form.get('full_name')
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        role = request.form.get('role')
        phone = request.form.get('phone')
        avatar_file = request.files.get('avatar') if 'avatar' in request.files else None

        # Gọi dao.py để xử lý business logic
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
            # Gửi email chào mừng (chỉ cho sinh viên)
            try:
                send_welcome_email(new_user)
                send_registration_confirmation(new_user)

                # Thông báo khác nhau theo role
                if role == 'instructor':
                    flash('Đăng ký giảng viên thành công! Tài khoản đang chờ admin duyệt. Bạn sẽ nhận được email thông báo khi được kích hoạt.', 'warning')
                else:
                    flash('Đăng ký thành công! Email chào mừng đã được gửi đến hộp thư của bạn.', 'success')

            except Exception as e:
                if role == 'instructor':
                    flash('Đăng ký giảng viên thành công! Tài khoản đang chờ admin duyệt. Có lỗi khi gửi email xác nhận.', 'warning')
                else:
                    flash('Đăng ký thành công! Nhưng có lỗi khi gửi email xác nhận.', 'warning')
                print(f"Email error: {e}")

            return redirect(url_for('login_user_route'))
        else:
            # Hiển thị lỗi từ dao.py
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


@login.user_loader
def load_user(user_id):
    return dao.get_user_by_id(user_id)


# ==================== ADMIN API ROUTES ====================
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


if __name__ == "__main__":
    app.run(debug=True)

