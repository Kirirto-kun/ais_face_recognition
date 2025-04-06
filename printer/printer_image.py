import win32print
import win32ui
from PIL import Image, ImageWin
import threading
from typing import Optional, Callable

def print_image(image_path):
    # Открытие изображения
    image = Image.open(image_path)
    
    # Получение принтера по умолчанию
    printer_name = win32print.GetDefaultPrinter()
    
    # Создание объекта для печати
    hprinter = win32print.OpenPrinter(printer_name)
    devmode = win32print.GetPrinter(hprinter, 2)["pDevMode"]
    
    # Открываем диалог печати
    printer_dc = win32ui.CreateDC()
    printer_dc.CreatePrinterDC(printer_name)
    printer_dc.StartDoc("Printing image")
    printer_dc.StartPage()

    # Преобразуем изображение в формат, который можно напечатать
    bmp = ImageWin.Dib(image)

    # Получаем размеры страницы
    width, height = image.size
    printer_dc.SetMapMode(1)  # Устанавливаем нормальный режим отображения

    # Печатаем изображение
    bmp.draw(printer_dc.GetHandleOutput(), (1430, 0, 1430+int(width*2.5//1), int(height*2.5//1)))
    print(2500, 0, 2500+int(width*2.5//1), int(height*2.5//1))
    # Завершаем печать
    printer_dc.EndPage()
    printer_dc.EndDoc()
    printer_dc.DeleteDC()

# Асинхронная версия функции печати через отдельный поток
def print_image_async(image_path, callback: Optional[Callable[[bool, str], None]] = None):
    """
    Печатает изображение в отдельном потоке, чтобы не блокировать основной поток.
    
    Args:
        image_path: Путь к файлу изображения
        callback: Функция обратного вызова, которая будет вызвана по завершении
                 с параметрами (success, result_or_error)
    
    Returns:
        threading.Thread: Объект потока выполнения
    """
    def _task():
        try:
            print_image(image_path)
            if callback:
                callback(True, image_path)
            return True
        except Exception as e:
            error_msg = f"Ошибка при печати изображения {image_path}: {str(e)}"
            print(error_msg)
            if callback:
                callback(False, error_msg)
            return False
    
    thread = threading.Thread(target=_task)
    thread.daemon = True  # Поток завершится когда завершится основная программа
    thread.start()
    return thread

# Код запускается только при прямом выполнении файла
if __name__ == "__main__":
    # Путь к изображению
    image_path = "printer/output.jpg"
    
    # Пример использования асинхронной функции
    def on_print_complete(success, result):
        if success:
            print(f"Изображение {result} успешно отправлено на печать")
        else:
            print(f"Ошибка: {result}")
    
    print_thread = print_image_async(image_path, callback=on_print_complete)
    print("Печать запущена в фоновом режиме. Основной поток продолжает работу...")
