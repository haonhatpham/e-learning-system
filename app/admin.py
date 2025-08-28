from app.models import Category, Course, User, UserRole, UserStatus
from flask_admin import Admin, BaseView, expose, AdminIndexView
from flask_admin.contrib.sqla import ModelView
from flask_login import current_user, logout_user, login_user
from flask import redirect, flash, request, url_for
from datetime import datetime
from app import app, db, dao
from sqlalchemy import func

class MyAdminIndexView(AdminIndexView):
    @expose('/')
    def index(self):
        # Thống kê tổng quan
        stats = {
            'total_users': dao.count_total_users(),
            'total_courses': dao.count_total_courses(),
            'pending_instructors': dao.count_pending_instructors(),
            'total_categories': dao.count_total_categories()
        }
        return self.render('admin/index.html', stats=stats)

    def is_accessible(self):
        return current_user.is_authenticated and current_user.role == UserRole.ADMIN

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('index'))


admin = Admin(app=app, name='E-Learning Admin', template_mode='bootstrap4', index_view=MyAdminIndexView())


class AdminView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.role == UserRole.ADMIN


class CategoryView(AdminView):
    column_list = ['category_name', 'description', 'courses']  # Sửa từ 'name' thành 'category_name'
    column_searchable_list = ['category_name']  # Sửa từ 'name' thành 'category_name'
    column_filters = ['category_name']  # Sửa từ 'name' thành 'category_name'
    can_create = True
    can_edit = True
    can_delete = True


class CourseView(AdminView):
    column_list = ['id', 'title', 'instructor', 'category', 'status', 'created_at']
    column_searchable_list = ['title', 'instructor.full_name']
    column_filters = ['status', 'category', 'created_at']
    can_export = True
    page_size = 20
    can_edit = True
    can_delete = True


class UserView(AdminView):
    column_list = ['id', 'username', 'full_name', 'email', 'role', 'status', 'created_at']
    column_searchable_list = ['username', 'full_name', 'email']
    column_filters = ['role', 'status', 'created_at']
    can_export = True
    page_size = 20
    can_edit = True
    can_delete = False  # Không cho phép xóa user


class AuthenticatedView(BaseView):
    def is_accessible(self):
        # Chỉ cho phép admin truy cập các view trong khu vực admin
        return current_user.is_authenticated and current_user.role == UserRole.ADMIN

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('index'))


class LogoutView(AuthenticatedView):
    @expose('/')
    def index(self):
        logout_user()
        return redirect('/admin')


class StatsView(AuthenticatedView):
    @expose('/')
    def index(self):
        # Lọc tháng/năm từ query
        month = request.args.get('month', type=int)
        year = request.args.get('year', type=int)

        # Thống kê theo giảng viên cho admin
        instructor_stats = dao.get_admin_instructor_stats(month=month, year=year)
        labels = [s.full_name for s in instructor_stats]
        revenues = [float(s.revenue) for s in instructor_stats]
        students = [int(s.num_students) for s in instructor_stats]

        # KPI tổng quan
        total_revenue = float(sum(revenues))
        total_instructors = len(instructor_stats)
        total_students = int(sum(students))

        # Doanh thu theo tháng trong năm
        selected_year = year or datetime.now().year
        monthly = dao.get_admin_monthly_revenue(selected_year)

        return self.render(
            'admin/stats.html',
            stats=instructor_stats,
            month=month,
            year=selected_year,
            labels=labels,
            revenues=revenues,
            students=students,
            total_revenue=total_revenue,
            total_instructors=total_instructors,
            total_students=total_students,
            months=monthly['months'],
            monthly_revenues=monthly['revenues']
        )


class InstructorApprovalView(AuthenticatedView):
    @expose('/')
    def index(self):
        # Danh sách giảng viên chờ duyệt
        pending_instructors = dao.get_pending_instructors()
        return self.render('admin/instructor_approval.html', instructors=pending_instructors)

    @expose('/approve/<int:user_id>')
    def approve_instructor(self, user_id):
        # Duyệt giảng viên
        success, message = dao.approve_instructor(user_id)
        if success:
            flash(f'Đã duyệt giảng viên: {message}', 'success')
        else:
            flash(f'Lỗi khi duyệt: {message}', 'error')
        return redirect('/admin/instructor-approval')

    @expose('/reject/<int:user_id>')
    def reject_instructor(self, user_id):
        # Từ chối giảng viên
        success, message = dao.reject_instructor(user_id)
        if success:
            flash(f'Đã từ chối giảng viên: {message}', 'success')
        else:
            flash(f'Lỗi khi từ chối: {message}', 'error')
        return redirect('/admin/instructor-approval')


# Đăng ký các view
admin.add_view(CategoryView(Category, db.session, name='Danh mục'))
admin.add_view(CourseView(Course, db.session, name='Khóa học'))
admin.add_view(UserView(User, db.session, name='Người dùng'))
admin.add_view(StatsView(name='Thống kê'))
admin.add_view(InstructorApprovalView(name='Duyệt giảng viên'))
admin.add_view(LogoutView(name='Đăng xuất'))

