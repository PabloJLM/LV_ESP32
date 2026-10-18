/*
 * lv_hal.h — LV_ESP32 v3
 * API de canales logicos. Las tablas de pines estan en lv_boards.h y la
 * implementacion en lv_hal.cpp. El protocolo (lv_protocol.cpp) solo usa esto.
 */
#ifndef LV_HAL_H
#define LV_HAL_H

#include <Arduino.h>

#define LV_VERSION    "3.0.0"
#define LV_NUM_PIXELS 16

enum LvType : uint8_t { LV_DI = 0, LV_DO, LV_AI, LV_AO, LV_PWM, LV_SERVO, LV_NEO, LV_NTYPES };

const char* lv_variant();                 /* "ESP32", "ESP32-ONLINE", "AVR", "STM32" */
const char* lv_boardName();               /* "ESP32-U", "UNO", "K8", ... */
uint8_t     lv_count(LvType t);           /* cuantos canales de ese tipo */

void    lv_halBegin();

bool    lv_dWrite(uint8_t ch, uint8_t v);          /* DO */
bool    lv_dRead(uint8_t ch, uint8_t* v);          /* DI */
int16_t lv_aRead(uint8_t ch);                      /* AI: 0..4095, -1 no disponible, -2 canal invalido */
bool    lv_aWrite(uint8_t ch, uint8_t v);          /* AO */
bool    lv_pwm(uint8_t ch, uint8_t duty);          /* PWM 0..255 */
bool    lv_servo(uint8_t ch, uint8_t angle);       /* 0..180 */

bool    lv_neoSelect(uint8_t opt);                 /* elige el pin de la tira */
void    lv_neoAll(uint8_t r, uint8_t g, uint8_t b);
bool    lv_neoOne(uint8_t i, uint8_t r, uint8_t g, uint8_t b);

#endif /* LV_HAL_H */
