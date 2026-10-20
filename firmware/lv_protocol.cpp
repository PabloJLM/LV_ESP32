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

void setup() {
  Serial.begin(115200);
  lv_halBegin();
#ifdef LV_ONLINE
  lv_onlineBegin();
#endif
}

void loop() {
#ifdef LV_ONLINE
  lv_onlineLoop();
#endif
  if (!Serial.available()) return;

  uint8_t cmd = (uint8_t)Serial.read();
  uint8_t p[20];

  switch (cmd) {

    case 0x01: {
      if (!readBytes(p, 2)) { nack(); break; }
      if (lv_dWrite(p[0], p[1])) ack(); else nack();
      break;
    }

    case 0x02: {
      if (!readBytes(p, 2)) { nack(); break; }
      uint8_t v;
      if (!lv_dRead(p[0], &v)) { nack(); break; }
      Serial.write('A');
      Serial.write(v ? '1' : '0');
      break;
    }

    case 0x03: {
      if (!readBytes(p, 3)) { nack(); break; }
      lv_neoAll(p[0], p[1], p[2]);
      ack();
      break;
    }

    case 0x04: {
      if (!readBytes(p, 4)) { nack(); break; }
      if (lv_neoOne(p[0], p[1], p[2], p[3])) ack(); else nack();
      break;
    }

    case 0x05: {
      if (!readBytes(p, 1)) { Serial.println(-2); break; }
      Serial.println(lv_aRead(p[0]));
      break;
    }

    case 0x06: {
      if (!readBytes(p, 2)) { nack(); break; }
      if (lv_aWrite(p[0], p[1])) ack(); else nack();
      break;
    }

    case 0x07: {
      if (!readBytes(p, 2)) { nack(); break; }
      if (lv_pwm(p[0], p[1])) ack(); else nack();
      break;
    }

    case 0x08: {
      if (!readBytes(p, 2)) { nack(); break; }
      if (lv_servo(p[0], p[1])) ack(); else nack();
      break;
    }

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

    case 0x0A: {
      if (!readBytes(p, 1)) { nack(); break; }
      if (lv_neoSelect(p[0])) ack(); else nack();
      break;
    }

#ifdef LV_ONLINE
    case 0xC1: {
      char ssid[LV_WIFI_SSID_MAX + 1], pass[LV_WIFI_PASS_MAX + 1];
      if (!readTwoStrings(ssid, LV_WIFI_SSID_MAX, true, pass, LV_WIFI_PASS_MAX)) { nack(); break; }
      if (lv_wifiSaveCreds(ssid, pass)) ack(); else nack();
      break;
    }

    case 0xC2: {
      if (lv_wifiConnect()) ack(); else nack();
      break;
    }

    case 0xC3: {
      char st[48];
      lv_onlineStatus(st, sizeof(st));
      Serial.println(st);
      break;
    }

    case 0xC4: {
      lv_wifiDisconnect();
      ack();
      break;
    }

    case 0xC5: {
      char user[LV_FTP_USER_MAX + 1], pass[LV_FTP_PASS_MAX + 1];
      if (!readTwoStrings(user, LV_FTP_USER_MAX, true, pass, LV_FTP_PASS_MAX)) { nack(); break; }
      if (lv_ftpSaveCreds(user, pass)) ack(); else nack();
      break;
    }

    case 0xC6: {
      if (!readBytes(p, 1)) { nack(); break; }
      if (lv_ftpSet(p[0] != 0)) ack(); else nack();
      break;
    }
#endif

    case 0xEF: {
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

    case 0xF0: {
      ack();
      break;
    }

    default:
      nack();
      break;
  }
}
