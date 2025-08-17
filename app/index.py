from flask import render_template, request # Import thêm request
from app import app
from app.dao import load_categories, load_featured_courses, search_courses, get_course_by_id # thêm cho tìm kiếm khóa học


@app.route("/")
def index():
    categories = load_categories()
    featured_courses = load_featured_courses(limit=6)
        

    return render_template('index.html',categories=categories,featured_courses=featured_courses)
# Trang tìm kiếm khóa học
@app.route("/search")
def search():
    q = request.args.get("q", "")
    courses = search_courses(q)
    return render_template("search.html", courses=courses, q=q)

# Trang chi tiết khóa học
@app.route("/course/<int:course_id>")
def course_detail(course_id):
    course = get_course_by_id(course_id)
    if not course:
        return "Khóa học không tồn tại", 404
    return render_template("course_detail.html", course=course)

if __name__ == "__main__":
    app.run(debug=True)
