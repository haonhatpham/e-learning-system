from app.models import *
from app import db, app
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView

admin = Admin(app=app, name="Quản trị eCourse", template_mode="bootstrap4")
admin.add_view(ModelView(Category,db.session))
admin.add_view(ModelView(Course,db.session))

