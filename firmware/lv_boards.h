/*
 * ===========================================================================
 * lv_boards.h — LV_ESP32 v3
 * ---------------------------------------------------------------------------
 * UNICO lugar donde se definen los pines. Todo lo demas (HAL, protocolo,
 * LabVIEW, tablas en PINOUT.md) sale de aqui.
 *
 * Modelo tipo PLC: LabVIEW NO manda numeros de GPIO, manda el NUMERO DE CANAL
 * de cada tipo. Cada canal tiene un rol fijo en cada tarjeta:
 *
 *      DI   entrada digital      DO   salida digital
 *      AI   entrada analogica    AO   salida analogica (DAC real)
 *      PWM  PWM 1 kHz / 8 bits   SERVO  servo 50 Hz (0..180 grados)
 *      NEO  2 opciones de pin para la tira NeoPixel (una activa a la vez)
 *
 * El canal 0 de cada tipo es el primero de la lista. Un canal fuera de rango
 * responde 'X','X' (y -2 en AI).
 *
 * Cada macro LV_T_xxx es una lista de pines CON COMA AL FINAL (asi puede estar
 * vacia, p. ej. AO en Arduino Uno).
 *
 * Los pines que dependen de la variante (base / ONLINE) van AL FINAL de DI y
 * DO, para que los numeros de canal de los demas no cambien entre variantes.
 * ===========================================================================
 */
#ifndef LV_BOARDS_H
#define LV_BOARDS_H

#include <Arduino.h>

/* ==========================================================================
 * ESP32 clasica — placa de la U (WROVER-IE sobre base DevKitC v4)
 * ========================================================================== */
#if defined(ARDUINO_ARCH_ESP32) && defined(CONFIG_IDF_TARGET_ESP32)
  #define LV_ARCH_ESP32  1
  #define LV_ARCH_NAME   "ESP32"
  #define LV_BOARD_NAME  "ESP32-U"

  /* AI: todos ADC1 (ADC2 se cae cuando se prende el WiFi) */
  #define LV_T_AI        36, 39, 34, 35, 32, 33,
  #define LV_T_AI_ADC2   0, 0, 0, 0, 0, 0,
  #define LV_T_AO        26,                         /* DAC1; el 25 es NeoPixel */
  #define LV_T_PWM       4, 12,                      /* LEDC 0-1 */
  #define LV_T_SERVO     13, 14,                     /* LEDC 4-5 */
  #define LV_T_NEO       25, 27,                     /* opcion 0 = 25 (defecto) */
  #ifdef LV_ONLINE
    #define LV_T_DI      0, 15, 36, 39, 34, 35, 32, 33,
    #define LV_T_DO      2,
    #define LV_SD_SCK    18                          /* VSPI nativo */
    #define LV_SD_MISO   19
    #define LV_SD_MOSI   23
    #define LV_SD_CS     5
  #else
    #define LV_T_DI      0, 15, 36, 39, 34, 35, 32, 33, 5, 18,
    #define LV_T_DO      2, 19, 23,
  #endif
  /* I2C del LCD: SDA 21, SCL 22 (Wire por defecto) */

/* ==========================================================================
 * Arduino Nano ESP32 (ESP32-S3)
 * ========================================================================== */
#elif defined(ARDUINO_NANO_ESP32)
  #define LV_ARCH_ESP32  1
  #define LV_ARCH_NAME   "ESP32"
  #define LV_BOARD_NAME  "NANO-ESP32"

  #define LV_T_AI        A0, A1, A2, A3, A6, A7,
  #define LV_T_AI_ADC2   0,  0,  0,  0,  1,  1,     /* A6/A7 = ADC2: -1 con WiFi */
  #define LV_T_AO                                    /* sin DAC */
  #define LV_T_PWM       D4, D5, D6,                 /* LEDC 0-2 */
  #define LV_T_SERVO     D7, D8,                     /* LEDC 4-5 */
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
  /* I2C del LCD: A4 (SDA), A5 (SCL) */

/* ==========================================================================
 * Arduino Uno
 * ========================================================================== */
#elif defined(ARDUINO_AVR_UNO)
  #define LV_ARCH_AVR    1
  #define LV_ARCH_NAME   "AVR"
  #define LV_BOARD_NAME  "UNO"

  #define LV_T_DI        2, 4, 7, A0, A1, A2, A3,
  #define LV_T_DO        12, 13,
  #define LV_T_AI        A0, A1, A2, A3,
  #define LV_T_AO                                    /* sin DAC */
  #define LV_T_PWM       3, 5, 11,
  #define LV_T_SERVO     9, 10,                      /* Servo.h usa Timer1 */
  #define LV_T_NEO       6, 8,
  /* I2C del LCD: A4 (SDA), A5 (SCL). D0/D1 = USB. */

/* ==========================================================================
 * Arduino Nano (ATmega328P)
 * ========================================================================== */
#elif defined(ARDUINO_AVR_NANO)
  #define LV_ARCH_AVR    1
  #define LV_ARCH_NAME   "AVR"
  #define LV_BOARD_NAME  "NANO"

  #define LV_T_DI        2, 4, 7, A0, A1, A2, A3,    /* A6/A7 no son digitales */
  #define LV_T_DO        12, 13,
  #define LV_T_AI        A0, A1, A2, A3, A6, A7,
  #define LV_T_AO
  #define LV_T_PWM       3, 5, 11,
  #define LV_T_SERVO     9, 10,
  #define LV_T_NEO       6, 8,

/* ==========================================================================
 * Nucleo F303K8
 * ========================================================================== */
#elif defined(ARDUINO_NUCLEO_F303K8)
  #define LV_ARCH_STM32  1
  #define LV_ARCH_NAME   "STM32"
  #define LV_BOARD_NAME  "K8"

  #define LV_T_DI        PA10, PA9, PA0, PA1, PA3, PA7,
  #define LV_T_DO        PB3,
  #define LV_T_AI        PA0, PA1, PA3, PA7,
  #define LV_T_AO        PA4,                        /* DAC1 (pide HAL_DAC_MODULE_ENABLED) */
  #define LV_T_PWM       PA8, PA11, PB1,
  #define LV_T_SERVO     PB5, PB4,
  #define LV_T_NEO       PB0, PA12,                  /* D3 (defecto), D2 */
  /* I2C del LCD: PB7 (SDA), PB6 (SCL).
     Reservados: PA2/PA15 (VCP), PA13/PA14 (SWD), PA5/PA6 (unidos a I2C por SB),
     PF0/PF1 (reloj ST-Link). */

#else
  #error "Tarjeta no soportada por LV_ESP32 v3. Agrega su tabla en lv_boards.h."
#endif

/* ---- Variantes -------------------------------------------------------- */
#ifdef LV_ONLINE
  #if !defined(LV_ARCH_ESP32)
    #error "LV_ONLINE solo existe para ESP32 (ESP32-U y Nano ESP32)."
  #endif
  #define LV_VARIANT LV_ARCH_NAME "-ONLINE"
#else
  #define LV_VARIANT LV_ARCH_NAME
#endif

#endif /* LV_BOARDS_H */
