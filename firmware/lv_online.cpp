/*
 * lv_online.cpp — LV_ESP32   (solo se compila con -DLV_ONLINE)
 * Protocolo y pinout: ver lv_online.h
 *
 * Sin -DLV_ONLINE este archivo queda vacio, asi que arduino-cli puede
 * compilarlo para cualquier tarjeta sin problema.
 */
#include "lv_online.h"

#ifdef LV_ONLINE

#include <WiFi.h>
#include <SPI.h>
#include <SD.h>
#include <Preferences.h>
#include <SimpleFTPServer.h>

#if __has_include(<esp_mac.h>)
  #include <esp_mac.h>              /* arduino-esp32 3.x */
#endif
#include <esp_system.h>

/* SimpleFTPServer decide SD o FFat al COMPILAR LA LIBRERIA, no este archivo.
   Si esto falla es que faltaron las banderas del catalogo (ver lv_online.h). */
#if !defined(STORAGE_TYPE) || (STORAGE_TYPE != STORAGE_SD)
  #error "Compila con -DDEFAULT_FTP_SERVER_NETWORK_TYPE_ESP32=6 -DDEFAULT_STORAGE_TYPE_ESP32=5"
#endif

static Preferences prefs;
#if defined(CONFIG_IDF_TARGET_ESP32)
static SPIClass    sdSpi(VSPI);
#else
static SPIClass    sdSpi(FSPI);      /* ESP32-S3 (Nano ESP32) */
#endif
static FtpServer   ftp;

static uint8_t  wState = LV_W_OFF;
static uint8_t  fState = LV_F_OFF;
static uint32_t wT0    = 0;
static uint32_t sdMB   = 0;

/* --- NVS ------------------------------------------------------------------ */
static bool putStr(const char* key, const char* v) {
  if (!prefs.begin("lvonl", false)) return false;
  size_t w = prefs.putString(key, v);
  prefs.end();
  /* putString devuelve 0 con cadena vacia: una clave WiFi vacia es valida
     (red abierta), asi que solo es error si habia algo que escribir. */
  return (w == strlen(v));
}

static String getStr(const char* key) {
  String s;
  if (prefs.begin("lvonl", true)) {
    s = prefs.getString(key, "");
    prefs.end();
  }
  return s;
}

/* --- ADC2 / radio --------------------------------------------------------- */
bool lv_radioActive() { return WiFi.getMode() != WIFI_OFF; }

/* --- arranque / servicio -------------------------------------------------- */
void lv_onlineBegin() {
  /* El radio queda APAGADO: el ADC2 sigue util hasta que LabVIEW mande 0xC2. */
  WiFi.persistent(false);          /* no escribir en flash por su cuenta */
  WiFi.mode(WIFI_OFF);
}

void lv_onlineLoop() {
  if (wState == LV_W_CONNECTING) {
    if (WiFi.status() == WL_CONNECTED) {
      wState = LV_W_UP;
    } else if ((millis() - wT0) > LV_WIFI_TIMEOUT_MS) {
      WiFi.disconnect(true);       /* deja de reintentar con una clave mala */
      wState = LV_W_FAIL;
    }
  } else if (wState == LV_W_UP && WiFi.status() != WL_CONNECTED) {
    wState = LV_W_CONNECTING;      /* se cayo: AutoReconnect lo intenta de nuevo */
    wT0 = millis();
  }

  if (fState == LV_F_ON && wState == LV_W_UP) ftp.handleFTP();
}

/* --- WiFi ----------------------------------------------------------------- */
bool lv_wifiSaveCreds(const char* ssid, const char* pass) {
  if (strlen(ssid) == 0 || strlen(ssid) > LV_WIFI_SSID_MAX) return false;
  if (strlen(pass) > LV_WIFI_PASS_MAX) return false;
  return putStr("ws", ssid) && putStr("wp", pass);
}

bool lv_wifiConnect() {
  if (wState == LV_W_UP || wState == LV_W_CONNECTING) return true;
  String ssid = getStr("ws");
  if (ssid.length() == 0) return false;          /* nada guardado */
  String pass = getStr("wp");

  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.begin(ssid.c_str(), pass.length() ? pass.c_str() : nullptr);
  wState = LV_W_CONNECTING;
  wT0    = millis();
  return true;
}

void lv_wifiDisconnect() {
  lv_ftpSet(false);
  WiFi.disconnect(true);
  WiFi.mode(WIFI_OFF);             /* libera el ADC2 */
  wState = LV_W_OFF;
}

/* --- FTP + SD ------------------------------------------------------------- */
bool lv_ftpSaveCreds(const char* user, const char* pass) {
  if (strlen(user) == 0 || strlen(user) > LV_FTP_USER_MAX) return false;
  if (strlen(pass) == 0 || strlen(pass) > LV_FTP_PASS_MAX) return false;
  return putStr("fu", user) && putStr("fp", pass);
}

bool lv_ftpSet(bool on) {
  if (!on) {
    if (fState == LV_F_ON) ftp.end();
    if (fState != LV_F_OFF) { SD.end(); sdSpi.end(); }
    fState = LV_F_OFF;
    sdMB   = 0;
    return true;
  }

  if (fState == LV_F_ON) return true;
  if (wState != LV_W_UP) return false;           /* sin red no hay FTP */

  String user = getStr("fu");
  String pass = getStr("fp");
  if (user.length() == 0 || pass.length() == 0) return false;

  sdSpi.begin(LV_SD_SCK, LV_SD_MISO, LV_SD_MOSI, LV_SD_CS);
  if (!SD.begin(LV_SD_CS, sdSpi, LV_SD_HZ) || SD.cardType() == CARD_NONE) {
    SD.end();
    sdSpi.end();
    fState = LV_F_SDERR;
    return false;
  }
  sdMB = (uint32_t)(SD.totalBytes() >> 20);

  ftp.begin(user.c_str(), pass.c_str());
  fState = LV_F_ON;
  return true;
}

/* --- estado --------------------------------------------------------------- */
void lv_onlineStatus(char* out, size_t n) {
  IPAddress ip = (wState == LV_W_UP) ? WiFi.localIP() : IPAddress(0, 0, 0, 0);
  int rssi = (wState == LV_W_UP) ? WiFi.RSSI() : 0;
  snprintf(out, n, "%u,%u.%u.%u.%u,%d,%u,%lu",
           (unsigned)wState, ip[0], ip[1], ip[2], ip[3], rssi,
           (unsigned)fState, (unsigned long)sdMB);
}

void lv_onlineMacStr(char* out) {
  uint8_t m[6] = {0};
  esp_read_mac(m, ESP_MAC_WIFI_STA);   /* funciona aunque el radio este apagado */
  snprintf(out, 18, "%02X:%02X:%02X:%02X:%02X:%02X",
           m[0], m[1], m[2], m[3], m[4], m[5]);
}

#endif /* LV_ONLINE */
