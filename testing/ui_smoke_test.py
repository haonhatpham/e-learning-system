import os
import sys
import time
from typing import List, Tuple

import requests
from bs4 import BeautifulSoup


BASE_URL = os.environ.get("BASE_URL", "http://localhost:5000")
DEFAULT_TIMEOUT_SECONDS = float(os.environ.get("UI_TEST_TIMEOUT", "10"))


def build_url(path: str) -> str:
    if not path.startswith("/"):
        path = f"/{path}"
    return f"{BASE_URL.rstrip('/')}{path}"


def get_page(path: str) -> Tuple[int, float, str]:
    """Fetch a page and return (status_code, elapsed_seconds, text)."""
    url = build_url(path)
    start = time.perf_counter()
    response = requests.get(url, timeout=DEFAULT_TIMEOUT_SECONDS)
    elapsed = time.perf_counter() - start
    return response.status_code, elapsed, response.text


def assert_status_ok(status: int, path: str, errors: List[str]) -> None:
    if status != 200:
        errors.append(f"{path}: kỳ vọng HTTP 200 nhưng nhận {status}")


def assert_elapsed_lt(elapsed: float, threshold: float, path: str, errors: List[str]) -> None:
    if elapsed > threshold:
        ms = int(elapsed * 1000)
        errors.append(f"{path}: thời gian tải {ms}ms > {int(threshold*1000)}ms")


def assert_title_contains(html: str, expected: str, path: str, errors: List[str]) -> None:
    soup = BeautifulSoup(html, "html.parser")
    title = (soup.title.string or "").strip() if soup.title else ""
    if expected not in title:
        errors.append(f"{path}: tiêu đề không chứa '{expected}'. Thực tế: '{title}'")


def assert_text_exists(html: str, expected: str, path: str, errors: List[str]) -> None:
    if expected not in html:
        errors.append(f"{path}: không tìm thấy đoạn văn bản '{expected}' trong HTML")


def test_homepage(errors: List[str]) -> None:
    path = "/"
    status, elapsed, html = get_page(path)
    assert_status_ok(status, path, errors)
    assert_elapsed_lt(elapsed, 2.0, path, errors)
    assert_title_contains(html, "E-Learning System", path, errors)
    # Một số nội dung quan trọng trên trang chủ
    assert_text_exists(html, "Tìm kiếm khóa học", path, errors)
    assert_text_exists(html, "Khóa học phổ biến", path, errors)


def test_register_page(errors: List[str]) -> None:
    path = "/register"
    status, elapsed, html = get_page(path)
    # Có thể yêu cầu đăng nhập/redirect; chấp nhận 200 hoặc 302
    if status not in (200, 302):
        errors.append(f"{path}: kỳ vọng HTTP 200 hoặc 302 nhưng nhận {status}")
    else:
        if status == 200:
            assert_title_contains(html, "Đăng ký", path, errors)


def test_login_page(errors: List[str]) -> None:
    path = "/login"
    status, elapsed, html = get_page(path)
    if status not in (200, 302):
        errors.append(f"{path}: kỳ vọng HTTP 200 hoặc 302 nhưng nhận {status}")
    else:
        if status == 200:
            assert_title_contains(html, "Đăng nhập", path, errors)


def test_course_search(errors: List[str]) -> None:
    path = "/search?q=python"
    status, elapsed, html = get_page(path)
    if status not in (200, 302):
        errors.append(f"{path}: kỳ vọng HTTP 200 hoặc 302 nhưng nhận {status}")
    else:
        if status == 200:
            # Trang tìm kiếm nên chứa từ khóa trên trang
            assert_text_exists(html, "python", path, errors)


def run_all_tests() -> int:
    tests = [
        ("Trang chủ", test_homepage),
        ("Trang đăng ký", test_register_page),
        ("Trang đăng nhập", test_login_page),
        ("Tìm kiếm khóa học", test_course_search),
    ]

    errors: List[str] = []
    for name, fn in tests:
        try:
            fn(errors)
        except Exception as exc:
            errors.append(f"{name}: lỗi ngoại lệ {exc}")

    if errors:
        print("KIỂM THỬ UI KHÔNG THÀNH CÔNG:\n- " + "\n- ".join(errors))
        return 1

    print("KIỂM THỬ UI THÀNH CÔNG: tất cả kiểm tra đều đạt.")
    return 0


if __name__ == "__main__":
    sys.exit(run_all_tests())


