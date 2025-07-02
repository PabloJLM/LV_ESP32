#include <WiFi.h>
#include <PubSubClient.h>
#include <Adafruit_NeoPixel.h>

#define MAX_PINS 40
bool pinConfigured[MAX_PINS] = {false};

#define PIN_NEOPIXEL 25
#define NUM_PIXELS 3
Adafruit_NeoPixel pixels(NUM_PIXELS, PIN_NEOPIXEL, NEO_GRB + NEO_KHZ800);

// Datos que puede reemplazar LabVIEW
const char* ssid = "%%SSID%%";
const char* password = "%%PASS%%";

// MQTT
WiFiClient espClient;
PubSubClient client(espClient);

bool wifiDisponible = false;

void setup() {
  Serial.begin(115200);
  delay(1000);

  if (!String(ssid).startsWith("%%") && String(ssid).length() > 0) {
    WiFi.begin(ssid, password);

    int intentos = 0;
    while (WiFi.status() != WL_CONNECTED && intentos < 20) {
      delay(500);
      intentos++;
    }

    if (WiFi.status() == WL_CONNECTED) {
      wifiDisponible = true;
      Serial.println("WiFi conectado.");
    } else {
      Serial.println("WiFi no disponible.");
    }
  }

  pixels.begin();
  pixels.show();
  Serial.println("ESP32 listo.");
}

void loop() {
  if (Serial.available()) {
    String input = Serial.readStringUntil('\n');
    input.trim();

    if (input.length() < 2) return;

    char tipo = input.charAt(0);
    String data = input.substring(1);

    // --- Tipo 1: Digital Write (1ppv) ---
    if (tipo == '1') {
      if (data.length() != 3) return;

      int pin = data.substring(0, 2).toInt();
      int val = data.charAt(2) - '0';

      if (pin < 4 || pin >= MAX_PINS) return;

      if (!pinConfigured[pin]) {
        pinMode(pin, OUTPUT);
        pinConfigured[pin] = true;
      }

      digitalWrite(pin, val == 1 ? HIGH : LOW);
      Serial.printf("Pin %d <- %s\n", pin, val == 1 ? "HIGH" : "LOW");
    }

    // --- Tipo 2: NeoPixel (2<colorDecimal>) ---
    else if (tipo == '2') {
      unsigned long color = strtoul(data.c_str(), NULL, 10);

      uint8_t blue  = (color >> 0) & 0xFF;
      uint8_t green = (color >> 8) & 0xFF;
      uint8_t red   = (color >> 16) & 0xFF;

      for (int i = 0; i < NUM_PIXELS; i++) {
        pixels.setPixelColor(i, pixels.Color(red, green, blue));
      }
      pixels.show();

      Serial.printf("NeoPixel: R=%d G=%d B=%d\n", red, green, blue);
    }

    // --- Tipo 3: MQTT publish (3|ip|topic|msg) ---
    else if (tipo == '3') {
      if (!wifiDisponible) return;

      int pos1 = data.indexOf('|');
      int pos2 = data.indexOf('|', pos1 + 1);
      if (pos1 < 0 || pos2 < 0) return;

      String brokerIP = data.substring(0, pos1);
      String topic    = data.substring(pos1 + 1, pos2);
      String message  = data.substring(pos2 + 1);

      IPAddress mqttServer;
      if (!mqttServer.fromString(brokerIP)) return;

      client.setServer(mqttServer, 1883);

      if (!client.connected()) {
        String clientId = "ESP32_" + String(random(0xffff), HEX);
        if (!client.connect(clientId.c_str())) return;
      }

      if (client.publish(topic.c_str(), message.c_str())) {
        Serial.printf("MQTT publicado: [%s] -> %s\n", topic.c_str(), message.c_str());
      } else {
        Serial.println("ERROR: En MQTT.");
      }
    }
  }
}
