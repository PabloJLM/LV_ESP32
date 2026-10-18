/*
 * ===========================================================================
 * lv_protocol.cpp — LV_ESP32 v3
 * Tesla Lab · Universidad Galileo · Pablo Lopez Mazariegos
 * ---------------------------------------------------------------------------
 * PROTOCOLO v3 — canales logicos (tipo PLC). Mismo USB serial, mismos 2 bytes
 * de respuesta. LabVIEW manda el NUMERO DE CANAL, no el GPIO. Las tablas de
 * canal -> pin de cada tarjeta estan en lv_boards.h y en PINOUT.md.
 *
 * Todos los subVIs hacen:  Flush -> Write N bytes -> Read 2 bytes
 *
 *   Escrituras:  'A','A'      Lecturas digitales: 'A','0'/'1'      Error: 'X','X'
 *
 *   0x01 [ch, val]               DO  digitalWrite         -> 'A','A' / 'X','X'
 *   0x02 [ch, dummy]             DI  digitalRead          -> 'A','0'|'1' / 'X','X'
 *   0x03 [r, g, b]               NeoPixel todos           -> 'A','A'
 *   0x04 [idx, r, g, b]          NeoPixel pixel           -> 'A','A' / 'X','X'
 *   0x05 [ch]                    AI  analogRead           -> "0".."4095"\n
 *                                   -1 = no disponible ahora (ADC2 con WiFi)
 *                                   -2 = canal invalido
 *   0x06 [ch, val]               AO  DAC 0..255           -> 'A','A' / 'X','X'
 *   0x07 [ch, duty]              PWM 0..255               -> 'A','A' / 'X','X'
 *   0x08 [ch, angulo]            SERVO 0..180             -> 'A','A' / 'X','X'
 *   0x09 [addr,col,fila,len,..]  LCD I2C                  -> 'A','A'
 *   0x0A [opcion]                pin de la tira NeoPixel  -> 'A','A' / 'X','X'
 *   0xEF (sin payload)           Identidad ->
 *        "LV,<variante>,<ver>,<mac>,<placa>,<nDI>,<nDO>,<nAI>,<nAO>,<nPWM>,<nSERVO>,<nNEO>\n"
 *   0xF0 (sin payload)           Ping                     -> 'A','A'
 *
 *   Variante ONLINE (-DLV_ONLINE, solo ESP32): 0xC1..0xC6, ver lv_online.h
 * ===========================================================================
 */
#include <Arduino.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

#include "lv_hal.h"
#ifdef LV_ONLINE
  #include "lv_online.h"
#endif

#define TIMEOUT_MS 200

static LiquidCrystal_I2C* lcd = nullptr;
static uint8_t lcdAddr = 0x00;

/* -- helpers ---------------------------------------------------------------- */

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

#ifdef LV_ONLINE
/* Lee [la][lb][a...][b...] (dos cadenas con su longitud). Si las longitudes
   no son validas igual consume los bytes que anuncian, para que no queden en
   el buffer y se interpreten despues como comandos. */
static bool readTwoStrings(char* a, uint8_t maxA, bool aRequired,
                           char* b, uint8_t maxB) {
  uint8_t h[2];
  if (!readBytes(h, 2)) return false;
  bool ok = (h[0] <= maxA) && (h[1] <= maxB) && (!aRequired || h[0] > 0);
  for (uint8_t i = 0; i < h[0] + h[1]; i++) {
    uint8_t c;
    if (!readBytes(&c, 1)) return false;
    if (!ok) continue;
    if (i < h[0]) a[i] = (char)c; else b[i - h[0]] = (char)c;
  }
  if (ok) { a[h[0]] = 0; b[h[1]] = 0; }
  return ok;
}
#endif

/* -- setup / loop ------------------------------------------------------------ */

void setup() {
  Serial.begin(115200);
  lv_halBegin();
#ifdef LV_ONLINE
  lv_onlineBegin();
#endif
}

void loop() {
#ifdef LV_ONLINE
  lv_onlineLoop();                 /* estado del WiFi y atencion del FTP */
#endif
  if (!Serial.available()) return;

  uint8_t cmd = (uint8_t)Serial.read();
  uint8_t p[20];

  switch (cmd) {

    case 0x01: {                                   /* DO */
      if (!readBytes(p, 2)) { nack(); break; }
      if (lv_dWrite(p[0], p[1])) ack(); else nack();
      break;
    }

    case 0x02: {                                   /* DI */
      if (!readBytes(p, 2)) { nack(); break; }
      uint8_t v;
      if (!lv_dRead(p[0], &v)) { nack(); break; }
      Serial.write('A');
      Serial.write(v ? '1' : '0');
      break;
    }

    case 0x03: {                                   /* NeoPixel todos */
      if (!readBytes(p, 3)) { nack(); break; }
      lv_neoAll(p[0], p[1], p[2]);
      ack();
      break;
    }

    case 0x04: {                                   /* NeoPixel individual */
      if (!readBytes(p, 4)) { nack(); break; }
      if (lv_neoOne(p[0], p[1], p[2], p[3])) ack(); else nack();
      break;
    }

    case 0x05: {                                   /* AI: ASCII con \n */
      if (!readBytes(p, 1)) { Serial.println(-2); break; }
      Serial.println(lv_aRead(p[0]));
      break;
    }

    case 0x06: {                                   /* AO */
      if (!readBytes(p, 2)) { nack(); break; }
      if (lv_aWrite(p[0], p[1])) ack(); else nack();
      break;
    }

    case 0x07: {                                   /* PWM */
      if (!readBytes(p, 2)) { nack(); break; }
      if (lv_pwm(p[0], p[1])) ack(); else nack();
      break;
    }

    case 0x08: {                                   /* SERVO */
      if (!readBytes(p, 2)) { nack(); break; }
      if (lv_servo(p[0], p[1])) ack(); else nack();
      break;
    }

    case 0x09: {                                   /* LCD I2C */
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

    case 0x0A: {                                   /* pin de la tira NeoPixel */
      if (!readBytes(p, 1)) { nack(); break; }
      if (lv_neoSelect(p[0])) ack(); else nack();
      break;
    }

#ifdef LV_ONLINE
    case 0xC1: {                                   /* guardar WiFi */
      char ssid[LV_WIFI_SSID_MAX + 1], pass[LV_WIFI_PASS_MAX + 1];
      if (!readTwoStrings(ssid, LV_WIFI_SSID_MAX, true, pass, LV_WIFI_PASS_MAX)) { nack(); break; }
      if (lv_wifiSaveCreds(ssid, pass)) ack(); else nack();
      break;
    }

    case 0xC2: {                                   /* conectar, no bloquea */
      if (lv_wifiConnect()) ack(); else nack();
      break;
    }

    case 0xC3: {                                   /* estado */
      char st[48];
      lv_onlineStatus(st, sizeof(st));
      Serial.println(st);
      break;
    }

    case 0xC4: {                                   /* desconectar */
      lv_wifiDisconnect();
      ack();
      break;
    }

    case 0xC5: {                                   /* guardar FTP */
      char user[LV_FTP_USER_MAX + 1], pass[LV_FTP_PASS_MAX + 1];
      if (!readTwoStrings(user, LV_FTP_USER_MAX, true, pass, LV_FTP_PASS_MAX)) { nack(); break; }
      if (lv_ftpSaveCreds(user, pass)) ack(); else nack();
      break;
    }

    case 0xC6: {                                   /* FTP on/off */
      if (!readBytes(p, 1)) { nack(); break; }
      if (lv_ftpSet(p[0] != 0)) ack(); else nack();
      break;
    }
#endif

    case 0xEF: {                                   /* identidad */
      Serial.print(F("LV,"));
      Serial.print(lv_variant());
      Serial.print(',');
      Serial.print(F(LV_VERSION));
      Serial.print(',');
#ifdef LV_ONLINE
      char macs[18];
      lv_onlineMacStr(macs);
      Serial.print(macs);
#else
      Serial.print('-');
#endif
      Serial.print(',');
      Serial.print(lv_boardName());
      for (uint8_t t = 0; t < LV_NTYPES; t++) {
        Serial.print(',');
        Serial.print(lv_count((LvType)t));
      }
      Serial.println();
      break;
    }

    case 0xF0: {                                   /* ping */
      ack();
      break;
    }

    default:
      nack();
      break;
  }
}
