import sqlite3
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from datetime import datetime
import threading
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Optional, Callable, Any, Tuple

# --- Настройки ---
DB_PATH = "printer/users.db"
OUTPUT_IMAGE = "printer/output.jpg"
DPI = 300
WIDTH_CM, HEIGHT_CM = 10, 15  # Формат 10*15
WIDTH_PX = int(WIDTH_CM * DPI / 2.54)
HEIGHT_PX = int(HEIGHT_CM * DPI / 2.54)

# Пути к шрифтам
BOLD_FONT_PATH = "printer/arialbd.ttf"
REGULAR_FONT_PATH = "printer/arial.ttf"

# --- Получение пользователя из БД ---
def get_user_by_iin(iin):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT surname, name, patronymic, phone, class, curator, photo 
            FROM users WHERE iin=?
        """, (iin,))
        result = cursor.fetchone()
        conn.close()
        return result
    except Exception as e:
        print(f"Ошибка при доступе к базе данных: {e}")
        return None

# Асинхронная версия получения пользователя
def get_user_by_iin_async(iin, callback=None):
    def _task():
        try:
            result = get_user_by_iin(iin)
            if callback:
                callback(result)
            return result
        except Exception as e:
            print(f"Ошибка при получении данных пользователя: {e}")
            if callback:
                callback(None)
            return None
    
    thread = threading.Thread(target=_task)
    thread.daemon = True
    thread.start()
    return thread

# --- Генерация изображения ---
def generate_image(user_data, output_path):
    image = Image.new("RGB", (WIDTH_PX, HEIGHT_PX), "white")
    draw = ImageDraw.Draw(image)

    try:
        bold_font = ImageFont.truetype(BOLD_FONT_PATH, 48)
        regular_font = ImageFont.truetype(REGULAR_FONT_PATH, 36)
        header_font = ImageFont.truetype(BOLD_FONT_PATH, 60)
        small_font = ImageFont.truetype(REGULAR_FONT_PATH, 28)
    except:
        bold_font = regular_font = header_font = small_font = ImageFont.load_default()

    # Заголовок
    header_text = "Сертификат об опоздании"
    header_width = draw.textlength(header_text, font=header_font)
    header_x = (WIDTH_PX - header_width) // 2
    draw.text((header_x, 30), header_text, fill="black", font=header_font)

    surname, name, patronymic, phone, class_, curator, photo_blob = user_data

    # Фото (справа)
    if photo_blob:
        user_photo = Image.open(BytesIO(photo_blob)).convert("RGB")
        max_photo_width = WIDTH_PX 
        max_photo_height = HEIGHT_PX 
        user_photo.thumbnail((max_photo_width, max_photo_height), Image.LANCZOS)
        photo_x = WIDTH_PX - user_photo.width - 20
        photo_y = 100  # Фото сразу под заголовком
        image.paste(user_photo, (photo_x, photo_y))

    # Текстовые данные
    left_margin = 50
    current_y = 150
    line_gap = 10

    def draw_field(label, value, extra_blank_lines=0):
        nonlocal current_y
        header = f"{label.upper()}:"
        draw.text((left_margin, current_y), header, fill="black", font=bold_font)
        bbox = draw.textbbox((left_margin, current_y), header, font=bold_font)
        current_y += (bbox[3] - bbox[1]) + line_gap

        draw.text((left_margin, current_y), str(value), fill="black", font=regular_font)
        bbox = draw.textbbox((left_margin, current_y), str(value), font=regular_font)
        current_y += (bbox[3] - bbox[1]) + line_gap

        for _ in range(extra_blank_lines):
            current_y += (bbox[3] - bbox[1]) + line_gap

    draw_field("Фамилия", surname)
    draw_field("Имя", name)
    draw_field("Отчество", patronymic)
    draw_field("Телефон", phone, extra_blank_lines=1)
    draw_field("Класс", class_)
    draw_field("Куратор", curator)

    # Доп. строка "распечатано..."
    printed_line = f"распечатано {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    draw.text((left_margin, current_y), printed_line, fill="black", font=small_font)

    # Штамп в левом нижнем углу
    try:
        stamp = Image.open("printer/stampbad.png").convert("RGBA")
        max_stamp_size = (300, 300)
        stamp.thumbnail(max_stamp_size, Image.LANCZOS)
        stamp_x = 400  # Увеличенный отступ слева
        stamp_y = HEIGHT_PX - stamp.height - 1200
        image.paste(stamp, (stamp_x, stamp_y), stamp)
    except Exception as e:
        print(f"Ошибка при вставке штампа: {e}")

    # Сохранение
    image.save(output_path)
    print(f"Файл сохранён: {output_path}")

# Асинхронная версия генерации изображения
def generate_image_async(user_data, output_path, callback=None):
    def _task():
        try:
            generate_image(user_data, output_path)
            if callback:
                callback(True, output_path)
            return True
        except Exception as e:
            print(f"Ошибка при генерации изображения: {e}")
            if callback:
                callback(False, str(e))
            return False
    
    thread = threading.Thread(target=_task)
    thread.daemon = True
    thread.start()
    return thread

# --- Вызов ---
def main_1(IIN):
    user = get_user_by_iin(IIN)
    if user:
        generate_image(user, OUTPUT_IMAGE)
    else:
        print("Пользователь не найден.")

# Асинхронная версия основной функции
def main_1_async(IIN, output_path=OUTPUT_IMAGE, callback=None):
    """
    Асинхронно генерирует сертификат об опоздании.
    
    Args:
        IIN: Идентификационный номер пользователя
        output_path: Путь для сохранения выходного изображения
        callback: Функция обратного вызова, которая будет вызвана по завершении
                 с параметрами (success, result_or_error)
    
    Returns:
        ThreadPoolExecutor для отслеживания выполнения
    """
    print(f"Запуск асинхронной генерации сертификата для IIN: {IIN}")
    # Create a new executor for each call to prevent resource issues
    executor = ThreadPoolExecutor(max_workers=1)
    
    def process_complete(success, result):
        if callback:
            callback(success, result)
        # Make sure to shutdown the executor to free resources
        executor.shutdown(wait=False)
    
    def on_user_received(user):
        if user:
            generate_image_async(user, output_path, 
                                lambda success, result: process_complete(success, result))
        else:
            process_complete(False, "Пользователь не найден")
    
    try:
        future = executor.submit(get_user_by_iin, IIN)
        future.add_done_callback(lambda f: on_user_received(f.result()))
    except Exception as e:
        print(f"Ошибка при запуске асинхронной задачи: {e}")
        if callback:
            callback(False, str(e))
        executor.shutdown(wait=False)
    
    return executor

# Пример использования асинхронной функции - только при прямом запуске файла
if __name__ == "__main__":
    def on_complete(success, result):
        if success:
            print(f"Сертификат успешно создан: {result}")
        else:
            print(f"Ошибка при создании сертификата: {result}")
    
    test_executor = main_1_async("070517551794", callback=on_complete)
    # Этот код запустится только при прямом выполнении файла, а не при импорте
    print("Тест асинхронной функции запущен...")
    # Дождемся завершения для демонстрационных целей
    import time
    time.sleep(3)
    print("Завершение тестового примера")
