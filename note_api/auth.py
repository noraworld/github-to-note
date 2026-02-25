import time

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def get_note_cookies(email, password):
    """noteにログインしてCookieを取得"""
    driver = webdriver.Chrome()

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
        return {cookie["name"]: cookie["value"] for cookie in cookies}

    except (TimeoutException, NoSuchElementException) as exc:
        print(f"ログイン処理で要素取得に失敗しました: {exc}")
        return {}
    finally:
        driver.quit()
