from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user
from app.models import UserRole, UserStatus

def require_instructor():
    """Kiểm tra giảng viên đã đăng nhập và được duyệt"""
    if not current_user.is_authenticated:
        return redirect(url_for('login_user_route'))
    if current_user.role != UserRole.INSTRUCTOR or current_user.status != UserStatus.ACTIVE:
        flash('Chỉ giảng viên đã được duyệt mới có thể truy cập.', 'error')
        return redirect(url_for('index'))
    return None

def require_admin():
    """Kiểm tra admin đã đăng nhập"""
    if not current_user.is_authenticated or current_user.role != UserRole.ADMIN:
        flash('Chỉ admin mới có thể truy cập.', 'error')
        return redirect(url_for('index'))
    return None

def require_student():
    """Kiểm tra học viên đã đăng nhập"""
    if not current_user.is_authenticated or current_user.role != UserRole.STUDENT:
        flash('Chỉ học viên mới có thể truy cập.', 'error')
        return redirect(url_for('index'))
    return None
