import os
import sys
from typing import List, Tuple

import requests


BASE_URL = os.environ.get("BASE_URL", "http://localhost:5000").rstrip("/")
TIMEOUT = int(os.environ.get("FUNC_TEST_TIMEOUT", "10"))


def url(path: str) -> str:
    if not path.startswith("/"):
        path = "/" + path
    return f"{BASE_URL}{path}"


def get(path: str, allow_redirects: bool = False) -> requests.Response:
    return requests.get(url(path), timeout=TIMEOUT, allow_redirects=allow_redirects)


def post(path: str, data: dict, allow_redirects: bool = False) -> requests.Response:
    return requests.post(url(path), data=data, timeout=TIMEOUT, allow_redirects=allow_redirects)


def test_home() -> Tuple[bool, str]:
    resp = get("/")
    ok = resp.status_code == 200
    return ok, f"GET / => {resp.status_code}"


def test_search() -> Tuple[bool, str]:
    resp = get("/search?q=test")
    ok = resp.status_code == 200
    return ok, f"GET /search?q=test => {resp.status_code}"


def test_login_invalid() -> Tuple[bool, str]:
    resp = post("/login", {"username": "__not_exist__", "password": "bad"}, allow_redirects=True)
    ok = resp.status_code == 200 and ("Đăng nhập" in resp.text or "Tên đăng nhập" in resp.text)
    return ok, f"POST /login (invalid) => {resp.status_code}"


def test_register_missing_fields() -> Tuple[bool, str]:
    # Gửi form thiếu để nhận 200 và hiển thị lỗi hợp lệ (không cần DB)
    data = {
        "full_name": "",
        "username": "",
        "email": "",
        "password": "123",
        "confirm_password": "456",
        "role": "student"
    }
    resp = post("/register", data, allow_redirects=True)
    ok = resp.status_code == 200
    return ok, f"POST /register (invalid form) => {resp.status_code}"


def test_progress_requires_login() -> Tuple[bool, str]:
    resp = get("/progress", allow_redirects=False)
    ok = resp.status_code in (302, 401) and "/login" in resp.headers.get("Location", "")
    return ok, f"GET /progress (anon) => {resp.status_code}, Location={resp.headers.get('Location', '')}"


def test_checkout_requires_login() -> Tuple[bool, str]:
    resp = get("/checkout/1", allow_redirects=False)
    ok = resp.status_code in (302, 401) and "/login" in resp.headers.get("Location", "")
    return ok, f"GET /checkout/1 (anon) => {resp.status_code}, Location={resp.headers.get('Location', '')}"


def test_course_detail_tolerant() -> Tuple[bool, str]:
    # Chấp nhận 200 nếu có course #1, hoặc 404 nếu không tồn tại
    resp = get("/course/1")
    ok = resp.status_code in (200, 404)
    return ok, f"GET /course/1 => {resp.status_code}"


def run() -> int:
    tests = [
        ("home", test_home),
        ("search", test_search),
        ("login_invalid", test_login_invalid),
        ("register_missing_fields", test_register_missing_fields),
        ("progress_requires_login", test_progress_requires_login),
        ("checkout_requires_login", test_checkout_requires_login),
        ("course_detail_tolerant", test_course_detail_tolerant),
    ]

    failures: List[str] = []
    for name, fn in tests:
        try:
            ok, msg = fn()
            status = "OK" if ok else "FAIL"
            print(f"[{status}] {msg}")
            if not ok:
                failures.append(f"{name}: {msg}")
        except Exception as exc:
            failures.append(f"{name}: exception {exc}")
            print(f"[EXC] {name}: {exc}")

    if failures:
        print("\nCHƯA ĐẠT:")
        for f in failures:
            print(f"- {f}")
        return 1

    print("\nTẤT CẢ KIỂM THỬ CHỨC NĂNG ĐỀU ĐẠT.")
    return 0


if __name__ == "__main__":
    sys.exit(run())


