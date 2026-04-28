/*
 * prueba_esp32_fixed.ino
 * LV_ESP32 — Firmware para LabVIEW via VISA serial
 *
 * PROTOCOLO — todos los comandos responden EXACTAMENTE 2 bytes:
 *   Escrituras:  'A' + 'A'
 *   Lecturas:    'A' + valor
 *   Errores:     'X' + 'X'
 *
 * Así todos los subVIs en LabVIEW hacen:
 *   Flush → Write N bytes → Read 2 bytes
 * Sin excepción. Sin desfase de buffer posible.
 *
 * CMDs:
 *   0x01  [pin, val]               digitalWrite     → 'A','A'
 *   0x02  [pin, dummy]             digitalRead      → 'A','0'/'1'
 *   0x03  [r, g, b]                NeoPixel todos   → 'A','A'
 *   0x04  [idx, r, g, b]           NeoPixel pixel   → 'A','A'
 *   0x05  [pin]                    analogRead       → [MSB, LSB]
 *   0x06  [pin, val]               DAC              → 'A','A'
 *   0x07  [pin, duty]              PWM              → 'A','A'
 *   0x08  [pin, angulo]            Servo            → 'A','A'
 *   0x09  [addr,col,fila,len,...] LCD print         → 'A','A'
 *   0xF0  (sin payload)            Ping             → 'A','A'
 */

#include <Adafruit_NeoPixel.h>
#include <Arduino.h>
#include <ESP32Servo.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

#define NUM_PIXELS   3
#define PIN_NEOPIXEL 25
#define TIMEOUT_MS   200

Adafruit_NeoPixel pixels(NUM_PIXELS, PIN_NEOPIXEL, NEO_GRB + NEO_KHZ800);
Servo myServo;
static int8_t servoPin = -1;

static uint8_t ledcCh[40];
static uint8_t nextCh = 0;

static LiquidCrystal_I2C* lcd = nullptr;
static uint8_t lcdAddr = 0x00;

// ── Helpers ──────────────────────────────────────────────────────────────────

bool readBytes(uint8_t* buf, uint8_t n) {
  uint32_t t = millis();
  uint8_t i = 0;
  while (i < n) {
    if (Serial.available()) {
      buf[i++] = (uint8_t)Serial.read();
    } else if ((millis() - t) > TIMEOUT_MS) {
      return false;
    }
  }
  return true;
}

static void ack()  { Serial.write('A'); Serial.write('A'); }
static void nack() { Serial.write('X'); Serial.write('X'); }

static void flushADC(uint8_t pin) {
  for (uint8_t i = 0; i < 8; i++) analogRead(pin);
}

static void attachLedcPin(uint8_t pin) {
  if (pin < 40 && ledcCh[pin] != 0xFF) return;
  uint8_t ch = (nextCh++) % 8;
  ledcAttachChannel(pin, 1000, 8, ch);
  if (pin < 40) ledcCh[pin] = ch;
}

// ── Setup ────────────────────────────────────────────────────────────────────

void setup() {
  Serial.begin(115200);
  memset(ledcCh, 0xFF, sizeof(ledcCh));
  pixels.begin();
  pixels.clear();
  pixels.show();
}

// ── Loop ─────────────────────────────────────────────────────────────────────

void loop() {
  if (!Serial.available()) return;

  uint8_t cmd = (uint8_t)Serial.read();
  uint8_t p[20];

  switch (cmd) {

    // ── 0x01: digitalWrite ──────────────────────────────────────────────────
    case 0x01: {
      if (!readBytes(p, 2)) { nack(); break; }
      pinMode(p[0], OUTPUT);
      digitalWrite(p[0], p[1] ? HIGH : LOW);
      ack();
      break;
    }

    // ── 0x02: digitalRead ───────────────────────────────────────────────────
    // 'A' + '0'/'1'  →  VI compara con "A1"
    case 0x02: {
      if (!readBytes(p, 2)) { nack(); break; }
      pinMode(p[0], INPUT);
      Serial.write('A');
      Serial.write(digitalRead(p[0]) ? '1' : '0');
      break;
    }

    // ── 0x03: NeoPixel todos ────────────────────────────────────────────────
    case 0x03: {
      if (!readBytes(p, 3)) { nack(); break; }
      for (uint8_t i = 0; i < NUM_PIXELS; i++)
        pixels.setPixelColor(i, pixels.Color(p[0], p[1], p[2]));
      pixels.show();
      ack();
      break;
    }

    // ── 0x04: NeoPixel individual ───────────────────────────────────────────
    case 0x04: {
      if (!readBytes(p, 4)) { nack(); break; }
      if (p[0] >= NUM_PIXELS) { nack(); break; }
      pixels.setPixelColor(p[0], pixels.Color(p[1], p[2], p[3]));
      pixels.show();
      ack();
      break;
    }

    // ── 0x05: analogRead ──────────────────────────────────────────────────
    // Responde string ASCII terminado en \n: "0"~"4095"\n
    // VI: TermChar = \n, lee hasta encontrarlo, convierte string a numero
    case 0x05: {
      if (!readBytes(p, 1)) { Serial.println(-1); break; }
      flushADC(p[0]);
      uint16_t v = (uint16_t)analogRead(p[0]);
      Serial.println(v);
      break;
    }

    // ── 0x06: DAC ───────────────────────────────────────────────────────────
    case 0x06: {
      if (!readBytes(p, 2)) { nack(); break; }
      if (p[0] != 26) { nack(); break; } // pin 25 reservado para NeoPixel
      analogWrite(p[0], p[1]);
      ack();
      break;
    }

    // ── 0x07: PWM ───────────────────────────────────────────────────────────
    case 0x07: {
      if (!readBytes(p, 2)) { nack(); break; }
      attachLedcPin(p[0]);
      ledcWrite(p[0], p[1]);
      ack();
      break;
    }

    // ── 0x08: Servo ─────────────────────────────────────────────────────────
    case 0x08: {
      if (!readBytes(p, 2)) { nack(); break; }
      uint8_t angulo = p[1] > 210 ? 210 : p[1];
      if (servoPin != (int8_t)p[0]) {
        if (myServo.attached()) myServo.detach();
        myServo.attach(p[0], 500, 2400);
        servoPin = (int8_t)p[0];
      }
      myServo.write(angulo);
      ack();
      break;
    }

    // ── 0x09: LCD ───────────────────────────────────────────────────────────
    // [addr, col, fila, len, char0..charN]
    case 0x09: {
      if (!readBytes(p, 4)) { nack(); break; }
      uint8_t addr = p[0];
      uint8_t col  = p[1] > 15 ? 15 : p[1];
      uint8_t fila = p[2] > 1  ?  1 : p[2];
      uint8_t len  = p[3] > 16 ? 16 : p[3];
      uint8_t txt[17] = {0};
      if (len > 0 && !readBytes(txt, len)) { nack(); break; }
      if (lcd == nullptr || lcdAddr != addr) {
        delete lcd;
        lcd = new LiquidCrystal_I2C(addr, 16, 2);
        lcd->init();
        lcd->backlight();
        lcdAddr = addr;
      }
      lcd->setCursor(col, fila);
      for (uint8_t i = 0; i < len; i++) lcd->write(txt[i]);
      ack();
      break;
    }

    // ── 0xF0: Ping ──────────────────────────────────────────────────────────
    case 0xF0: {
      ack();
      break;
    }

    default:
      nack();
      break;
  }
}
