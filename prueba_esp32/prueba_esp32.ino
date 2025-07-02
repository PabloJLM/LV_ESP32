#include <Adafruit_NeoPixel.h>

#define MAX_PINS 40
bool pinConfigured[MAX_PINS] = {false};

#define PIN_NEOPIXEL 25
#define NUM_PIXELS 3
Adafruit_NeoPixel pixels(NUM_PIXELS, PIN_NEOPIXEL, NEO_GRB + NEO_KHZ800);

void setup() {
  Serial.begin(115200);
  pixels.begin();
  pixels.show();
  Serial.println("ESP32 listo.");
}

void loop() {
  if (Serial.available()) {
    String input = Serial.readStringUntil('\n');
    input.trim();

    if (input.length() < 2) {
      Serial.println("ERROR: Comando demasiado corto.");
      return;
    }

    char cmdType = input.charAt(0);
    String data = input.substring(1);

    if (cmdType == '1') {
      
      if (data.length() != 3) {
        Serial.println("ERROR: Formato comando digital incorrecto.");
        return;
      }

      int pin = data.substring(0, 2).toInt();
      int val = data.charAt(2) - '0';

      if (pin < 0 || pin >= MAX_PINS) {
        Serial.println("ERROR: Pin inválido.");
        return;
      }
      if (val != 0 && val != 1) {
        Serial.println("ERROR: Valor inválido.");
        return;
      }
      if (!pinConfigured[pin]) {
        pinMode(pin, OUTPUT);
        pinConfigured[pin] = true;
      }
      digitalWrite(pin, val == 1 ? HIGH : LOW);
      Serial.print("Pin ");
      Serial.print(pin);
      Serial.print(" <- ");
      Serial.println(val == 1 ? "HIGH" : "LOW");

    } else if (cmdType == '2') {
      
      if (data.length() == 0) {
        Serial.println("ERROR: Comando NeoPixel vacío.");
        return;
      }

      unsigned long colorNum = strtoul(data.c_str(), NULL, 10);

      uint8_t blue  = (colorNum >> 0) & 0xFF;
      uint8_t green = (colorNum >> 8) & 0xFF;
      uint8_t red   = (colorNum >> 16) & 0xFF;

      for (int i = 0; i < NUM_PIXELS; i++) {
        pixels.setPixelColor(i, pixels.Color(red, green, blue));
      }
      pixels.show();

      Serial.print("Color NeoPixel recibido: R=");
      Serial.print(red);
      Serial.print(" G=");
      Serial.print(green);
      Serial.print(" B=");
      Serial.println(blue);

    } else {
      Serial.println("ERROR: Comando desconocido.");
    }
  }
}
