from app import app, db
from app.models import User, Category, Course, UserRole, UserStatus, CourseStatus, CourseLevel
from werkzeug.security import generate_password_hash

def create_sample_data():
    """Tạo dữ liệu mẫu cho ứng dụng"""
    
    # Kiểm tra và tạo categories nếu chưa có
    existing_categories = Category.query.all()
    if not existing_categories:
        categories = [
            Category(category_name='Lập trình Web', description='Các khóa học về phát triển web, HTML, CSS, JavaScript, React, Node.js'),
            Category(category_name='Lập trình Mobile', description='Các khóa học về phát triển ứng dụng di động Android, iOS, React Native'),
            Category(category_name='Data Science', description='Các khóa học về khoa học dữ liệu, Python, Machine Learning, SQL'),
            Category(category_name='AI & Machine Learning', description='Các khóa học về trí tuệ nhân tạo, deep learning, neural networks'),
            Category(category_name='Lập trình Game', description='Các khóa học về phát triển game với Unity, Unreal Engine'),
            Category(category_name='DevOps & Cloud', description='Các khóa học về DevOps, Docker, Kubernetes, AWS, Azure'),
            Category(category_name='Cybersecurity', description='Các khóa học về bảo mật thông tin, ethical hacking'),
            Category(category_name='Digital Marketing', description='Các khóa học về marketing số, SEO, Social Media'),
        ]
        
        for category in categories:
            db.session.add(category)
        
        try:
            db.session.commit()
            print(" Categories created successfully!")
        except Exception as e:
            db.session.rollback()
            print(f" Error creating categories: {e}")
            return
    else:
        print(f" Categories already exist ({len(existing_categories)} found)")
    
    # Kiểm tra và tạo admin nếu chưa có
    existing_admin = User.query.filter_by(role=UserRole.ADMIN).first()
    if not existing_admin:
        admin = User(
            username='admin',
            full_name='Administrator',
            email='admin@elearning.com',
            password=generate_password_hash('admin123'),
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
            phone='0123456789'
        )
        db.session.add(admin)
        try:
            db.session.commit()
            print(" Admin created successfully!")
        except Exception as e:
            db.session.rollback()
            print(f" Error creating admin: {e}")
    else:
        print(" Admin already exists")
    
    # Kiểm tra và tạo instructors nếu chưa có
    existing_instructors = User.query.filter_by(role=UserRole.INSTRUCTOR).all()
    if not existing_instructors:
        instructors = [
            User(
                username='nguyenvanA',
                full_name='Nguyễn Văn A',
                email='nguyenvana@elearning.com',
                password=generate_password_hash('instructor123'),
                role=UserRole.INSTRUCTOR,
                status=UserStatus.ACTIVE,
                phone='0987654321',
                avatar_url='https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150&h=150&fit=crop&crop=face'
            ),
            User(
                username='tranthiB',
                full_name='Trần Thị B',
                email='tranthib@elearning.com',
                password=generate_password_hash('instructor123'),
                role=UserRole.INSTRUCTOR,
                status=UserStatus.ACTIVE,
                phone='0987654322',
                avatar_url='https://images.unsplash.com/photo-1494790108755-2616b612b786?w=150&h=150&fit=crop&crop=face'
            ),
            User(
                username='levanC',
                full_name='Lê Văn C',
                email='levanc@elearning.com',
                password=generate_password_hash('instructor123'),
                role=UserRole.INSTRUCTOR,
                status=UserStatus.ACTIVE,
                phone='0987654323',
                avatar_url='https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=150&h=150&fit=crop&crop=face'
            ),
            User(
                username='phamthuD',
                full_name='Phạm Thu D',
                email='phamthud@elearning.com',
                password=generate_password_hash('instructor123'),
                role=UserRole.INSTRUCTOR,
                status=UserStatus.ACTIVE,
                phone='0987654324',
                avatar_url='https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=150&h=150&fit=crop&crop=face'
            ),
            User(
                username='hoangminhE',
                full_name='Hoàng Minh E',
                email='hoangminhe@elearning.com',
                password=generate_password_hash('instructor123'),
                role=UserRole.INSTRUCTOR,
                status=UserStatus.ACTIVE,
                phone='0987654325',
                avatar_url='https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=150&h=150&fit=crop&crop=face'
            )
        ]
        
        for instructor in instructors:
            db.session.add(instructor)
        
        try:
            db.session.commit()
            print(" Instructors created successfully!")
        except Exception as e:
            db.session.rollback()
            print(f" Error creating instructors: {e}")
    else:
        print(f" Instructors already exist ({len(existing_instructors)} found)")
    
    # Kiểm tra và tạo courses nếu chưa có
    existing_courses = Course.query.all()
    if not existing_courses:
        # Lấy categories và instructors để map ID
        categories = Category.query.all()
        instructors = User.query.filter_by(role=UserRole.INSTRUCTOR).all()
        
        category_map = {cat.category_name: cat.id for cat in categories}
        instructor_map = {instructor.username: instructor.id for instructor in instructors}
        
        courses = [
            Course(
                title='HTML & CSS Cơ Bản',
                price=0.00,
                description='Khóa học cơ bản về HTML và CSS cho người mới bắt đầu học lập trình web. Học cách tạo trang web đơn giản với HTML và CSS.',
                category_id=category_map['Lập trình Web'],
                instructor_id=instructor_map['nguyenvanA'],
                status=CourseStatus.PUBLISHED,
                level=CourseLevel.BEGINNER,
                cover_image='https://images.unsplash.com/photo-1461749280684-dccba630e2f6?w=400&h=250&fit=crop'
            ),
            Course(
                title='JavaScript Nâng Cao',
                price=299000.00,
                description='Khóa học JavaScript nâng cao với ES6+, async/await, và modern patterns. Học cách viết code JavaScript hiện đại và hiệu quả.',
                category_id=category_map['Lập trình Web'],
                instructor_id=instructor_map['tranthiB'],
                status=CourseStatus.PUBLISHED,
                level=CourseLevel.ADVANCED,
                cover_image='https://images.unsplash.com/photo-1579468118864-1b9ea3c0db4a?w=400&h=250&fit=crop'
            ),
            Course(
                title='React.js Cơ Bản',
                price=399000.00,
                description='Học React.js từ cơ bản đến nâng cao với dự án thực tế. Xây dựng ứng dụng web hiện đại với React.',
                category_id=category_map['Lập trình Web'],
                instructor_id=instructor_map['levanC'],
                status=CourseStatus.PUBLISHED,
                level=CourseLevel.INTERMEDIATE,
                cover_image='https://images.unsplash.com/photo-1633356122544-f134324a6cee?w=400&h=250&fit=crop'
            ),
            Course(
                title='Flutter Development',
                price=499000.00,
                description='Phát triển ứng dụng mobile đa nền tảng với Flutter. Tạo ứng dụng iOS và Android với một codebase duy nhất.',
                category_id=category_map['Lập trình Mobile'],
                instructor_id=instructor_map['phamthuD'],
                status=CourseStatus.PUBLISHED,
                level=CourseLevel.INTERMEDIATE,
                cover_image='https://images.unsplash.com/photo-1512941937669-90a1b58e7e9c?w=400&h=250&fit=crop'
            ),
            Course(
                title='Python Data Analysis',
                price=599000.00,
                description='Phân tích dữ liệu với Python, Pandas, và Matplotlib. Học cách xử lý và phân tích dữ liệu thực tế.',
                category_id=category_map['Data Science'],
                instructor_id=instructor_map['hoangminhE'],
                status=CourseStatus.PUBLISHED,
                level=CourseLevel.BEGINNER,
                cover_image='https://images.unsplash.com/photo-1526379095098-d400fd0bf935?w=400&h=250&fit=crop'
            ),
            Course(
                title='Machine Learning Cơ Bản',
                price=799000.00,
                description='Giới thiệu về Machine Learning với Python và Scikit-learn. Học các thuật toán ML cơ bản và ứng dụng thực tế.',
                category_id=category_map['AI & Machine Learning'],
                instructor_id=instructor_map['nguyenvanA'],
                status=CourseStatus.PUBLISHED,
                level=CourseLevel.INTERMEDIATE,
                cover_image='https://images.unsplash.com/photo-1677442136019-21780ecad995?w=400&h=250&fit=crop'
            ),
            Course(
                title='Unity Game Development',
                price=699000.00,
                description='Phát triển game 2D và 3D với Unity. Học cách tạo game từ ý tưởng đến sản phẩm hoàn chỉnh.',
                category_id=category_map['Lập trình Game'],
                instructor_id=instructor_map['tranthiB'],
                status=CourseStatus.PUBLISHED,
                level=CourseLevel.INTERMEDIATE,
                cover_image='https://images.unsplash.com/photo-1511512578047-dfb367046420?w=400&h=250&fit=crop'
            ),
            Course(
                title='Docker & Kubernetes',
                price=899000.00,
                description='Học Docker và Kubernetes để containerize và orchestrate ứng dụng. DevOps skills cần thiết cho developer hiện đại.',
                category_id=category_map['DevOps & Cloud'],
                instructor_id=instructor_map['levanC'],
                status=CourseStatus.PUBLISHED,
                level=CourseLevel.ADVANCED,
                cover_image='https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=400&h=250&fit=crop'
            ),
            Course(
                title='Ethical Hacking',
                price=999000.00,
                description='Khóa học về bảo mật thông tin và ethical hacking. Học cách bảo vệ hệ thống khỏi các cuộc tấn công.',
                category_id=category_map['Cybersecurity'],
                instructor_id=instructor_map['phamthuD'],
                status=CourseStatus.PUBLISHED,
                level=CourseLevel.ADVANCED,
                cover_image='https://images.unsplash.com/photo-1550751827-4bd374c3f58b?w=400&h=250&fit=crop'
            ),
            Course(
                title='Digital Marketing Mastery',
                price=399000.00,
                description='Thành thạo digital marketing với SEO, Social Media, và Content Marketing. Xây dựng chiến lược marketing hiệu quả.',
                category_id=category_map['Digital Marketing'],
                instructor_id=instructor_map['hoangminhE'],
                status=CourseStatus.PUBLISHED,
                level=CourseLevel.BEGINNER,
                cover_image='https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=400&h=250&fit=crop'
            )
        ]
        
        for course in courses:
            db.session.add(course)
        
        try:
            db.session.commit()
            print(" Courses created successfully!")
        except Exception as e:
            db.session.rollback()
            print(f" Error creating courses: {e}")
    else:
        print(f" Courses already exist ({len(existing_courses)} found)")
    
    print(" Sample data creation completed!")
    print(" Summary:")
    print(f"   - Categories: {len(Category.query.all())}")
    print(f"   - Instructors: {len(User.query.filter_by(role=UserRole.INSTRUCTOR).all())}")
    print(f"   - Courses: {len(Course.query.all())}")
    print(f"   - Admin: {User.query.filter_by(role=UserRole.ADMIN).count()}")
    
    print(" Login Credentials:")
    print("   - Admin: admin@elearning.com / admin123")
    print("   - Instructors: nguyenvana@elearning.com / instructor123")
    print("   - Instructors: tranthib@elearning.com / instructor123")
    print("   - Instructors: levanc@elearning.com / instructor123")
    print("   - Instructors: phamthud@elearning.com / instructor123")
    print("   - Instructors: hoangminhe@elearning.com / instructor123")

def main():
    with app.app_context():
        try:
            # Tạo tất cả bảng
            db.create_all()
            print(" Database tables created successfully!")
            
            # Tạo dữ liệu mẫu
            create_sample_data()
            
        except Exception as e:
            print(f" Error creating database: {e}")

if __name__ == "__main__":
    main()
