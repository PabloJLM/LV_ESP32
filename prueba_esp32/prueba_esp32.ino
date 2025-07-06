#include <Adafruit_NeoPixel.h>

#define NUM_PIXELS 3
#define PIN_NEOPIXEL 25
Adafruit_NeoPixel pixels(NUM_PIXELS, PIN_NEOPIXEL, NEO_GRB + NEO_KHZ800);

void setup() {
  Serial.begin(115200);
  pixels.begin();
  pixels.show();  
}

void loop() {
  if (Serial.available() > 0) {
    byte instruccion = Serial.read();

    switch (instruccion) {
      case 0x01: {  // digitalWrite 
        while (Serial.available() < 2);
        byte pin = Serial.read();
        byte val = Serial.read();
        pinMode(pin, OUTPUT);
        digitalWrite(pin, val == 0 ? LOW : HIGH);
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
        break;
      }
      case 0x04: {//neopixel individual
      while (Serial.available() < 4);
        byte neo = Serial.read();
        byte r = Serial.read();
        byte g = Serial.read();
        byte b = Serial.read();
        pixels.setPixelColor(neo, pixels.Color(r, g, b));
        pixels.show();
        break;
      }

      case 0xF0: {  // Ping simple
        Serial.write('A');
        break;
      }

      default:

        break;
    }
  }
}
