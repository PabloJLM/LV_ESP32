/*
 * ===========================================================================
 * LV_ESP32 — Firmware
 * Tesla Lab · Universidad Galileo · Pablo Lopez Mazariegos
 * ===========================================================================
 *
 * UN SOLO PROTOCOLO PARA TODAS LAS TARJETAS, POR EL MISMO USB.
 *
 * Este archivo es identico compile para lo que compile: ESP32, ESP32 con
 * ESP-NOW, Arduino UNO/Nano/Mega o STM32. Lo unico que cambia por debajo es
 * lv_hal.h. Por eso los VIs de LabVIEW no cambian al cambiar de tarjeta.
 *
 * Nada de sockets, nada de TCP, nada de IP. LabVIEW habla VISA serial y ya.
 *
 * PROTOCOLO — respuesta de EXACTAMENTE 2 bytes, salvo donde se indica:
 *   Escrituras:  'A' + 'A'
 *   Lecturas:    'A' + valor
 *   Errores:     'X' + 'X'
 *
 * Todos los subVIs hacen:  Flush -> Write N bytes -> Read 2 bytes
 *
 * CMDs (identicos a v2, sin un solo cambio)
 *   0x01  [pin, val]              digitalWrite      -> 'A','A'
 *   0x02  [pin, dummy]            digitalRead       -> 'A','0'/'1'
 *   0x03  [r, g, b]               NeoPixel todos    -> 'A','A'
 *   0x04  [idx, r, g, b]          NeoPixel pixel    -> 'A','A' / 'X','X'
 *   0x05  [pin]                   analogRead        -> "0".."4095"\n
 *   0x06  [pin, val]              DAC               -> 'A','A' / 'X','X'
 *   0x07  [pin, duty]             PWM               -> 'A','A'
 *   0x08  [pin, angulo]           Servo             -> 'A','A'
 *   0x09  [addr,col,fila,len,..]  LCD I2C           -> 'A','A'
 *   0xF0  (sin payload)           Ping              -> 'A','A'
 *
 * NUEVOS (existen en todas las variantes)
 *   0xEF  (sin payload)           Identidad         -> "LV,<var>,<ver>,<mac>\n"
 *
 * NUEVOS DE ESP-NOW (solo compilando con -DLV_ESPNOW)
 *   0xD1  [mac0..5][len][datos]   enviar            -> 'A','A' / 'X','X'
 *   0xD2  (sin payload)           recibir           -> "<mac>,<datos>\n" o "-\n"
 *   0xD3  [canal 1..13]           canal del radio   -> 'A','A' / 'X','X'
 *
 *   El BROADCAST no tiene comando propio: es enviar a FF:FF:FF:FF:FF:FF.
 *   Por eso en LabVIEW basta con DOS VIs nuevos: Send y Receive.
 *   El peer se registra solo la primera vez que le mandas algo.
 *   0xD2 nunca bloquea: si no hay nada devuelve "-\n".
 *
 * NOTAS DE COMPATIBILIDAD
 *   - El ADC siempre responde 0..4095. En AVR es de 10 bits y se escala en el
 *     firmware, no en LabVIEW.
 *   - 0x06 (DAC) responde 'X','X' en tarjetas sin DAC (Arduino AVR, ESP32-S3).
 *     El VI ya trata 'X' como error, asi que degrada solo.
 *   - En la variante ESP-NOW el radio esta encendido, asi que leer un pin del
 *     ADC2 devuelve -1 en vez de un numero inventado.
 * ===========================================================================
 */

#include <Arduino.h>
#include <Adafruit_NeoPixel.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

#include "lv_hal.h"
#ifdef LV_ESPNOW
  #include "lv_espnow.h"
#endif

#define NUM_PIXELS 3
#define TIMEOUT_MS 200

Adafruit_NeoPixel pixels(NUM_PIXELS, LV_NEOPIXEL_PIN, NEO_GRB + NEO_KHZ800);

static LiquidCrystal_I2C* lcd = nullptr;
static uint8_t lcdAddr = 0x00;

/* ── Helpers ─────────────────────────────────────────────────────────────── */

static bool readBytes(uint8_t* buf, uint8_t n) {
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

/* ── Setup ───────────────────────────────────────────────────────────────── */

void setup() {
  Serial.begin(115200);
  lv_halBegin();
  pixels.begin();
  pixels.clear();
  pixels.show();
#ifdef LV_ESPNOW
  lv_nowBegin();
#endif
}

/* ── Loop ────────────────────────────────────────────────────────────────── */

void loop() {
  if (!Serial.available()) return;

  uint8_t cmd = (uint8_t)Serial.read();
  uint8_t p[20];

  switch (cmd) {

    /* ── 0x01: digitalWrite ────────────────────────────────────────────── */
    case 0x01: {
      if (!readBytes(p, 2)) { nack(); break; }
      lv_pinOutput(p[0]);
      lv_write(p[0], p[1]);
      ack();
      break;
    }

    /* ── 0x02: digitalRead ─────────────────────────────────────────────── */
    case 0x02: {
      if (!readBytes(p, 2)) { nack(); break; }
      lv_pinInput(p[0]);
      Serial.write('A');
      Serial.write(lv_read(p[0]) ? '1' : '0');
      break;
    }

    /* ── 0x03: NeoPixel todos ──────────────────────────────────────────── */
    case 0x03: {
      if (!readBytes(p, 3)) { nack(); break; }
      for (uint8_t i = 0; i < NUM_PIXELS; i++)
        pixels.setPixelColor(i, pixels.Color(p[0], p[1], p[2]));
      pixels.show();
      ack();
      break;
    }

    /* ── 0x04: NeoPixel individual ─────────────────────────────────────── */
    case 0x04: {
      if (!readBytes(p, 4)) { nack(); break; }
      if (p[0] >= NUM_PIXELS) { nack(); break; }
      pixels.setPixelColor(p[0], pixels.Color(p[1], p[2], p[3]));
      pixels.show();
      ack();
      break;
    }

    /* ── 0x05: analogRead — ASCII con \n, siempre 0..4095 ──────────────── */
    case 0x05: {
      if (!readBytes(p, 1)) { Serial.println(-1); break; }
      Serial.println(lv_adc(p[0]));
      break;
    }

    /* ── 0x06: DAC ─────────────────────────────────────────────────────── */
    case 0x06: {
      if (!readBytes(p, 2)) { nack(); break; }
      if (lv_dac(p[0], p[1])) ack(); else nack();
      break;
    }

    /* ── 0x07: PWM ─────────────────────────────────────────────────────── */
    case 0x07: {
      if (!readBytes(p, 2)) { nack(); break; }
      lv_pwm(p[0], p[1]);
      ack();
      break;
    }

    /* ── 0x08: Servo ───────────────────────────────────────────────────── */
    case 0x08: {
      if (!readBytes(p, 2)) { nack(); break; }
      lv_servo(p[0], p[1]);
      ack();
      break;
    }

    /* ── 0x09: LCD I2C — [addr, col, fila, len, texto...] ──────────────── */
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

#ifdef LV_ESPNOW
    /* ── 0xD1: ESP-NOW enviar — [mac0..5][len][datos...] ───────────────── */
    /*  Broadcast = enviar a FF:FF:FF:FF:FF:FF. Sin comando aparte.        */
    case 0xD1: {
      uint8_t mac[6];
      uint8_t len;
      if (!readBytes(mac, 6))  { nack(); break; }
      if (!readBytes(&len, 1)) { nack(); break; }
      if (len > LV_NOW_MAXLEN) { nack(); break; }
      uint8_t buf[LV_NOW_MAXLEN];
      if (len && !readBytes(buf, len)) { nack(); break; }
      if (lv_nowSend(mac, buf, len)) ack(); else nack();
      break;
    }

    /* ── 0xD2: ESP-NOW recibir — no bloquea ────────────────────────────── */
    case 0xD2: {
      LvNowMsg m;
      if (!lv_nowPop(&m)) { Serial.println(F("-")); break; }   /* nunca bloquea */
      char macs[18];
      snprintf(macs, sizeof(macs), "%02X:%02X:%02X:%02X:%02X:%02X",
               m.mac[0], m.mac[1], m.mac[2], m.mac[3], m.mac[4], m.mac[5]);
      Serial.print(macs);
      Serial.print(',');
      /* Protege el framing: un \n dentro del dato partiria la linea. */
      for (uint8_t i = 0; i < m.len; i++) {
        uint8_t c = m.data[i];
        Serial.write((c == '\n' || c == '\r') ? ' ' : c);
      }
      Serial.write('\n');
      break;
    }

    /* ── 0xD3: canal del radio ─────────────────────────────────────────── */
    case 0xD3: {
      if (!readBytes(p, 1)) { nack(); break; }
      if (lv_nowChannel(p[0])) ack(); else nack();
      break;
    }
#endif

    /* ── 0xEF: identidad — "LV,<variante>,<version>,<mac>\n" ───────────── */
    case 0xEF: {
      Serial.print(F("LV,"));
      Serial.print(F(LV_VARIANT));
      Serial.print(',');
      Serial.print(F(LV_VERSION));
      Serial.print(',');
#ifdef LV_ESPNOW
      char macs[18];
      lv_nowMacStr(macs);
      Serial.println(macs);
#else
      Serial.println(F("-"));
#endif
      break;
    }

    /* ── 0xF0: Ping ────────────────────────────────────────────────────── */
    case 0xF0: {
      ack();
      break;
    }

    default:
      nack();
      break;
  }
}
