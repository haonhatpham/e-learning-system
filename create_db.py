from app import app, db
from app.models import create_sample_data

def main():
    with app.app_context():
        try:
            # Tạo tất cả bảng
            db.create_all()
            print("tạo thành công bảng database!")
            
            # Tạo dữ liệu mẫu
            create_sample_data()
            print("Đã tạo thành công dữ liệu mẫu!")

            
        except Exception as e:
            print(f"Lỗi khi tạo database: {e}")

if __name__ == "__main__":
    main()
