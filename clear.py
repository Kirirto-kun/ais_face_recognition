import sqlite3

# Подключение к базе данных
conn = sqlite3.connect('information.db')
cursor = conn.cursor()

# Очистка данных из таблицы Attendance
cursor.execute("DELETE FROM Attendance")

# Сохранение изменений и закрытие соединения
conn.commit()
conn.close()

print("Данные успешно удалены из таблицы Attendance.")
