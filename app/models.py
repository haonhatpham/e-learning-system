from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Boolean, Text, DECIMAL, Enum, JSON, CheckConstraint
# from flask_login import UserMixin  # Tạm thời comment lại
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, backref
from app import db
import enum

# Enum classes
class UserRole(enum.Enum):
    STUDENT = 'student'
    INSTRUCTOR = 'instructor'
    ADMIN = 'admin'

class UserStatus(enum.Enum):
    ACTIVE = 'active'
    INACTIVE = 'inactive'
    PENDING_APPROVAL = 'pending_approval'
    REJECTED = 'rejected'

class CourseStatus(enum.Enum):
    DRAFT = 'draft'
    PUBLISHED = 'published'
    ARCHIVED = 'archived'

class CourseLevel(enum.Enum):
    BEGINNER = 'beginner'
    INTERMEDIATE = 'intermediate'
    ADVANCED = 'advanced'

class LessonType(enum.Enum):
    VIDEO = 'video'
    QUIZ = 'quiz'
    TEXT = 'text'
    ASSIGNMENT = 'assignment'

class PaymentMethod(enum.Enum):
    MOMO = 'momo'
    VNPAY = 'vnpay'

class PaymentStatus(enum.Enum):
    PENDING = 'pending'
    COMPLETED = 'completed'
    FAILED = 'failed'
    REFUNDED = 'refunded'

# Base Model - Tất cả các model khác sẽ kế thừa từ đây
class BaseModel(db.Model):
    __abstract__ = True
    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

# User Model - Kế thừa từ BaseModel (tạm thời không dùng UserMixin)
class User(BaseModel):  # Tạm thời bỏ UserMixin
    __tablename__ = 'users'
    
    full_name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.STUDENT)
    status = Column(Enum(UserStatus), default=UserStatus.ACTIVE)
    avatar_url = Column(String(500))
    
    # Relationships
    courses_created = relationship('Course', backref='instructor', lazy=True, foreign_keys='Course.instructor_id')
    enrollments = relationship('Enrollment', backref='user', lazy=True)
    progress_records = relationship('Progress', backref='user', lazy=True)
    reviews = relationship('Review', backref='user', lazy=True)
    forum_comments = relationship('ForumComment', backref='user', lazy=True)

# Category Model - Kế thừa từ BaseModel
class Category(BaseModel):
    __tablename__ = 'categories'
    
    category_name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    
    # Relationships
    courses = relationship('Course', backref='category', lazy=True)

# Course Model - Kế thừa từ BaseModel
class Course(BaseModel):
    __tablename__ = 'courses'
    
    title = Column(String(200), nullable=False)
    price = Column(DECIMAL(10, 2), nullable=False, default=0.00)
    description = Column(Text)
    cover_image = Column(String(500))
    category_id = Column(ForeignKey('categories.id'), nullable=True)
    instructor_id = Column(ForeignKey('users.id'), nullable=True, default=None)
    status = Column(Enum(CourseStatus), default=CourseStatus.DRAFT)
    level = Column(Enum(CourseLevel), default=CourseLevel.BEGINNER)
    
    # Relationships
    lessons = relationship('Lesson', backref='course', lazy=True, order_by='Lesson.lesson_order')
    enrollments = relationship('Enrollment', backref='course', lazy=True)
    reviews = relationship('Review', backref='course', lazy=True)
    forum_comments = relationship('ForumComment', backref='course', lazy=True)

# Lesson Model - Kế thừa từ BaseModel
class Lesson(BaseModel):
    __tablename__ = 'lessons'
    
    title = Column(String(200), nullable=False)
    type = Column(Enum(LessonType), nullable=False)
    content_url = Column(String(500))
    content_data = Column(JSON)
    course_id = Column(ForeignKey('courses.id'), nullable=False)
    lesson_order = Column(Integer, nullable=False, default=0)
    duration_seconds = Column(Integer, default=0)
    is_preview = Column(Boolean, default=False)
    
    # Relationships
    progress_records = relationship('Progress', backref='lesson', lazy=True)

# Enrollment Model - Kế thừa từ BaseModel
class Enrollment(BaseModel):
    __tablename__ = 'enrollments'
    
    user_id = Column(ForeignKey('users.id'), nullable=False)
    course_id = Column(ForeignKey('courses.id'), nullable=False)
    enroll_date = Column(DateTime, default=func.now())
    
    # Relationships
    payments = relationship('Payment', backref='enrollment', lazy=True)
    
    # Unique constraint
    __table_args__ = (db.UniqueConstraint('user_id', 'course_id', name='unique_user_course'),)

# Payment Model - Kế thừa từ BaseModel
class Payment(BaseModel):
    __tablename__ = 'payments'
    
    enrollment_id = Column(ForeignKey('enrollments.id'), nullable=False)
    amount = Column(DECIMAL(10, 2), nullable=False)
    payment_method = Column(Enum(PaymentMethod), nullable=False)
    transaction_id = Column(String(100))
    status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING)
    payment_date = Column(DateTime, default=func.now())

# Progress Model - Kế thừa từ BaseModel
class Progress(BaseModel):
    __tablename__ = 'progress'
    
    user_id = Column(ForeignKey('users.id'), nullable=False)
    lesson_id = Column(ForeignKey('lessons.id'), nullable=False)
    is_completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)
    time_spent = Column(Integer, default=0)
    score = Column(Integer, nullable=True)
    
    # Unique constraint
    __table_args__ = (db.UniqueConstraint('user_id', 'lesson_id', name='unique_user_lesson'),)

# Review Model - Kế thừa từ BaseModel
class Review(BaseModel):
    __tablename__ = 'reviews'
    
    user_id = Column(ForeignKey('users.id'), nullable=False)
    course_id = Column(ForeignKey('courses.id'), nullable=False)
    rating = Column(Integer, nullable=False)
    content = Column(Text)
    
    # Check constraint for rating
    __table_args__ = (
        CheckConstraint('rating >= 1 AND rating <= 5', name='check_rating_range'),
        db.UniqueConstraint('user_id', 'course_id', name='unique_user_course_review')
    )

# Forum Comment Model - Kế thừa từ BaseModel
class ForumComment(BaseModel):
    __tablename__ = 'forum_comments'
    
    course_id = Column(ForeignKey('courses.id'), nullable=True)
    user_id = Column(ForeignKey('users.id'), nullable=True)
    content = Column(Text, nullable=False)
    parent_comment_id = Column(ForeignKey('forum_comments.id'), nullable=True)
    
    # Self-referencing relationship for nested comments
    replies = relationship('ForumComment', backref=backref('parent', remote_side='ForumComment.id'))

# Hàm tạo dữ liệu mẫu
def create_sample_data():
    """Tạo dữ liệu mẫu cho ứng dụng"""
    from app import db
    
    # Kiểm tra và tạo categories nếu chưa có
    existing_categories = Category.query.all()
    if not existing_categories:
        categories = [
            Category(category_name='Lập trình Web', description='Các khóa học về phát triển web, HTML, CSS, JavaScript, React, Node.js'),
            Category(category_name='Lập trình Mobile', description='Các khóa học về phát triển ứng dụng di động Android, iOS, React Native'),
            Category(category_name='Data Science', description='Các khóa học về khoa học dữ liệu, Python, Machine Learning, SQL'),
            Category(category_name='AI & Machine Learning', description='Các khóa học về trí tuệ nhân tạo, deep learning, neural networks'),
        ]
        
        for category in categories:
            db.session.add(category)
        
        try:
            db.session.commit()
            print("Categories created successfully!")
        except Exception as e:
            db.session.rollback()
            print(f"Error creating categories: {e}")
            return
    else:
        print(f"Categories already exist ({len(existing_categories)} found)")
    
    # Kiểm tra và tạo courses nếu chưa có
    existing_courses = Course.query.all()
    if not existing_courses:
        # Lấy categories để map ID
        categories = Category.query.all()
        category_map = {cat.category_name: cat.id for cat in categories}
        
        courses = [
            Course(
                title='HTML & CSS Cơ Bản',
                price=0.00,
                description='Khóa học cơ bản về HTML và CSS cho người mới bắt đầu học lập trình web',
                category_id=category_map['Lập trình Web'],
                instructor_id=None,
                status=CourseStatus.PUBLISHED,
                level=CourseLevel.BEGINNER
            ),
            Course(
                title='JavaScript Nâng Cao',
                price=299000.00,
                description='Khóa học JavaScript nâng cao với ES6+, async/await, và modern patterns',
                category_id=category_map['Lập trình Web'],
                instructor_id=None,
                status=CourseStatus.PUBLISHED,
                level=CourseLevel.ADVANCED
            ),
            Course(
                title='React.js Cơ Bản',
                price=399000.00,
                description='Học React.js từ cơ bản đến nâng cao với dự án thực tế',
                category_id=category_map['Lập trình Web'],
                instructor_id=None,
                status=CourseStatus.PUBLISHED,
                level=CourseLevel.INTERMEDIATE
            ),
            Course(
                title='Flutter Development',
                price=499000.00,
                description='Phát triển ứng dụng mobile đa nền tảng với Flutter',
                category_id=category_map['Lập trình Mobile'],
                instructor_id=None,
                status=CourseStatus.PUBLISHED,
                level=CourseLevel.INTERMEDIATE
            ),
            Course(
                title='Python Data Analysis',
                price=599000.00,
                description='Phân tích dữ liệu với Python, Pandas, và Matplotlib',
                category_id=category_map['Data Science'],
                instructor_id=None,
                status=CourseStatus.PUBLISHED,
                level=CourseLevel.BEGINNER
            ),
            Course(
                title='Machine Learning Cơ Bản',
                price=799000.00,
                description='Giới thiệu về Machine Learning với Python và Scikit-learn',
                category_id=category_map['AI & Machine Learning'],
                instructor_id=None,
                status=CourseStatus.PUBLISHED,
                level=CourseLevel.INTERMEDIATE
            )
        ]
        
        for course in courses:
            db.session.add(course)
        
        try:
            db.session.commit()
            print("Courses created successfully!")
            print("Sample data created successfully!")
        except Exception as e:
            db.session.rollback()
            print(f"Error creating courses: {e}")
    else:
        print(f"Courses already exist ({len(existing_courses)} found)")


# if __name__ == '__main__':
#     from app import app
#     with app.app_context():
#         db.create_all()
