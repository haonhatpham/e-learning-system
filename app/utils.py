from flask import render_template
from flask_mail import Message
from app import mail
from threading import Thread
from flask import current_app

def send_async_email(app, msg):
    """Gửi email bất đồng bộ"""
    with app.app_context():
        mail.send(msg)

def send_email(subject, recipients, template, **kwargs):
    """Gửi email với template"""
    try:
        msg = Message(subject, recipients=recipients)
        msg.html = render_template(f'emails/{template}.html', **kwargs)
        
        # Gửi email bất đồng bộ để không block main thread
        Thread(target=send_async_email, args=(current_app._get_current_object(), msg)).start()
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

def send_welcome_email(user):
    """Gửi email chào mừng khi đăng ký thành công"""
    try:
        # Chỉ gửi email cho sinh viên, giảng viên sẽ nhận email sau khi được duyệt
        if user.role.value == 'student':
            subject = f"Chào mừng {user.full_name} đến với E-Learning System!"
            
            send_email(
                subject=subject,
                recipients=[user.email],
                template='welcome_student',
                user=user,
                role_name='Học viên'
            )
            return True
        else:
            # Giảng viên không gửi email chào mừng, sẽ gửi sau khi duyệt
            print(f"Không gửi email chào mừng cho giảng viên {user.full_name} - đang chờ duyệt")
            return True
            
    except Exception as e:
        print(f"Error sending welcome email: {e}")
        return False

def send_registration_confirmation(user):
    """Gửi email xác nhận đăng ký"""
    try:
        subject = "Xác nhận đăng ký tài khoản - E-Learning System"
        
        send_email(
            subject=subject,
            recipients=[user.email],
            template='registration_confirmation',
            user=user
        )
        
        return True
    except Exception as e:
        print(f"Error sending registration confirmation: {e}")
        return False


def send_approval_email(user):
    """Gửi email thông báo giảng viên được duyệt"""
    try:
        subject = f"🎉 Chúc mừng! Tài khoản giảng viên của {user.full_name} đã được duyệt"
        
        send_email(
            subject=subject,
            recipients=[user.email],
            template='instructor_approved',
            user=user
        )
        
        return True
    except Exception as e:
        print(f"Error sending approval email: {e}")
        return False


def send_rejection_email(user):
    """Gửi email thông báo giảng viên bị từ chối"""
    try:
        subject = f"Thông báo về đơn đăng ký giảng viên của {user.full_name}"
        
        send_email(
            subject=subject,
            recipients=[user.email],
            template='instructor_rejected',
            user=user
        )
        
        return True
    except Exception as e:
        print(f"Error sending rejection email: {e}")
        return False
