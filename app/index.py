from flask import render_template
from app import app
from app.dao import load_categories, load_featured_courses


@app.route("/")
def index():
    categories = load_categories()
    featured_courses = load_featured_courses(limit=6)
        

    return render_template('index.html',categories=categories,featured_courses=featured_courses)
  
if __name__ == "__main__":
    app.run(debug=True)
