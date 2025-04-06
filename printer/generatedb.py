def read_photo_as_blob(photo_path):
    with open(photo_path, "rb") as file:
        blob_data = file.read()
    return blob_data
import sqlite3

def insert_user(iin, surname, name, patronymic, phone, class_, curator, photo_path):
    photo_blob = read_photo_as_blob(photo_path)
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO users (iin, surname, name, patronymic, phone, class, curator, photo)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (iin, surname, name, patronymic, phone, class_, curator, photo_blob))
    conn.commit()
    conn.close()

# Пример вызова:
# Добавление Габитова Абдулазиза Габитовича
insert_user(
    "080424552629",
    "ГАБИТОВ",
    "АБДУЛАЗИЗ",
    "ГАБИТОВИЧ",
    "+77755124030",
    "11Н",
    "Самал Талгатовна",
    "Azi.png"  # путь к файлу с фотографией ученика
)

# Добавление Мажитова Джафаара Армановича
insert_user(
    "070708551158",
    "МАЖИТОВ",
    "ДЖАФАР",
    "АРМАНОВИЧ",
    "+77712900331",
    "11D",
    "Ботагоз Бауыржановна",
    "Jaf.png"  # путь к файлу с фотографией ученика
)

# Добавление Бердышева Керея Нуржанулы
insert_user(
    "071004553794",
    "БЕРДЫШЕВ",
    "КЕРЕЙ",
    "НУРЖАНУЛЫ",
    "+77767625577",
    "11Н",
    "Татьяна Викторовна",
    "Kir.png"  # путь к файлу с фотографией ученика
)

