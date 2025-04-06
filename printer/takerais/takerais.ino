#include <WiFi.h>
#include <WiFiUdp.h>

const char* ssid = "NIS_ORBISTAN";
const char* password = "aktobe2015";

WiFiUDP udp;
const int localUdpPort = 4210;
char incomingPacket[255];

void setup() {
  Serial.begin(9600);

  WiFi.begin(ssid, password);
  Serial.print("Connecting to Wi-Fi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nConnected to Wi-Fi. IP: " + WiFi.localIP().toString());
  udp.begin(localUdpPort);
}

void loop() {
  int packetSize = udp.parsePacket();
  if (packetSize) {
    int len = udp.read(incomingPacket, 255);
    if (len > 0) {
      incomingPacket[len] = '\0';
    }
    Serial.println( String(incomingPacket));
  }
}
