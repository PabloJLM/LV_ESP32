/*
 * ===========================================================================
 * lv_espnow.h — LV_ESP32   (solo se compila con -DLV_ESPNOW)
 * ---------------------------------------------------------------------------
 * ESP-NOW dentro del MISMO protocolo binario, por el MISMO cable USB.
 * No hay sockets, no hay TCP, no hay IP. LabVIEW sigue hablando VISA serial
 * exactamente igual que siempre.
 *
 * Solo 3 comandos nuevos, y el broadcast NO necesita comando propio: es
 * enviar a la MAC FF:FF:FF:FF:FF:FF. Por eso en LabVIEW son 2 VIs, no 4.
 *
 *   0xD1 [mac0..5][len][datos...]   enviar   -> 'A','A' / 'X','X'
 *   0xD2 (sin payload)              recibir  -> "<mac>,<datos>\n"  o  "-\n"
 *   0xD3 [canal]                    canal    -> 'A','A' / 'X','X'
 *
 * El peer se registra solo la primera vez que le envias algo: LabVIEW no
 * tiene que llamar a ningun "add peer".
 *
 * Recibir NO bloquea. 0xD2 devuelve "-\n" si no hay nada, asi que un loop de
 * LabVIEW puede sondear sin colgarse. Los mensajes que llegan mientras nadie
 * consulta se guardan en una cola de 6.
 * ===========================================================================
 */
#ifndef LV_ESPNOW_H
#define LV_ESPNOW_H

#include <WiFi.h>
#include <esp_now.h>
#include <esp_wifi.h>

#define LV_NOW_MAXLEN 200
#define LV_NOW_SLOTS  6

struct LvNowMsg {
  uint8_t mac[6];
  uint8_t len;
  uint8_t data[LV_NOW_MAXLEN];
};

static volatile LvNowMsg lv_nowQ[LV_NOW_SLOTS];
static volatile uint8_t  lv_nowHead = 0;      /* donde escribe la ISR   */
static volatile uint8_t  lv_nowTail = 0;      /* donde lee LabVIEW      */
static volatile uint16_t lv_nowLost = 0;      /* perdidos por cola llena */
static bool lv_nowReady = false;

/* lv_hal.h lo consulta: con el radio encendido el ADC2 no sirve */
bool lv_radioActive() { return lv_nowReady; }

/* --- callback de recepcion ------------------------------------------------ */
#if defined(ESP_ARDUINO_VERSION_MAJOR) && ESP_ARDUINO_VERSION_MAJOR >= 3
static void lv_nowRecv(const esp_now_recv_info_t* info, const uint8_t* data, int len) {
  const uint8_t* src = info->src_addr;
#else
static void lv_nowRecv(const uint8_t* src, const uint8_t* data, int len) {
#endif
  uint8_t next = (uint8_t)((lv_nowHead + 1) % LV_NOW_SLOTS);
  if (next == lv_nowTail) { lv_nowLost++; return; }      /* cola llena */
  if (len > LV_NOW_MAXLEN) len = LV_NOW_MAXLEN;
  LvNowMsg* m = (LvNowMsg*)&lv_nowQ[lv_nowHead];
  memcpy(m->mac, src, 6);
  m->len = (uint8_t)len;
  memcpy(m->data, data, len);
  lv_nowHead = next;
}

/* --- arranque ------------------------------------------------------------- */
static bool lv_nowBegin() {
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();                 /* ESP-NOW no necesita router */
  if (esp_now_init() != ESP_OK) return false;
  esp_now_register_recv_cb(lv_nowRecv);
  lv_nowReady = true;
  return true;
}

static bool lv_nowChannel(uint8_t ch) {
  if (ch < 1 || ch > 13) return false;
  esp_wifi_set_promiscuous(true);
  bool ok = (esp_wifi_set_channel(ch, WIFI_SECOND_CHAN_NONE) == ESP_OK);
  esp_wifi_set_promiscuous(false);
  return ok;
}

/* --- enviar (registra el peer solo si hace falta) ------------------------- */
static bool lv_nowSend(const uint8_t mac[6], const uint8_t* data, uint8_t len) {
  if (!lv_nowReady) return false;
  if (!esp_now_is_peer_exist(mac)) {
    esp_now_peer_info_t peer;
    memset(&peer, 0, sizeof(peer));
    memcpy(peer.peer_addr, mac, 6);
    peer.channel = 0;                /* 0 = el canal actual */
    peer.encrypt = false;
    if (esp_now_add_peer(&peer) != ESP_OK) return false;
  }
  return esp_now_send(mac, data, len) == ESP_OK;
}

/* --- hay mensaje? --------------------------------------------------------- */
static bool lv_nowHas() { return lv_nowHead != lv_nowTail; }

/* Copia el mensaje mas viejo y lo saca de la cola. */
static bool lv_nowPop(LvNowMsg* out) {
  if (!lv_nowHas()) return false;
  memcpy(out, (const void*)&lv_nowQ[lv_nowTail], sizeof(LvNowMsg));
  lv_nowTail = (uint8_t)((lv_nowTail + 1) % LV_NOW_SLOTS);
  return true;
}

/* --- MAC propia, en texto ------------------------------------------------- */
static void lv_nowMacStr(char* out) {   /* out: al menos 18 bytes */
  uint8_t m[6] = {0};
  WiFi.macAddress(m);
  snprintf(out, 18, "%02X:%02X:%02X:%02X:%02X:%02X",
           m[0], m[1], m[2], m[3], m[4], m[5]);
}

#endif /* LV_ESPNOW_H */
