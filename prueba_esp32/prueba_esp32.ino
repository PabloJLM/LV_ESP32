#include <Adafruit_NeoPixel.h>
#include <WiFi.h>
#include <PubSubClient.h>

#define NUM_PIXELS 3
#define PIN_NEOPIXEL 25

Adafruit_NeoPixel pixels(NUM_PIXELS, PIN_NEOPIXEL, NEO_GRB + NEO_KHZ800);

WiFiClient espClient;
PubSubClient client(espClient);

const char* ssid = "%%SSID%%";
const char* password = "%%PASS%%";

void setup() {
  Serial.begin(115200);
  

  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    //Serial.print(".");
  }

  //Serial.println("\n✅ Conectado a WiFi!");
  //Serial.print("📡 IP local: ");
  //Serial.println(WiFi.localIP());

  pixels.begin();
  pixels.show();
}

void loop() {
  static String line = "";

  if (Serial.available()) {
    char peekChar = Serial.peek();
    if (peekChar == 'A') {
      // Leer línea completa
      while (Serial.available()) {
        char c = Serial.read();
        if (c == '\n') break;
        line += c;
      }

      if (line.startsWith("A")) {
        line.remove(0, 1);  // quitar 'A'
        line.trim();
        int ipEnd = line.indexOf(' ');
        int topicEnd = line.indexOf(' ', ipEnd + 1);

        if (ipEnd > 0 && topicEnd > ipEnd) {
          String ipStr = line.substring(0, ipEnd);
          String topic = line.substring(ipEnd + 1, topicEnd);
          String message = line.substring(topicEnd + 1);

          IPAddress brokerIP;
          if (!brokerIP.fromString(ipStr)) {
            Serial.write('X');
            line = "";
            return;
          }

          client.setServer(brokerIP, 1883);
          if (!client.connected()) {
            if (!client.connect("esp32_client")) {
              Serial.write('X');
              line = "";
              return;
            }
          }

          bool ok = client.publish(topic.c_str(), message.c_str());
          Serial.write(ok ? 'A' : 'X');
        } else {
          Serial.write('X');  
        }
      }

      line = "";
      return;
    }
  }

  // PROTOCOLO NORMAL EN BYTES:
  if (Serial.available() > 0) {
    byte instruccion = Serial.read();

    switch (instruccion) {
      case 0x01: {  // digitalWrite
        while (Serial.available() < 2);
        byte pin = Serial.read();
        byte val = Serial.read();
        pinMode(pin, OUTPUT);
        digitalWrite(pin, val == 0 ? LOW : HIGH);
        Serial.write('A');
        break;
      }

      case 0x02: {  // digitalRead
        while (Serial.available() < 2);
        byte pin = Serial.read();
        byte dummy = Serial.read();
        pinMode(pin, INPUT);
        byte lectura = digitalRead(pin);
        Serial.write(lectura ? '1' : '0');
        break;
      }

      case 0x03: {  // NeoPixel triple
        while (Serial.available() < 3);
        byte r = Serial.read();
        byte g = Serial.read();
        byte b = Serial.read();
        for (int i = 0; i < NUM_PIXELS; i++) {
          pixels.setPixelColor(i, pixels.Color(r, g, b));
        }
        pixels.show();
        Serial.write('A');
        break;
      }

      case 0x04: {  // NeoPixel individual
        while (Serial.available() < 4);
        byte neo = Serial.read();
        byte r = Serial.read();
        byte g = Serial.read();
        byte b = Serial.read();
        if (neo < NUM_PIXELS) {
          pixels.setPixelColor(neo, pixels.Color(r, g, b));
          pixels.show();
          Serial.write('A');
        } else {
          Serial.write('X');
        }
        break;
      }

      case 0xF0: {  // Ping
        Serial.write('A');
        break;
      }

      case 0xF1: {  // WiFi status
        Serial.write(WiFi.status() == WL_CONNECTED ? 'A' : 'X');
        break;
      }

      default:
        Serial.write('X');
        break;
    }
  }
}
