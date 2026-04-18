import os
import time

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def _parse_cookie_header(cookie_header):
    cookies = {}
    if not cookie_header:
        return cookies
    for part in str(cookie_header).split(";"):
        token = part.strip()
        if not token or "=" not in token:
            continue
        key, value = token.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key:
            cookies[key] = value
    return cookies


def _get_cookie_fallback_from_env():
    cookies = {}

    cookie_header = os.getenv("NOTE_COOKIE") or os.getenv("NOTE_COOKIES")
    cookies.update(_parse_cookie_header(cookie_header))

    note_session_v5 = os.getenv("NOTE_SESSION_V5")
    xsrf_token = os.getenv("XSRF_TOKEN")
    csrf_token = os.getenv("CSRF_TOKEN")

    if note_session_v5:
        cookies["_note_session_v5"] = note_session_v5
    if xsrf_token:
        cookies["XSRF-TOKEN"] = xsrf_token
    if csrf_token:
        cookies["csrf_token"] = csrf_token

    return cookies


def _has_auth_cookie(cookies):
    return bool(cookies.get("_note_session_v5"))


def _is_truthy_env(name):
    value = os.getenv(name)
    if value is None:
        return False
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def _is_verbose_enabled():
    return _is_truthy_env("NOTE_VERBOSE")


def _debug_log_user_agent(driver, label):
    """verbose 有効時のみ、現在の navigator.userAgent を表示する。"""
    if not _is_verbose_enabled():
        return
    try:
        current_user_agent = driver.execute_script("return navigator.userAgent")
        print(f"[auth debug] navigator.userAgent ({label}): {current_user_agent}")
    except Exception as exc:
        print(
            f"[auth debug] navigator.userAgent ({label}) の取得に失敗しました。"
            f"処理は継続します: {exc}"
        )


def _mask_headless_user_agent(driver):
    """Best-effortで HeadlessChrome を Chrome に置き換える。失敗しても継続する。"""
    try:
        current_user_agent = driver.execute_script("return navigator.userAgent")
        if not current_user_agent or "HeadlessChrome/" not in current_user_agent:
            _debug_log_user_agent(driver, "without override")
            return

        masked_user_agent = current_user_agent.replace("HeadlessChrome/", "Chrome/")
        driver.execute_cdp_cmd(
            "Network.setUserAgentOverride",
            {
                "userAgent": masked_user_agent,
                "acceptLanguage": "ja-JP",
                "platform": "MacIntel",
            },
        )
        _debug_log_user_agent(driver, "after override")
    except Exception as exc:
        print(
            "HeadlessChrome を Chrome に置き換える User-Agent 補助処理に失敗しました。"
            f"処理は継続します: {exc}"
        )


def _build_driver():
    options = webdriver.ChromeOptions()
    if not _is_truthy_env("NOTE_SHOW_BROWSER"):
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1280,720")
    options.add_argument("--lang=ja-JP")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    chrome_binary = os.getenv("CHROME_BINARY")
    if chrome_binary:
        options.binary_location = chrome_binary

    chromedriver_path = os.getenv("CHROMEDRIVER_PATH")
    if chromedriver_path:
        service = webdriver.ChromeService(executable_path=chromedriver_path)
        return webdriver.Chrome(service=service, options=options)

    return webdriver.Chrome(options=options)


def get_note_cookies(email, password):
    """noteにログインしてCookieを取得"""
    if _is_truthy_env("NOTE_SHOW_BROWSER"):
        print("NOTE_SHOW_BROWSER=1 のためヘッドレスを無効化して起動します。")
    driver = _build_driver()
    _mask_headless_user_agent(driver)
    login_error = None

    try:
        driver.get("https://note.com/login")
        wait = WebDriverWait(driver, 20)

        def find_first(selectors):
            for by, value in selectors:
                elements = driver.find_elements(by, value)
                if elements:
                    return elements[0]
            return None

        email_login_entry = find_first(
            [
                (By.XPATH, "//a[contains(., 'メールアドレス') and contains(., 'ログイン')]"),
                (By.XPATH, "//button[contains(., 'メールアドレス') and contains(., 'ログイン')]"),
                (By.XPATH, "//a[contains(., 'メールアドレスでログイン')]"),
                (By.XPATH, "//button[contains(., 'メールアドレスでログイン')]"),
            ]
        )
        if email_login_entry:
            wait.until(EC.element_to_be_clickable(email_login_entry)).click()

        wait.until(
            lambda d: find_first(
                [
                    (By.NAME, "email"),
                    (By.NAME, "login"),
                    (By.CSS_SELECTOR, "input[type='email']"),
                    (By.CSS_SELECTOR, "input[autocomplete='username']"),
                    (By.XPATH, "//input[contains(@placeholder, 'メール')]"),
                ]
            )
            is not None
        )
        email_input = find_first(
            [
                (By.NAME, "email"),
                (By.NAME, "login"),
                (By.CSS_SELECTOR, "input[type='email']"),
                (By.CSS_SELECTOR, "input[autocomplete='username']"),
                (By.XPATH, "//input[contains(@placeholder, 'メール')]"),
            ]
        )
        if not email_input:
            raise TimeoutException("メールアドレス入力欄を検出できませんでした。")

        password_input = find_first(
            [
                (By.NAME, "password"),
                (By.CSS_SELECTOR, "input[type='password']"),
                (By.CSS_SELECTOR, "input[autocomplete='current-password']"),
                (By.XPATH, "//input[contains(@placeholder, 'パスワード')]"),
            ]
        )
        if not password_input:
            raise TimeoutException("パスワード入力欄を検出できませんでした。")

        email_input.clear()
        email_input.send_keys(email)
        password_input.clear()
        password_input.send_keys(password)

        login_button = find_first(
            [
                (By.XPATH, "//button[@type='submit']"),
                (By.XPATH, "//button[contains(., 'ログイン')]"),
                (By.XPATH, "//button[contains(., 'Sign in')]"),
                (By.XPATH, "//input[@type='submit']"),
            ]
        )
        if not login_button:
            raise TimeoutException("ログインボタンを検出できませんでした。")
        wait.until(EC.element_to_be_clickable(login_button)).click()

        wait.until(lambda d: "note.com/login" not in d.current_url)
        time.sleep(2)

        cookies = driver.get_cookies()
        cookie_map = {cookie["name"]: cookie["value"] for cookie in cookies}
        if _has_auth_cookie(cookie_map):
            return cookie_map
        login_error = "ログイン後Cookieに _note_session_v5 が含まれていません。"

    except (TimeoutException, NoSuchElementException) as exc:
        login_error = f"ログイン処理で要素取得に失敗しました: {exc}"
        print(login_error)
        print(f"current_url={driver.current_url}")
        print(f"title={driver.title}")
        try:
            screenshot_path = "/tmp/note-login-failed.png"
            driver.save_screenshot(screenshot_path)
            print(f"screenshot={screenshot_path}")
        except Exception:
            pass
    finally:
        driver.quit()

    fallback_cookies = _get_cookie_fallback_from_env()
    if _has_auth_cookie(fallback_cookies):
        print("ID/パスワードログインに失敗。環境変数のセッション情報で継続します。")
        return fallback_cookies

    print("セッション情報のフォールバックも見つからないためログイン失敗です。")
    return {}
