#!/usr/bin/env python3
"""
Скрипт для скачивания HTML страниц из Яндекс Хендбука по C++.

Использует Selenium для обхода защиты и поддерживает ручное прохождение капчи.

Использование:
    uv run python -m src.data_processing.download_handbook_cpp
    
    # Или напрямую
    uv run python src/data_processing/download_handbook_cpp.py
"""

import random
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.data_processing import RAW_DATA_DIR

# Директория для сохранения HTML
OUTPUT_DIR = RAW_DATA_DIR / "cpp"

# URL хендбука
HANDBOOK_URL = "https://education.yandex.ru/handbook/cpp"


def create_driver() -> webdriver.Chrome:
    """Создаёт Chrome WebDriver с настройками для обхода защиты."""
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    # chrome_options.add_argument("--headless")  # раскомментируй для headless режима

    driver = webdriver.Chrome(options=chrome_options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver


def wait_for_captcha(driver: webdriver.Chrome) -> None:
    """Ждёт пока пользователь пройдёт капчу, если она появилась."""
    while "SmartCaptcha" in driver.page_source or "Я не робот" in driver.page_source:
        print("  ⚠️  Обнаружена капча! Пройди её вручную...")
        time.sleep(3)


def get_chapter_urls(driver: webdriver.Chrome, handbook_url: str) -> list[str]:
    """Собирает ссылки на все главы из оглавления."""
    print(f"📖 Загрузка оглавления: {handbook_url}")
    driver.get(handbook_url)
    time.sleep(3)

    wait_for_captcha(driver)

    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "ul.styles_book-contents__a6F2_"))
        )
    except Exception as e:
        print(f"❌ Не удалось загрузить оглавление: {e}")
        return []

    chapter_links = driver.find_elements(By.CSS_SELECTOR, "ul.styles_book-contents__a6F2_ a")
    chapter_urls = []

    for link in chapter_links:
        href = link.get_attribute("href")
        if href and "contest.yandex.ru" not in href:
            chapter_urls.append(href)

    return chapter_urls


def download_chapters(driver: webdriver.Chrome, chapter_urls: list[str]) -> None:
    """Скачивает HTML всех глав."""
    print(f"\n📄 Найдено {len(chapter_urls)} глав")
    print("=" * 60)

    for i, url in enumerate(chapter_urls):
        try:
            print(f"\n[{i + 1}/{len(chapter_urls)}] {url}")

            driver.get(url)
            time.sleep(random.uniform(2.0, 4.0))

            wait_for_captcha(driver)

            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "main")))

            page_html = driver.page_source

            safe_filename = f"{i + 1:02d}_{url.split('/')[-1]}.html"
            file_path = OUTPUT_DIR / safe_filename

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(page_html)

            print(f"  ✓ Сохранено: {file_path.name}")

        except Exception as e:
            print(f"  ❌ Ошибка: {e}")


def main():
    """Основная функция скачивания."""
    # Создаём директорию если не существует
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("🚀 Яндекс Хендбук C++ Downloader")
    print("=" * 60)
    print(f"📂 Директория: {OUTPUT_DIR}")

    driver = create_driver()

    try:
        chapter_urls = get_chapter_urls(driver, HANDBOOK_URL)

        if not chapter_urls:
            print("❌ Не удалось получить список глав")
            return

        download_chapters(driver, chapter_urls)

        print("\n" + "=" * 60)
        print(f"✅ Готово! Все файлы сохранены в: {OUTPUT_DIR}")
        print("=" * 60)

    finally:
        driver.quit()


if __name__ == "__main__":
    main()

