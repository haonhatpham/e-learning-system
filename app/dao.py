import hashlib
import urllib.parse
from app import db
from app.models import *
from sqlalchemy import desc, func
from typing import List, Dict, Tuple
from werkzeug.security import generate_password_hash, check_password_hash
import cloudinary.uploader
from werkzeug.utils import secure_filename

# Cấu hình upload file
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def upload_avatar_to_cloudinary(file, email):
    """Upload avatar lên Cloudinary và trả về URL"""
    try:
        if file and file.filename and allowed_file(file.filename):
            # Upload lên Cloudinary
            result = cloudinary.uploader.upload(
                file,
                folder="e-learning/avatars",
                public_id=f"user_{email}_{secure_filename(file.filename)}",
                overwrite=True,
                resource_type="auto"
            )
            return result['secure_url']
        return None
    except Exception as e:
        print(f"Error uploading avatar: {e}")
        return None


def upload_image_to_cloudinary(file, folder, public_id_prefix):
    """Generic image upload to Cloudinary and return secure URL"""
    try:
        if file and file.filename and allowed_file(file.filename):
            result = cloudinary.uploader.upload(
                file,
                folder=folder,
                public_id=f"{public_id_prefix}_{secure_filename(file.filename)}",
                overwrite=True,
                resource_type="image"
            )
            return result.get('secure_url')
        return None
    except Exception as e:
        print(f"Error uploading image: {e}")
        return None


def upload_video_to_cloudinary(file, folder, public_id_prefix):
    """Upload video lên Cloudinary và trả về URL an toàn."""
    try:
        if not file or not file.filename:
            return None
        result = cloudinary.uploader.upload(
            file,
            folder=folder,
            public_id=f"{public_id_prefix}_{secure_filename(file.filename)}",
            overwrite=True,
            resource_type="video"
        )
        return result.get('secure_url')
    except Exception as e:
        print(f"Error uploading video: {e}")
        return None


def validate_registration_data(username, email, password, confirm_password):
    """Validate dữ liệu đăng ký và trả về (is_valid, error_message)"""

    # Kiểm tra mật khẩu xác nhận
    if password != confirm_password:
        return False, 'Mật khẩu xác nhận không khớp!'

    # Kiểm tra độ dài mật khẩu
    if len(password) < 8:
        return False, 'Mật khẩu phải có ít nhất 8 ký tự!'

    # Kiểm tra username đã tồn tại chưa
    existing_username = get_user_by_username(username)
    if existing_username:
        return False, 'Tên đăng nhập đã được sử dụng!'

    # Kiểm tra email đã tồn tại chưa
    existing_user = get_user_by_email(email)
    if existing_user:
        return False, 'Email đã được sử dụng!'

    return True, ''


def create_user_with_validation(full_name, username, email, password, confirm_password, role, phone=None, avatar_file=None):
    """Tạo user mới với validation đầy đủ"""

    # Validate dữ liệu
    is_valid, error_message = validate_registration_data(username, email, password, confirm_password)
    if not is_valid:
        return None, error_message

    try:
        # Hash password
        hashed_password = generate_password_hash(password)

        # Upload avatar nếu có
        avatar_url = None
        if avatar_file:
            avatar_url = upload_avatar_to_cloudinary(avatar_file, email)

        # Chuyển đổi role string thành enum
        if role == 'student':
            user_role = UserRole.STUDENT
            user_status = UserStatus.ACTIVE  # Học viên được active ngay
        elif role == 'instructor':
            user_role = UserRole.INSTRUCTOR
            user_status = UserStatus.PENDING_APPROVAL  # Giảng viên cần admin duyệt
        else:
            user_role = UserRole.STUDENT
            user_status = UserStatus.ACTIVE

        new_user = User(
            username=username,
            full_name=full_name,
            email=email,
            password=hashed_password,
            role=user_role,
            phone=phone,
            avatar_url=avatar_url,
            status=user_status
        )

        db.session.add(new_user)
        db.session.commit()

        # Nếu là giảng viên, gửi email thông báo chờ duyệt
        if role == 'instructor':
            # TODO: Gửi email thông báo chờ admin duyệt
            # send_pending_approval_email(new_user)
            return new_user, 'Đăng ký thành công! Tài khoản đang chờ admin duyệt.'

        return new_user, 'Đăng ký thành công!'

    except Exception as e:
        db.session.rollback()
        print(f"Error creating user: {e}")
        return None, f'Có lỗi xảy ra: {str(e)}'


def load_categories():
    categories = Category.query.all()
    return categories

def load_featured_courses(limit=6):
    featured_courses = (
        Course.query
        .filter(Course.status == CourseStatus.PUBLISHED)
        .order_by(desc(Course.created_at))
        .limit(limit)
        .all()
    )
    return featured_courses

# Hàm tìm kiếm khóa học theo từ khóa
# Có thể tìm theo:
#   - Tên khóa học (Course.title)
#   - Tên giảng viên (User.full_name)
# Đã thêm bộ lọc

def search_courses(keyword=None, category_id=None, price_min=None, price_max=None):
    query = Course.query.join(User, Course.instructor_id == User.id, isouter=True)

    if keyword:
        query = query.filter(
            (Course.title.ilike(f"%{keyword}%")) |
            (User.full_name.ilike(f"%{keyword}%"))
        )
    if category_id:
        query = query.filter(Course.category_id == category_id)
    if price_min:
        query = query.filter(Course.price >= price_min)
    if price_max:
        query = query.filter(Course.price <= price_max)
    return query.all()


# Hàm lấy chi tiết khóa học theo ID

def get_course_by_id(course_id: int):
    return Course.query.get(course_id)

def auth_user(username, password, role=None):
    # Tìm user theo username trước
    user = User.query.filter_by(username=username.strip()).first()

    if not user:
        return None

    # Kiểm tra mật khẩu bằng check_password_hash
    if not check_password_hash(user.password, password):
        return None

    # Kiểm tra role nếu có yêu cầu
    if role and user.role != role:
        return None

    return user

#Hàm lấy tiến độ học tập 
def get_user_progress(user_id, course_id):
    """
    Tính tiến độ học tập (theo % số bài học đã hoàn thành trong một khóa học)
    """
    # Tổng số bài học trong khóa
    total_lessons = Lesson.query.filter_by(course_id=course_id).count()

    # Số bài đã hoàn thành
    completed_lessons = (
        db.session.query(Progress)
        .join(Lesson, Progress.lesson_id == Lesson.id)
        .filter(
            Progress.user_id == user_id,
            Lesson.course_id == course_id,
            Progress.is_completed == True   # ✅ dùng cột thật
        )
        .count()
    )

    if total_lessons == 0:
        return 0

    return int((completed_lessons / total_lessons) * 100)



def auth_user_by_username(username, password):
    user = User.query.filter_by(username=username).first()
    if user and check_password_hash(user.password, password):
        # Kiểm tra trạng thái tài khoản
        if user.status == UserStatus.ACTIVE:
            return user
        elif user.status == UserStatus.PENDING_APPROVAL:
            # Giảng viên chờ duyệt không thể đăng nhập
            return None
        elif user.status == UserStatus.REJECTED:
            # Tài khoản bị từ chối không thể đăng nhập
            return None
        elif user.status == UserStatus.INACTIVE:
            # Tài khoản bị khóa không thể đăng nhập
            return None
    return None


def get_user_by_id(user_id):
    return User.query.get(user_id)


def get_user_by_email(email):
    return User.query.filter_by(email=email).first()


def get_user_by_username(username):
    return User.query.filter_by(username=username).first()


def create_user(full_name, username, email, password, role, phone=None, avatar_file=None):

    try:
        # Hash password trước khi lưu vào database
        hashed_password = generate_password_hash(password)

        # Upload avatar nếu có
        avatar_url = None
        if avatar_file:
            avatar_url = upload_avatar_to_cloudinary(avatar_file, email)

        # Chuyển đổi role string thành enum
        if role == 'student':
            user_role = UserRole.STUDENT
        elif role == 'instructor':
            user_role = UserRole.INSTRUCTOR
        else:
            user_role = UserRole.STUDENT

        new_user = User(
            username=username,
            full_name=full_name,
            email=email,
            password=hashed_password,  # Sử dụng password đã hash
            role=user_role,
            phone=phone,
            avatar_url=avatar_url,
            status=UserStatus.ACTIVE
        )

        db.session.add(new_user)
        db.session.commit()
        return new_user

    except Exception as e:
        db.session.rollback()
        print(f"Error creating user: {e}")
        return None


def update_user_profile(user_id, **kwargs):
    try:
        user = User.query.get(user_id)
        if user:
            for key, value in kwargs.items():
                if hasattr(user, key):
                    setattr(user, key, value)
            db.session.commit()
            return user
        return None
    except Exception as e:
        db.session.rollback()
        print(f"Error updating user: {e}")
        return None


# =============== ADMIN FUNCTIONS ===============

def count_total_users():
    """Đếm tổng số người dùng"""
    return User.query.count()


def count_total_courses():
    """Đếm tổng số khóa học"""
    return Course.query.count()


def count_pending_instructors():
    """Đếm số giảng viên chờ duyệt"""
    return User.query.filter_by(role=UserRole.INSTRUCTOR, status=UserStatus.PENDING_APPROVAL).count()


def count_total_categories():
    """Đếm tổng số danh mục"""
    return Category.query.count()


def count_users_by_role():
    """Thống kê người dùng theo vai trò"""
    stats = db.session.query(
        User.role,
        func.count(User.id).label('count')
    ).group_by(User.role).all()

    return {role.value: count for role, count in stats}


def count_courses_by_status():
    """Thống kê khóa học theo trạng thái"""
    stats = db.session.query(
        Course.status,
        func.count(Course.id).label('count')
    ).group_by(Course.status).all()

    return {status: count for status, count in stats}


def count_courses_by_category():
    """Thống kê khóa học theo danh mục"""
    stats = db.session.query(
        Category.category_name,  # Sửa từ 'name' thành 'category_name'
        func.count(Course.id).label('count')
    ).join(Course).group_by(Category.category_name).all()

    return {name: count for name, count in stats}


def monthly_registrations():
    """Thống kê đăng ký theo tháng"""
    stats = db.session.query(
        func.date_format(User.created_at, '%Y-%m').label('month'),
        func.count(User.id).label('count')
    ).group_by('month').order_by('month').all()

    return {month: count for month, count in stats}


def get_pending_instructors():
    """Lấy danh sách giảng viên chờ duyệt"""
    return User.query.filter_by(
        role=UserRole.INSTRUCTOR,
        status=UserStatus.PENDING_APPROVAL
    ).order_by(User.created_at.desc()).all()


def approve_instructor(user_id):
    """Duyệt giảng viên"""
    try:
        user = User.query.get(user_id)
        if not user:
            return False, 'Không tìm thấy người dùng'

        if user.role != UserRole.INSTRUCTOR:
            return False, 'Người dùng không phải giảng viên'

        if user.status != UserStatus.PENDING_APPROVAL:
            return False, 'Giảng viên đã được duyệt hoặc từ chối'

        # Cập nhật trạng thái
        user.status = UserStatus.ACTIVE
        db.session.commit()

        # Gửi email thông báo duyệt thành công
        try:
            from app.utils import send_approval_email
            send_approval_email(user)
        except Exception as e:
            print(f"Error sending approval email: {e}")
            # Không return False vì việc duyệt vẫn thành công

        return True, user.full_name

    except Exception as e:
        db.session.rollback()
        print(f"Error approving instructor: {e}")
        return False, str(e)


def reject_instructor(user_id):
    """Từ chối giảng viên"""
    try:
        user = User.query.get(user_id)
        if not user:
            return False, 'Không tìm thấy người dùng'

        if user.role != UserRole.INSTRUCTOR:
            return False, 'Người dùng không phải giảng viên'

        if user.status != UserStatus.PENDING_APPROVAL:
            return False, 'Giảng viên đã được duyệt hoặc từ chối'

        # Cập nhật trạng thái
        user.status = UserStatus.REJECTED
        db.session.commit()

        # Gửi email thông báo từ chối
        try:
            from app.utils import send_rejection_email
            send_rejection_email(user)
        except Exception as e:
            print(f"Error sending rejection email: {e}")
            # Không return False vì việc từ chối vẫn thành công

        return True, user.full_name

    except Exception as e:
        db.session.rollback()
        print(f"Error rejecting instructor: {e}")
        return False, str(e)




def normalize_video_url(url: str) -> str:
    """Normalize common video URLs to embeddable ones (currently YouTube + Vimeo)."""
    try:
        if not url:
            return url

        # Use urllib.parse to analyze
        parsed = urllib.parse.urlparse(url)
        hostname = (parsed.hostname or '').lower()

        # Helper: parse t/start into seconds
        def _to_seconds(raw: str) -> int:
            try:
                if not raw:
                    return 0
                raw = raw.strip().lower()
                if raw.isdigit():
                    return int(raw)
                # formats like 1h2m3s, 2m10s, 30s
                import re
                hours = minutes = seconds = 0
                match_h = re.search(r"(\d+)h", raw)
                match_m = re.search(r"(\d+)m", raw)
                match_s = re.search(r"(\d+)s", raw)
                if match_h:
                    hours = int(match_h.group(1))
                if match_m:
                    minutes = int(match_m.group(1))
                if match_s:
                    seconds = int(match_s.group(1))
                if not (match_h or match_m or match_s):
                    return int(raw)
                return hours * 3600 + minutes * 60 + seconds
            except Exception:
                return 0

        # YouTube family
        if 'youtube.com' in hostname or 'youtu.be' in hostname or 'youtube-nocookie.com' in hostname:
            # Short link: youtu.be/VIDEO_ID
            if 'youtu.be' in hostname:
                video_id = parsed.path.lstrip('/')
                qs = urllib.parse.parse_qs(parsed.query or '')
                start = _to_seconds(qs.get('t', [''])[0] or qs.get('start', [''])[0])
                start_query = f"?start={start}" if start > 0 else ''
                return f"https://www.youtube.com/embed/{video_id}{start_query}"

            # Shorts: youtube.com/shorts/VIDEO_ID
            if parsed.path.startswith('/shorts/'):
                video_id = parsed.path.split('/shorts/')[1].split('/')[0]
                return f"https://www.youtube.com/embed/{video_id}"

            # Standard watch: youtube.com/watch?v=VIDEO_ID
            if parsed.path == '/watch':
                qs = urllib.parse.parse_qs(parsed.query or '')
                video_id = (qs.get('v') or [''])[0]
                start = _to_seconds(qs.get('t', [''])[0] or qs.get('start', [''])[0])
                start_query = f"?start={start}" if start > 0 else ''
                if video_id:
                    return f"https://www.youtube.com/embed/{video_id}{start_query}"
            # Already embed or other path: return as-is
            return url

        # Vimeo
        if 'vimeo.com' in hostname and 'player.vimeo.com' not in hostname:
            video_id = parsed.path.strip('/').split('/')[0]
            if video_id and video_id.isdigit():
                return f"https://player.vimeo.com/video/{video_id}"

        return url
    except Exception:
        return url

#cuu
def to_embeddable_video_url(url: str) -> str:
    """Compute a safe embeddable URL at render time (idempotent)."""
    try:
        if not url:
            return url
        return normalize_video_url(url)
    except Exception:
        return url


def get_quiz_questions(lesson_id: int):
    lesson = Lesson.query.get(lesson_id)
    if not lesson:
        return None
    if lesson.type != LessonType.QUIZ:
        return None  #
    return lesson.content_data.get("questions", [])


# ================= INSTRUCTOR STATS =================
def get_instructor_course_stats(instructor_id: int, month: int = None, year: int = None):
    """Trả về thống kê khóa học của một giảng viên theo tháng/năm.

    Kết quả gồm:
    - stats: danh sách tuple (stt, course_id, title, num_students, revenue)
    - labels: danh sách tiêu đề khóa học (title)
    - student_counts: danh sách số học viên (num_students)
    - revenues: danh sách doanh thu (float)
    - total_revenue: tổng doanh thu (float)
    """

    query = (
        db.session.query(
            Course.id,
            Course.title,
            func.count(Enrollment.id).label("num_students"),
            func.coalesce(func.sum(Payment.amount), 0).label("revenue")
        )
        .outerjoin(Enrollment, Enrollment.course_id == Course.id)
        .outerjoin(Payment, Payment.enrollment_id == Enrollment.id)
        .filter(Course.instructor_id == instructor_id, Payment.status == PaymentStatus.COMPLETED)
    )

    if month:
        query = query.filter(func.extract("month", Payment.payment_date) == month)
    if year:
        query = query.filter(func.extract("year", Payment.payment_date) == year)

    query = query.group_by(Course.id, Course.title)
    raw = query.all()

    stats = [(idx + 1, c.id, c.title, c.num_students, float(c.revenue)) for idx, c in enumerate(raw)]
    labels = [c.title for c in raw]
    student_counts = [c.num_students for c in raw]
    revenues = [float(c.revenue) for c in raw]
    total_revenue = float(sum(revenues))

    return {
        'stats': stats,
        'labels': labels,
        'student_counts': student_counts,
        'revenues': revenues,
        'total_revenue': total_revenue
    }


def get_admin_instructor_stats(month: int = None, year: int = None):
    """Thống kê tổng hợp theo giảng viên cho trang admin.

    Trả về list các bản ghi (User.id, User.full_name, num_students, revenue).
    """
    query = (
        db.session.query(
            User.id,
            User.full_name,
            func.count(Enrollment.id).label("num_students"),
            func.coalesce(func.sum(Payment.amount), 0).label("revenue")
        )
        .join(Course, Course.instructor_id == User.id)
        .outerjoin(Enrollment, Enrollment.course_id == Course.id)
        .outerjoin(Payment, Payment.enrollment_id == Enrollment.id)
        .filter(User.role == UserRole.INSTRUCTOR, Payment.status == PaymentStatus.COMPLETED)
        .group_by(User.id, User.full_name)
        .order_by(User.id)
    )

    if month:
        query = query.filter(func.extract("month", Payment.payment_date) == month)
    if year:
        query = query.filter(func.extract("year", Payment.payment_date) == year)

    return query.all()