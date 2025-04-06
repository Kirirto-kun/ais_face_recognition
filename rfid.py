import serial
import time
import sqlite3
import datetime
import os

from printer.createopbad import main_1, main_1_async
# Import the async printing function
from printer.printer_image import print_image_async
# RFID to person mapping
RFID_TO_NAME = {
    "070708551158": "JAFAR",
    "080424552629": "AZIZ",
    "070517551794": "MAKSIM"
}

def initialize_database():
    """Initialize the database if it doesn't exist"""
    db_path = os.path.join(os.path.dirname(__file__), 'information.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create only the Attendance table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Attendance (
        NAME TEXT,
        Time TEXT,
        Date TEXT
    )
    ''')
    
    conn.commit()
    conn.close()

def log_rfid_to_database(status, rfid_id):
    """Log RFID readings to the database"""
    # Get name based on RFID ID
    name = RFID_TO_NAME.get(rfid_id, "UNKNOWN")
    dictionary = {
        "MAKSIM": "070517551794",
        "JAFAR": "070708551158",
        "KEREY": "071004553794",
        "AZIZ": "080424552629"
    }
    # Use the asynchronous version to run in a separate thread
    # This won't block the camera or face recognition processing
    def on_certificate_complete(success, result):
        if success:
            print(f"Certificate for {name} created successfully")
            # After certificate is created successfully, print it asynchronously
            def on_print_complete(print_success, print_result):
                if print_success:
                    print(f"Certificate for {name} printed successfully")
                else:
                    print(f"Failed to print certificate for {name}: {print_result}")
            
            # Start printing in a separate thread
            output_image_path = "printer/output.jpg"  # Use the path from createopbad.py
            print_image_async(output_image_path, callback=on_print_complete)
        else:
            print(f"Failed to create certificate for {name}: {result}")
    
    # Start the certificate creation in a separate thread
    main_1_async(dictionary[name], callback=on_certificate_complete)
    # Get current time and date in the required format
    now = datetime.datetime.now()
    dtString = now.strftime('%H:%M')
    today_date = str(datetime.date.today())
    
    # Connect to database
    db_path = os.path.join(os.path.dirname(__file__), 'information.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Make sure the Attendance table exists
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Attendance (
        NAME TEXT,
        Time TEXT,
        Date TEXT
    )
    ''')
    
    # No longer logging to rfid_logs table
    
    # Check if the record already exists in Attendance
    cursor.execute("SELECT * FROM Attendance WHERE NAME=? AND Date=?", (name, today_date))
    existing_record = cursor.fetchone()
    
    # Insert only if record doesn't exist
    if name != "UNKNOWN":
        cursor.execute("INSERT INTO Attendance (NAME, Time, Date) VALUES (?, ?, ?)", 
                     (name, dtString, today_date))
    
    # Get the data for return
    cursor.execute("SELECT NAME, Time, Date FROM Attendance WHERE NAME=? AND Date=?", 
                 (name, today_date))
    record = cursor.fetchone()
    
    conn.commit()
    conn.close()
    
    return name

def read_rfid_from_esp32(port='COM7', baudrate=9600, timeout=1):
    """
    Read RFID data from an ESP32 connected to a serial port.
    
    Args:
        port (str): Serial port name (default: COM7)
        baudrate (int): Serial baudrate (default: 9600)
        timeout (int): Serial timeout in seconds (default: 1)
    
    Returns:
        None
    """
    try:
        # Initialize the database
        initialize_database()
        
        # Connect to the serial port
        ser = serial.Serial(port, baudrate, timeout=timeout)
        print(f"Connected to {port} at {baudrate} baud")
        
        while True:
            # Read a line from the serial port
            if ser.in_waiting:
                try:
                    # Use 'replace' to handle invalid UTF-8 characters
                    data = ser.readline().decode('utf-8', errors='replace').strip()
                except Exception as e:
                    print(f"Error reading from serial port: {e}")
                    continue
                
                # Skip empty lines or lines with just whitespace
                if not data or data.isspace():
                    continue
                    
                print(f"Raw data: '{data}'")
                
                try:
                    # Parse the data (format: "0,070517551794" or "1,080424552629")
                    # Check if data contains a comma
                    if ',' in data:
                        status, rfid_id = data.split(',')
                        status = int(status)
                        
                        # Log to database and get name
                        name = log_rfid_to_database(status, rfid_id)
                        
                        print(f"Status: {status}, RFID ID: {rfid_id}, Name: {name}")
                    else:
                        print(f"Skipping invalid data format: '{data}'")
                        
                except ValueError as e:
                    print(f"Error parsing data: '{data}', error: {e}")
            
            # Small delay to prevent CPU overuse
            time.sleep(0.1)
            
    except serial.SerialException as e:
        print(f"Error opening serial port {port}: {e}")
    except KeyboardInterrupt:
        print("Reading stopped by user")
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print("Serial port closed")

if __name__ == "__main__":
    read_rfid_from_esp32()
