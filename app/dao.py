from app import db
from app.models import Category, Course, User # Import thêm User
from sqlalchemy import desc, func
from typing import List, Dict


def load_categories():
    categories = Category.query.all()
    return categories

def load_featured_courses(limit=6):
    featured_courses = (
        Course.query
        .filter_by(status='published')
        .order_by(desc(Course.created_at))
        .limit(limit)
        .all()
    )
    return featured_courses

# Hàm tìm kiếm khóa học theo từ khóa
# Có thể tìm theo:
#   - Tên khóa học (Course.title)
#   - Tên giảng viên (User.full_name)
def search_courses(keyword: str):
    if not keyword:
        return []

    # Join sang bảng User để tìm theo tên giảng viên
    return Course.query.join(User, Course.instructor_id == User.id, isouter=True) \
        .filter(
            (Course.title.ilike(f"%{keyword}%")) |
            (User.full_name.ilike(f"%{keyword}%"))
        ).all()

# Hàm lấy chi tiết khóa học theo ID
def get_course_by_id(course_id: int):
    return Course.query.get(course_id)