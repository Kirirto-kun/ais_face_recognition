from PIL import Image
from io import BytesIO
import sqlite3


def get_user_by_iin(iin):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT surname, name, patronymic, phone, class, curator, photo 
        FROM users WHERE iin=?
    """, (iin,))
    result = cursor.fetchone()
    conn.close()
    return result

# Пример использования:
user_data = get_user_by_iin("080424552629")
if user_data:
    surname, name, patronymic, phone, class_, curator, photo_blob = user_data
    if photo_blob:
        try:
            photo = Image.open(BytesIO(photo_blob))
            photo.show()  # Для проверки — откроется окно с фотографией
        except Exception as e:
            print("Ошибка при загрузке фото:", e)
