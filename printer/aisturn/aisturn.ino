#include <WiFi.h>
#include <SPI.h>
#include <MFRC522.h>
#include <WiFiUdp.h>

#define SS_PIN 5
#define RST_PIN 0
#define PIEZO_PIN 15  // Пин для пьезо-сирены

const char* ssid = "NIS_ORBISTAN";
const char* password = "aktobe2015";

const char* udpAddress = "10.69.151.107";  // IP второй ESP32
const int udpPort = 4210;

WiFiUDP udp;
MFRC522 rfid(SS_PIN, RST_PIN);

struct CardData {
  byte uid[7];
  byte uidLength;
  String iin;
  int status;
};

CardData cards[] = {
  {{0xA1, 0x1B, 0xBD, 0xCF}, 4, "080424552629", 0},
  {{0x04, 0x50, 0x1A, 0xDA, 0x7D, 0x62, 0x80}, 7, "070517551794", 0}
};

void setup() {
  Serial.begin(9600);
  SPI.begin();
  rfid.PCD_Init();
  
  pinMode(PIEZO_PIN, OUTPUT);  // Установка пина для пьезо на выход
  
  WiFi.begin(ssid, password);
  Serial.print("Connecting to Wi-Fi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
   tone(PIEZO_PIN, 750, 500);
  Serial.println("\nConnected to Wi-Fi");
}

void loop() {
  if (!rfid.PICC_IsNewCardPresent() || !rfid.PICC_ReadCardSerial()) return;

  int matchedIndex = -1;

  for (int i = 0; i < sizeof(cards) / sizeof(cards[0]); i++) {
    if (rfid.uid.size != cards[i].uidLength) continue;

    bool match = true;
    for (int j = 0; j < cards[i].uidLength; j++) {
      if (rfid.uid.uidByte[j] != cards[i].uid[j]) {
        match = false;
        break;
      }
    }

    if (match) {
      matchedIndex = i;
      break;
    }
  }

  if (matchedIndex >= 0) {
    int status = cards[matchedIndex].status;
    String message = String(status) + "," + cards[matchedIndex].iin;
    udp.beginPacket(udpAddress, udpPort);
    udp.print(message);
    udp.endPacket();
    Serial.println("Sent: " + message);

    soundAlarm(status);  // Звуковой сигнал

    cards[matchedIndex].status = 1 - cards[matchedIndex].status;
  } else {
    udp.beginPacket(udpAddress, udpPort);
    udp.print("-1,-1");
    udp.endPacket();
    Serial.println("Sent: -1,-1");

    soundAlarm(-1);  // Звуковой сигнал для неправильной карты
  }

  rfid.PICC_HaltA();
  rfid.PCD_StopCrypto1();

  delay(1000);  // Пауза после считывания
}

// Функция для воспроизведения звукового сигнала в зависимости от состояния
void soundAlarm(int status) {
  if (status == 0) {
    // Вход (0) - один короткий тон (500 мс)
    tone(PIEZO_PIN, 1200, 500);
  } 
  else if (status == 1) {
    // Выход (1) - два коротких тона (500 мс)
    tone(PIEZO_PIN, 1000, 500);
    delay(500);
    tone(PIEZO_PIN, 1000, 500);
  } 
  else {
    // Неправильная карта (-1) - один длинный тон (1 секунда)
    tone(PIEZO_PIN, 500, 1000);
  }
}
