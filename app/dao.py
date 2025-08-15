from app import db
from app.models import Category, Course
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
