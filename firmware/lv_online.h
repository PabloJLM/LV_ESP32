#ifndef LV_ONLINE_H
#define LV_ONLINE_H

#include <Arduino.h>

#ifdef LV_ONLINE

#if !defined(ARDUINO_ARCH_ESP32)
  #error "LV_ONLINE solo existe para ESP32."
#endif

#include "lv_boards.h"
#ifndef LV_SD_CS
  #error "Esta tarjeta no tiene pines de SD definidos en lv_boards.h"
#endif

#ifndef LV_SD_HZ
  #define LV_SD_HZ 10000000
#endif

#define LV_WIFI_TIMEOUT_MS 20000UL

#define LV_WIFI_SSID_MAX 32
#define LV_WIFI_PASS_MAX 63
#define LV_FTP_USER_MAX  32
#define LV_FTP_PASS_MAX  32

enum { LV_W_OFF = 0, LV_W_CONNECTING = 1, LV_W_UP = 2, LV_W_FAIL = 3 };
enum { LV_F_OFF = 0, LV_F_ON = 1, LV_F_SDERR = 2 };

void lv_onlineBegin();
void lv_onlineLoop();

bool lv_wifiSaveCreds(const char* ssid, const char* pass);
bool lv_wifiConnect();
void lv_onlineStatus(char* out, size_t n);
void lv_wifiDisconnect();
bool lv_ftpSaveCreds(const char* user, const char* pass);
bool lv_ftpSet(bool on);

void lv_onlineMacStr(char* out);
bool lv_radioActive();

#endif
#endif
