/*
 * ===========================================================================
 * lv_online.h — LV_ESP32   (solo se compila con -DLV_ONLINE, solo ESP32)
 * ---------------------------------------------------------------------------
 * Variante "online": el ESP32 se conecta a una red WiFi y expone el contenido
 * de una tarjeta SD (por SPI) como servidor FTP.
 *
 * LabVIEW NO habla con la red: sigue hablando VISA serial por el mismo USB y
 * el mismo protocolo binario. La red es solo para los archivos de la SD
 * (el cliente FTP es el PC: Explorador de Windows, FileZilla, etc).
 *
 *   0xC1 [ls][lp][ssid][pass]   guarda SSID y clave WiFi en flash (NVS)
 *                                                -> 'A','A' / 'X','X'
 *   0xC2 (sin payload)          conecta con lo guardado. NO bloquea: arranca
 *                               y se consulta con 0xC3 -> 'A','A' / 'X','X'
 *   0xC3 (sin payload)          estado -> "<wifi>,<ip>,<rssi>,<ftp>,<sdMB>\n"
 *                                 wifi: 0 apagado  1 conectando  2 conectado
 *                                       3 fallo (sin red o clave mala)
 *                                 ftp : 0 apagado  1 activo  2 error de SD
 *                                 sdMB: capacidad de la SD (0 si el FTP esta off)
 *   0xC4 (sin payload)          desconecta (detiene FTP y apaga el radio, asi
 *                               el ADC2 vuelve a funcionar) -> 'A','A'
 *   0xC5 [lu][lp][user][pass]   guarda usuario y clave del FTP en flash
 *                                                -> 'A','A' / 'X','X'
 *   0xC6 [on]                   1 = monta la SD y arranca el FTP, 0 = lo detiene
 *                               -> 'A','A' / 'X','X'
 *                               (X: sin WiFi, sin credenciales FTP o SD ausente)
 *
 * Al arrancar el radio esta APAGADO: hasta que mandes 0xC2 el ADC2 sigue
 * siendo utilizable. Una vez conectado, los pines ADC2 devuelven -1 (igual que
 * en la variante ESP-NOW).
 *
 * PINOUT DE LA SD  (ESP32-U: bus VSPI. Nano ESP32: ver lv_boards.h / PINOUT.md)
 *
 *      SD / modulo microSD         ESP32
 *      ------------------------------------
 *      SCK                         GPIO 18
 *      MISO (DO)                   GPIO 19
 *      MOSI (DI)                   GPIO 23
 *      CS                          GPIO 5
 *      VCC                         5V (VIN) si el modulo trae regulador,
 *                                  3V3 si es una SD "pelada"
 *      GND                         GND
 *
 *   Por que estos y no otros:
 *   - Son los pines nativos de VSPI (IOMUX): llegan a 40-80 MHz y no pasan por
 *     la matriz de GPIO.
 *   - Ninguno es ADC2, asi que no le roban canales al ADC del protocolo.
 *   - No chocan con nada del firmware: NeoPixel 25, DAC 26, I2C del LCD 21/22,
 *     UART0 1/3, flash 6-11.
 *   - Evita GPIO 12 (MTDI): una SD con pull-up ahi cambia el voltaje del flash
 *     y la placa no arranca. GPIO 5 es de strapping pero su estado por defecto
 *     (pull-up) es el que necesita el CS de la SD.
 *   Otras tarjetas o cableado distinto: -DLV_SD_CS=.. -DLV_SD_SCK=.. etc.
 *
 * LIBRERIA FTP: SimpleFTPServer (soporta modo pasivo, que es el que usan por
 * defecto Windows y FileZilla). Se configura para SD con las banderas
 *   -DDEFAULT_FTP_SERVER_NETWORK_TYPE_ESP32=6 -DDEFAULT_STORAGE_TYPE_ESP32=5
 * que ya pone el catalogo de tarjetas junto con -DLV_ONLINE.
 * ===========================================================================
 */
#ifndef LV_ONLINE_H
#define LV_ONLINE_H

#include <Arduino.h>

#ifdef LV_ONLINE

#if !defined(ARDUINO_ARCH_ESP32)
  #error "LV_ONLINE solo existe para ESP32."
#endif

/* Pines de la SD: salen de lv_boards.h (LV_SD_SCK/MISO/MOSI/CS) */
#include "lv_boards.h"
#ifndef LV_SD_CS
  #error "Esta tarjeta no tiene pines de SD definidos en lv_boards.h"
#endif

#ifndef LV_SD_HZ
  #define LV_SD_HZ 10000000          /* 10 MHz: aguanta cables de protoboard */
#endif

#define LV_WIFI_TIMEOUT_MS 20000UL   /* despues de esto el estado pasa a 3  */

#define LV_WIFI_SSID_MAX 32
#define LV_WIFI_PASS_MAX 63
#define LV_FTP_USER_MAX  32
#define LV_FTP_PASS_MAX  32

/* Estados que viajan en 0xC3 */
enum { LV_W_OFF = 0, LV_W_CONNECTING = 1, LV_W_UP = 2, LV_W_FAIL = 3 };
enum { LV_F_OFF = 0, LV_F_ON = 1, LV_F_SDERR = 2 };

void lv_onlineBegin();                                         /* setup()      */
void lv_onlineLoop();                                          /* cada loop()  */

bool lv_wifiSaveCreds(const char* ssid, const char* pass);     /* 0xC1 */
bool lv_wifiConnect();                                         /* 0xC2 */
void lv_onlineStatus(char* out, size_t n);                     /* 0xC3 */
void lv_wifiDisconnect();                                      /* 0xC4 */
bool lv_ftpSaveCreds(const char* user, const char* pass);      /* 0xC5 */
bool lv_ftpSet(bool on);                                       /* 0xC6 */

void lv_onlineMacStr(char* out);   /* out: al menos 18 bytes */
bool lv_radioActive();             /* lo consulta lv_hal.h por el ADC2 */

#endif /* LV_ONLINE */
#endif /* LV_ONLINE_H */
