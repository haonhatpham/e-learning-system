// Spinner functionality
window.addEventListener('load', function() {
    const spinner = document.getElementById('spinner');
    if (spinner) {
        spinner.classList.remove('show');
    }
});

// WOW.js initialization
if (typeof WOW !== 'undefined') {
    new WOW().init();
}

// nút lên đầu trang
window.addEventListener('scroll', function() {
    const backToTop = document.querySelector('.back-to-top');
    if (backToTop) {
        if (window.pageYOffset > 100) {
            backToTop.style.display = 'block';
        } else {
            backToTop.style.display = 'none';
        }
    }
});

// Auto-hide alerts
document.addEventListener('DOMContentLoaded', function() {
    // Auto-hide Bootstrap alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            if (alert && alert.parentNode) {
                alert.style.transition = 'opacity 0.5s ease-out';
                alert.style.opacity = '0';
                setTimeout(function() {
                    if (alert && alert.parentNode) {
                        alert.remove();
                    }
                }, 500);
            }
        }, 5000);
    });
});

// Simple Toastr functions
function showSuccessToast(message, title = 'Thành công!') {
    toastr.success(message, title);
}

function showErrorToast(message, title = 'Lỗi!') {
    toastr.error(message, title);
}

function showWarningToast(message, title = 'Cảnh báo!') {
    toastr.warning(message, title);
}

function showInfoToast(message, title = 'Thông tin!') {
    toastr.info(message, title);
}

// Make functions globally available
window.showToast = {
    success: showSuccessToast,
    error: showErrorToast,
    warning: showWarningToast,
    info: showInfoToast
};

// Make toast functions globally available for auth.js
window.showErrorToast = showErrorToast;
window.showSuccessToast = showSuccessToast;
window.showWarningToast = showWarningToast;
window.showInfoToast = showInfoToast;

/*=============== XEM MẬT KHẨU ===============*/
document.addEventListener('DOMContentLoaded', function() {
    // Xử lý tất cả các trường mật khẩu
    const passwordToggles = document.querySelectorAll('[id*="showPasswordToggle"]');
    
    passwordToggles.forEach(function(toggle) {
        const input = toggle.previousElementSibling;
        const icon = toggle.querySelector('i');
        
        if (input && icon) {
            toggle.addEventListener('click', function() {
                if (input.type === 'password') {
                    input.type = 'text';
                    icon.className = 'bi bi-eye-slash';
                } else {
                    input.type = 'password';
                    icon.className = 'bi bi-eye';
                }
            });
        }
    });
});

/*=============== XỬ LÝ FLASH MESSAGES ===============*/
document.addEventListener('DOMContentLoaded', function() {
    // Đợi một chút để đảm bảo Toastr đã load
    setTimeout(function() {
        // Lấy tất cả flash messages từ Flask
        const flashMessages = document.querySelectorAll('#flash-container .alert');
        
        if (flashMessages.length > 0) {
            console.log('Found flash messages:', flashMessages.length);
            
            flashMessages.forEach(function(message, index) {
                const messageText = message.textContent.trim();
                const messageType = getMessageType(message);
                
                console.log(`Message ${index}:`, messageText, 'Type:', messageType);
                
                // Ẩn message gốc ngay lập tức
                if (message && message.parentNode) {
                    message.style.display = 'none';
                }
                
                // Hiển thị toast tương ứng
                if (messageType === 'success') {
                    showSuccessToast(messageText);
                } else if (messageType === 'error' || messageType === 'danger') {
                    showErrorToast(messageText);
                } else if (messageType === 'warning') {
                    showWarningToast(messageText);
                } else if (messageType === 'info') {
                    showInfoToast(messageText);
                }
            });
        } else {
            console.log('No flash messages found');
        }
    }, 100);
});

// Hàm xác định loại message
function getMessageType(messageElement) {
    const classes = messageElement.className;
    
    if (classes.includes('alert-success') || classes.includes('success')) {
        return 'success';
    } else if (classes.includes('alert-danger') || classes.includes('error') || classes.includes('danger')) {
        return 'error';
    } else if (classes.includes('alert-warning') || classes.includes('warning')) {
        return 'warning';
    } else if (classes.includes('alert-info') || classes.includes('info')) {
        return 'info';
    }
    
    return 'info'; // Mặc định
}
