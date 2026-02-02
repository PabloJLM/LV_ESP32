#include <Adafruit_NeoPixel.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <Arduino.h>
#include <ESP32Servo.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>



Servo myServo;
#define NUM_PIXELS 3
#define PIN_NEOPIXEL 25//se asume el pin de neopixel por la board Galiot

Adafruit_NeoPixel pixels(NUM_PIXELS, PIN_NEOPIXEL, NEO_GRB + NEO_KHZ800);

WiFiClient espClient;
PubSubClient client(espClient);

const char* ssid = "%%SSID%%";
const char* password = "%%PASS%%";

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
  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < 5000) {// intebta conectar sino funciona deja el modo offline
    delay(500);
  }

  if (WiFi.status() == WL_CONNECTED) {
    client.setCallback(callback);
  } 

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
          line = "";
          return;
        }

        client.setServer(brokerIP, 1883);
        if (!client.connected()) {
          if (!client.connect("esp32_client")) {
            line = "";
            return;
          }
        }

        if (tipo == 'A') { // A<ip> <topic> <msg>
          int sep2 = second.indexOf(' ');
          if (sep2 > 0) {
            String topic = second.substring(0, sep2);
            String msg = second.substring(sep2 + 1);
            bool ok = client.publish(topic.c_str(), msg.c_str());
            Serial.write(ok ? 'A' : 'X');
          }
        } else if (tipo == 'B') { // B<ip> <topic>
          listen_topic = second;
          mqtt_subscribed = client.subscribe(listen_topic.c_str());
        }
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

      case 0x06: {
        while (Serial.available() < 2);
        byte pin = Serial.read();
        byte val = Serial.read();
        if (pin == 25 || pin == 26) {
          dacWrite(pin, val);
          Serial.write('A');
        } else {
          Serial.write('X');
        }
        break;
      }

      case 0x07: {
        while (Serial.available() < 2);
        byte pin = Serial.read();
        byte duty = Serial.read(); // 0–255

        ledcAttachChannel(pin, 1000, 8,0);
        ledcWrite(pin, duty);
        Serial.write('A');
        break;
      }

      case 0x08: {
        while (Serial.available() < 2);
        byte pin = Serial.read();
        byte angulo = Serial.read(); // 0–210 grados
        if (angulo > 210) angulo = 210;
        // Adjuntar el servo con rango extendido si aún no está
        if (myServo.attached()) {
            myServo.detach();  // liberar el pin actual
        }
        myServo.attach(pin, 500, 2400);

        myServo.write(angulo);
        //Serial.write('A');
        break;
      }
      
      case 0x09: {
        // Esperamos dirección, columna y fila
        while (Serial.available() < 3);

        byte direccion = Serial.read();
        byte col = Serial.read();
        byte fila = Serial.read();

        // Leemos el resto del texto hasta salto de línea
        String mensaje = "";
        while (Serial.available()) {
          char c = Serial.read();
          if (c == '\n') break;
          mensaje += c;
        }

        // Creamos el objeto LCD con esa dirección (dinámico)
        LiquidCrystal_I2C lcd(direccion, 16, 2);
        lcd.init();
        lcd.backlight();

        // Limpiamos y escribimos en la posición indicada
        if (fila > 1) fila = 1;       // seguridad
        if (col > 15) col = 15;       // seguridad

        lcd.setCursor(col, fila);
        lcd.print(mensaje);

        Serial.write('A'); // confirmación
        break;
      }





      case 0xF0: {
        Serial.write('A');
        break;
      }

      case 0xF1: {
        Serial.write(WiFi.status() == WL_CONNECTED ? 'A' : 'X');//conectado o no
        break;
      }

      case 0xF2: {
        if (mqtt_subscribed && client.connected()) {
          client.unsubscribe(listen_topic.c_str());
          mqtt_subscribed = false;
          listen_topic = "";
        }
        break;
      }

      default:
        //Serial.write('X');
        break;
    }
  }
}