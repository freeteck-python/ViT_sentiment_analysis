import subprocess
import sys

# Автоматический контроль зависимостей перед запуском
try:
    import pandas as pd
    import undetected_chromedriver as uc
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
except ModuleNotFoundError:
    print("Обнаружены отсутствующие библиотеки. Запускаем автоустановку...")
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "pandas", "openpyxl", "undetected-chromedriver", "selenium",
         "setuptools"])
    print("Все библиотеки успешно установлены! Перезапустите скрипт.")
    sys.exit()

import time
import random

def get_driver():
    options = uc.ChromeOptions()
    # Отключаем картинки для экономии трафика и ускорения загрузки страниц
    options.add_argument('--blink-settings=imagesEnabled=false')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument("--disable-blink-features=AutomationControlled")

    # Явно указываем 148-ю версию Chrome (на данный момент - май 2026)
    driver = uc.Chrome(options=options, version_main=148)
    driver.set_window_size(random.randint(1200, 1400), random.randint(800, 900))
    return driver

def parse_yandex_all_reviews(driver, company_id, address):
    print(f"\n>>> Обработка: {address} (ID: {company_id})")
    url = f"https://yandex.ru/maps/org/vkusno_i_tochka/{company_id}/reviews/"
    results = []

    try:
        driver.get(url)
        wait = WebDriverWait(driver, 15)

        # Динамические селекторы для поиска контейнера отзывов
        selectors = [
            "div.business-reviews-card-view__review-list",
            "div[class*='review-list']",
            "div[class*='reviews-view']"
        ]

        scrollable_div = None
        active_selector = None

        for sel in selectors:
            try:
                scrollable_div = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, sel)))
                active_selector = sel
                break
            except:
                continue

        if scrollable_div is None:
            print("Контейнер отзывов не найден. Пропустили. (Возможно, капча)")
            return []

        # Глубокий скроллинг
        max_scrolls = 60
        print("Идет глубокое адаптивное сканирование ленты: ", end="", flush=True)

        last_count = 0
        no_change_attempts = 0

        for scroll_idx in range(max_scrolls):
            try:
                current_div = driver.find_element(By.CSS_SELECTOR, active_selector)

                # Имитируем поведение человека: скроллим то вниз, то чуть-чуть вверх («встряска» для триггера загрузки)
                if scroll_idx % 5 == 0 and scroll_idx > 0:
                    # Слегка приподнимаем скролл вверх на 300 пикселей
                    driver.execute_script("arguments.scrollTo(0, arguments.scrollHeight - 300);", current_div)
                    time.sleep(random.uniform(0.5, 1.0))

                # Основной скролл до упора вниз
                driver.execute_script("arguments.scrollTo(0, arguments.scrollHeight);", current_div)
                print("[DOWN]", end="", flush=True)

                # Каждые 7 скроллов делаем длинную «человеческую» паузу для прогрузки тяжелых скриптов Яндекса
                if scroll_idx % 7 == 0:
                    time.sleep(random.uniform(3.5, 5.0))
                else:
                    time.sleep(random.uniform(1.8, 2.8))

                # Проверяем динамику подгрузки отзывов
                current_items_count = len(
                    driver.find_elements(By.CSS_SELECTOR, "div.business-review-view, div[class*='review-view']"))
                if current_items_count == last_count:
                    no_change_attempts += 1
                    if no_change_attempts >= 6:  # Если 6 скроллов подряд новых отзывов нет — останавливаем скролл
                        print("[STOP]", end="", flush=True)
                        break
                else:
                    last_count = current_items_count
                    no_change_attempts = 0

            except Exception:
                print(".", end="", flush=True)
                time.sleep(2)

        print("\nПрокрутка завершена. Извлечение и фильтрация текстовых данных...")
        time.sleep(2)

        # Сбор карточек отзывов
        items = driver.find_elements(By.CSS_SELECTOR, "div.business-review-view, div[class*='review-view']")
        seen_reviews = set()

        for item in items:
            try:
                if not item.is_displayed():
                    continue

                # 1. Извлечение автора
                author = item.find_element(By.CSS_SELECTOR,
                                           "[class*='author-name'] span, [class*='author-name']").text.strip()

                # 2. Извлечение даты и автоподстановка 2026 года
                raw_date = item.find_element(By.CSS_SELECTOR, "[class*='date']").text.strip()
                if not any(char.isdigit() and len(raw_date.split()[-1]) == 4 for char in raw_date.split()):
                    date_val = f"{raw_date} 2026"
                else:
                    date_val = raw_date

                # 3. Клик на кнопку раскрытия полного текста "еще"
                try:
                    expanded_btn = item.find_element(By.CSS_SELECTOR, "[class*='expand'], [class*='more']")
                    if expanded_btn.is_displayed():
                        driver.execute_script("arguments.click();", expanded_btn)
                        time.sleep(0.1)
                except:
                    pass

                # 4. Сбор и чистка текста отзыва
                try:
                    text = item.find_element(By.CSS_SELECTOR, "[class*='__body']").text
                    if text.endswith("ещё"):
                        text = text[:-3]
                    text = text.replace('\n', ' ').strip()
                except:
                    text = ""

                # 5. Сбор рейтинга
                try:
                    rating_el = item.find_element(By.CSS_SELECTOR,
                                                  "[class*='rating'] span[aria-label], [class*='stars'] span[aria-label]")
                    rating_text = rating_el.get_attribute("aria-label")
                    rating = int(''.join(filter(str.isdigit, rating_text)))
                except:
                    rating = 0

                # Исключаем дубли по комбинации уникального ключа
                review_key = f"{author}_{date_val}_{text[:20]}"
                if review_key in seen_reviews:
                    continue

                # Нам нужны только содержательные текстовые отзывы
                if text != "":
                    seen_reviews.add(review_key)
                    results.append({
                        'ID_ресторана': company_id,
                        'Адрес_ресторана': address,
                        'Дата': date_val,
                        'Рейтинг': rating,
                        'Автор': author,
                        'Текст': text
                    })
            except Exception:
                continue

    except Exception as e:
        print(f"Системный сбой при обработке адреса: {e}")

    print(f" Результат: успешно сохранено {len(results)} отзывов.")
    return results

if __name__ == "__main__":
    EXCEL_FILE = "restaurants.xlsx"
    try:
        input_df = pd.read_excel(EXCEL_FILE)
        input_df = input_df.dropna(subset=['ID_ресторана'])
        restaurants = input_df.to_dict('records')
        print(f"Файл {EXCEL_FILE} успешно прочитан. Очередь на сбор: {len(restaurants)} ресторанов.")
    except Exception as e:
        print(f"Ошибка загрузки Excel: {e}")
        exit()

    driver = get_driver()
    all_reviews = []

    try:
        # Цикл пройдется по всем ресторанам без ограничений
        for index, rest in enumerate(restaurants):
            r_id = str(int(rest['ID_ресторана']))
            r_addr = rest['Адрес_ресторана']

            data = parse_yandex_all_reviews(driver, r_id, r_addr)
            all_reviews.extend(data)

            # Страховка (Бэкап): перезаписываем файл прогресса после каждого ресторана.
            # Если скрипт прервется, данные не потеряются!
            if all_reviews:
                pd.DataFrame(all_reviews).to_csv("progress_backup.csv", index=False, encoding='utf-8-sig')

            print(f"Общий прогресс: {index + 1}/{len(restaurants)} ресторанов пройдено.")

            # Длинная пауза между филиалами, чтобы снизить вероятность капчи
            time.sleep(random.uniform(5, 10))

    finally:
        driver.quit()

    # Финальное сохранение базы данных
    if all_reviews:
        final_df = pd.DataFrame(all_reviews)
        final_df.to_csv("yandex_reviews_final_3.csv", index=False, encoding='utf-8-sig')
        print(
            f"\nСБОР ЗАВЕРШЕН! Создана полная база: 'yandex_reviews_final_3.csv'. Всего строк: {len(final_df)}")
    else:
        print("\nДанные не были собраны. Проверьте систему на наличие жестких блокировок.")