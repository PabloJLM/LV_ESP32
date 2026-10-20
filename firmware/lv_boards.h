#ifndef LV_BOARDS_H
#define LV_BOARDS_H

#include <Arduino.h>

#if defined(ARDUINO_ARCH_ESP32) && defined(CONFIG_IDF_TARGET_ESP32)
  #define LV_ARCH_ESP32  1
  #define LV_ARCH_NAME   "ESP32"
  #define LV_BOARD_NAME  "ESP32-U"

  #define LV_T_AI        36, 39, 34, 35, 32, 33,
  #define LV_T_AI_ADC2   0, 0, 0, 0, 0, 0,
  #define LV_T_AO        26,
  #define LV_T_PWM       4, 12,
  #define LV_T_SERVO     13, 14,
  #define LV_T_NEO       25, 27,
  #ifdef LV_ONLINE
    #define LV_T_DI      0, 15, 36, 39, 34, 35, 32, 33,
    #define LV_T_DO      2,
    #define LV_SD_SCK    18
    #define LV_SD_MISO   19
    #define LV_SD_MOSI   23
    #define LV_SD_CS     5
  #else
    #define LV_T_DI      0, 15, 36, 39, 34, 35, 32, 33, 5, 18,
    #define LV_T_DO      2, 19, 23,
  #endif

#elif defined(ARDUINO_NANO_ESP32)
  #define LV_ARCH_ESP32  1
  #define LV_ARCH_NAME   "ESP32"
  #define LV_BOARD_NAME  "NANO-ESP32"

  #define LV_T_AI        A0, A1, A2, A3, A6, A7,
  #define LV_T_AI_ADC2   0,  0,  0,  0,  1,  1,
  #define LV_T_AO
  #define LV_T_PWM       D4, D5, D6,
  #define LV_T_SERVO     D7, D8,
  #define LV_T_NEO       D2, D3,
  #ifdef LV_ONLINE
    #define LV_T_DI      D0, D1, A0, A1, A2, A3, A6, A7,
    #define LV_T_DO      D9,
    #define LV_SD_SCK    D13
    #define LV_SD_MISO   D12
    #define LV_SD_MOSI   D11
    #define LV_SD_CS     D10
  #else
    #define LV_T_DI      D0, D1, A0, A1, A2, A3, A6, A7, D10, D11,
    #define LV_T_DO      D9, D12, D13,
  #endif

#elif defined(ARDUINO_AVR_UNO)
  #define LV_ARCH_AVR    1
  #define LV_ARCH_NAME   "AVR"
  #define LV_BOARD_NAME  "UNO"

  #define LV_T_DI        2, 4, 7, A0, A1, A2, A3,
  #define LV_T_DO        12, 13,
  #define LV_T_AI        A0, A1, A2, A3,
  #define LV_T_AO
  #define LV_T_PWM       3, 5, 11,
  #define LV_T_SERVO     9, 10,
  #define LV_T_NEO       6, 8,

#elif defined(ARDUINO_AVR_NANO)
  #define LV_ARCH_AVR    1
  #define LV_ARCH_NAME   "AVR"
  #define LV_BOARD_NAME  "NANO"

  #define LV_T_DI        2, 4, 7, A0, A1, A2, A3,
  #define LV_T_DO        12, 13,
  #define LV_T_AI        A0, A1, A2, A3, A6, A7,
  #define LV_T_AO
  #define LV_T_PWM       3, 5, 11,
  #define LV_T_SERVO     9, 10,
  #define LV_T_NEO       6, 8,

#elif defined(ARDUINO_NUCLEO_F303K8)
  #define LV_ARCH_STM32  1
  #define LV_ARCH_NAME   "STM32"
  #define LV_BOARD_NAME  "K8"

  #define LV_T_DI        PA10, PA9, PA0, PA1, PA3, PA7,
  #define LV_T_DO        PB3,
  #define LV_T_AI        PA0, PA1, PA3, PA7,
  #define LV_T_AO        PA4,
  #define LV_T_PWM       PA8, PA11, PB1,
  #define LV_T_SERVO     PB5, PB4,
  #define LV_T_NEO       PB0, PA12,

#else
  #error "Tarjeta no soportada por LV_ESP32 v3. Agrega su tabla en lv_boards.h."
#endif

#ifdef LV_ONLINE
  #if !defined(LV_ARCH_ESP32)
    #error "LV_ONLINE solo existe para ESP32 (ESP32-U y Nano ESP32)."
  #endif
  #define LV_VARIANT LV_ARCH_NAME "-ONLINE"
#else
  #define LV_VARIANT LV_ARCH_NAME
#endif

#endif
