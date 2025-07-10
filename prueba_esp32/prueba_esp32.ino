#include <Adafruit_NeoPixel.h>
#include <WiFi.h>
#include <PubSubClient.h>

#define NUM_PIXELS 3
#define PIN_NEOPIXEL 25

Adafruit_NeoPixel pixels(NUM_PIXELS, PIN_NEOPIXEL, NEO_GRB + NEO_KHZ800);

WiFiClient espClient;
PubSubClient client(espClient);

const char* ssid = "CLARO1_8383C6";
const char* password = "021S4WVSGC";

String listen_topic = "";
bool mqtt_subscribed = false;

void callback(char* topic, byte* payload, unsigned int length) {
  String msg = "";
  for (unsigned int i = 0; i < length; i++) {
    msg += (char)payload[i];
  }
  Serial.print(topic);
  Serial.print(":");
  Serial.println(msg);
}

void setup() {
  Serial.begin(115200);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
  }
  client.setCallback(callback);
  pixels.begin();
  pixels.show();
}

void loop() {
  static String line = "";

  if (Serial.available()) {
    char peekChar = Serial.peek();
    if (peekChar == 'A' || peekChar == 'B') {
      while (Serial.available()) {
        char c = Serial.read();
        if (c == '\n') break;
        line += c;
      }

      char tipo = line.charAt(0);
      line.remove(0, 1);
      line.trim();
      int sep = line.indexOf(' ');
      if (sep > 0) {
        String ipStr = line.substring(0, sep);
        String second = line.substring(sep + 1);

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

        if (tipo == 'A') { //A<ip> <topic> <msg>
          int sep2 = second.indexOf(' ');
          if (sep2 > 0) {
            String topic = second.substring(0, sep2);
            String msg = second.substring(sep2 + 1);
            bool ok = client.publish(topic.c_str(), msg.c_str());
            Serial.write(ok ? 'A' : 'X');
          } else {
            Serial.write('X');
          }
        } else if (tipo == 'B') {//B<ip> <topic>
          listen_topic = second;
          mqtt_subscribed = client.subscribe(listen_topic.c_str());
          Serial.write(mqtt_subscribed ? 'A' : 'X');
        }
      } else {
        Serial.write('X');
      }

      line = "";
      return;
    }
  }

  if (mqtt_subscribed && client.connected()) {
    client.loop();
  }

  if (Serial.available() > 0) {
    byte instruccion = Serial.read();

    switch (instruccion) {
      case 0x01: {
        while (Serial.available() < 2);
        byte pin = Serial.read();
        byte val = Serial.read();
        pinMode(pin, OUTPUT);
        digitalWrite(pin, val == 0 ? LOW : HIGH);
        Serial.write('A');
        break;
      }

      case 0x02: {
        while (Serial.available() < 2);
        byte pin = Serial.read();
        byte dummy = Serial.read();
        pinMode(pin, INPUT);
        byte lectura = digitalRead(pin);
        Serial.write(lectura ? '1' : '0');
        break;
      }

      case 0x03: {
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

      case 0x04: {
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
            case 0x05: {
        while (Serial.available() < 1);
        byte pin = Serial.read();
        int val = analogRead(pin);  // lectura ADC (0–4095)
        Serial.write(highByte(val));  // Enviamos MSB
        Serial.write(lowByte(val));   // Enviamos LSB
        break;
      }

      case 0xF0: {
        Serial.write('A');
        break;
      }

      case 0xF1: {
        Serial.write(WiFi.status() == WL_CONNECTED ? 'A' : 'X');
        break;
      }
      case 0xF2: {  
        if (mqtt_subscribed && client.connected()) {
          client.unsubscribe(listen_topic.c_str());
          mqtt_subscribed = false;
          listen_topic = "";
          Serial.write('A');
        } else {
          Serial.write('X');
        }
        break;
}
      default:
        Serial.write('X');
        break;
    }
  }
}
