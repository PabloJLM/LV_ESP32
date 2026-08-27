/*
 * ===========================================================================
 * lv_hal.h — LV_ESP32
 * ---------------------------------------------------------------------------
 * Capa de abstraccion de hardware.
 *
 * El PROTOCOLO no vive aqui: vive una sola vez en firmware.ino y es IDENTICO
 * para todas las tarjetas. Aqui solo se resuelve "como se hace esto en esta
 * arquitectura". Asi los VIs de LabVIEW no cambian nunca.
 *
 * La arquitectura se detecta sola desde el FQBN que le pasas a arduino-cli:
 *   esp32:esp32:esp32     -> ARDUINO_ARCH_ESP32
 *   arduino:avr:uno       -> ARDUINO_ARCH_AVR
 *   STMicroelectronics:.. -> ARDUINO_ARCH_STM32
 *
 * Variante ESP-NOW: se activa compilando con -DLV_ESPNOW (solo ESP32).
 * ===========================================================================
 */
#ifndef LV_HAL_H
#define LV_HAL_H

#include <Arduino.h>

#define LV_VERSION "2.1.0"

/* ==========================================================================
 * 1. Deteccion de arquitectura
 * ========================================================================== */
#if defined(ARDUINO_ARCH_ESP32)
  #define LV_ARCH_ESP32 1
  #define LV_ARCH_NAME  "ESP32"
  #include <ESP32Servo.h>
  #include "soc/soc_caps.h"
  #if defined(SOC_DAC_SUPPORTED) && SOC_DAC_SUPPORTED
    #define LV_HAS_DAC 1
  #else
    #define LV_HAS_DAC 0
  #endif
  #ifndef LV_NEOPIXEL_PIN
    #define LV_NEOPIXEL_PIN 25        /* igual que v2: no cambia el cableado */
  #endif
  #ifndef LV_DAC_PIN
    #define LV_DAC_PIN      26
  #endif

#elif defined(ARDUINO_ARCH_AVR)
  #define LV_ARCH_AVR  1
  #define LV_ARCH_NAME "AVR"
  #include <Servo.h>
  #define LV_HAS_DAC      0           /* las AVR clasicas no tienen DAC */
  #ifndef LV_NEOPIXEL_PIN
    #define LV_NEOPIXEL_PIN 6
  #endif
  #define LV_DAC_PIN      255
  #ifdef LV_ESPNOW
    #error "LV_ESPNOW no existe para Arduino AVR: no tiene radio."
  #endif

#elif defined(ARDUINO_ARCH_STM32)
  #define LV_ARCH_STM32 1
  #define LV_ARCH_NAME  "STM32"
  #include <Servo.h>
  #define LV_HAS_DAC      1           /* la mayoria de F1/F4 tienen DAC en PA4 */
  #define LV_NEOPIXEL_PIN PB0
  #define LV_DAC_PIN      PA4
  #ifdef LV_ESPNOW
    #error "LV_ESPNOW no aplica a STM32 en esta version."
  #endif

#else
  #error "Arquitectura no soportada por LV_ESP32. Revisa el FQBN."
#endif

/* Nombre de la variante, lo devuelve el comando 0xEF */
#if defined(LV_ESPNOW)
  #define LV_VARIANT LV_ARCH_NAME "-ESPNOW"
#else
  #define LV_VARIANT LV_ARCH_NAME
#endif

/* ==========================================================================
 * 2. Servo (misma libreria conceptual, distinto header por arquitectura)
 * ========================================================================== */
static Servo  lv_servoObj;
static int8_t lv_servoPin = -1;

static void lv_servo(uint8_t pin, uint8_t angulo) {
  if (angulo > 210) angulo = 210;
  if (lv_servoPin != (int8_t)pin) {
    if (lv_servoObj.attached()) lv_servoObj.detach();
#if defined(LV_ARCH_ESP32)
    lv_servoObj.attach(pin, 500, 2400);
#else
    lv_servoObj.attach(pin, 500, 2400);
#endif
    lv_servoPin = (int8_t)pin;
  }
  lv_servoObj.write(angulo);
}

/* ==========================================================================
 * 3. Digital
 * ========================================================================== */
static inline void lv_pinOutput(uint8_t pin) { pinMode(pin, OUTPUT); }
static inline void lv_pinInput(uint8_t pin)  { pinMode(pin, INPUT);  }
static inline void lv_write(uint8_t pin, uint8_t v) { digitalWrite(pin, v ? HIGH : LOW); }
static inline uint8_t lv_read(uint8_t pin)   { return digitalRead(pin) ? 1 : 0; }

/* ==========================================================================
 * 4. ADC — SIEMPRE devuelve 0..4095, sea cual sea la tarjeta
 *
 * Es la pieza clave para que los VIs no cambien: en AVR el ADC es de 10 bits
 * (0..1023) y se escala aqui, no en LabVIEW. Un panel calibrado para una
 * ESP32 muestra lo mismo conectado a un UNO.
 * ========================================================================== */
static void lv_adcBegin() {
#if defined(LV_ARCH_ESP32)
  analogReadResolution(12);
#endif
}

/* -1 significa "este pin no puede leerse ahora" (ADC2 con el radio on) */
static int16_t lv_adc(uint8_t pin) {
#if defined(LV_ARCH_ESP32)
  #if defined(LV_ESPNOW)
    /* Con el radio encendido el ADC2 entrega basura SIN avisar. Preferimos
       devolver un error visible antes que un numero inventado. */
    extern bool lv_radioActive();
    switch (pin) {
      case 0: case 2: case 4: case 12: case 13:
      case 14: case 15: case 25: case 26: case 27:
        if (lv_radioActive()) return -1;
      default: break;
    }
  #endif
  for (uint8_t i = 0; i < 8; i++) analogRead(pin);   /* descarta transitorios */
  return (int16_t)analogRead(pin);

#elif defined(LV_ARCH_AVR)
  (void)analogRead(pin);
  uint16_t v = (uint16_t)analogRead(pin);            /* 10 bits: 0..1023 */
  return (int16_t)(((uint32_t)v * 4095u) / 1023u);   /* escala exacta a 12 bits */

#else
  analogReadResolution(12);
  (void)analogRead(pin);
  return (int16_t)analogRead(pin);
#endif
}

/* ==========================================================================
 * 5. DAC — devuelve false si esta tarjeta no puede
 * ========================================================================== */
static bool lv_dac(uint8_t pin, uint8_t val) {
#if LV_HAS_DAC && defined(LV_ARCH_ESP32)
  if (pin != LV_DAC_PIN) return false;   /* 25 sigue reservado al NeoPixel */
  dacWrite(pin, val);                    /* DAC real, no PWM */
  return true;
#elif LV_HAS_DAC && defined(LV_ARCH_STM32)
  if (pin != LV_DAC_PIN) return false;
  analogWrite(pin, val);
  return true;
#else
  (void)pin; (void)val;
  return false;                          /* AVR: responde 'X','X' */
#endif
}

/* ==========================================================================
 * 6. PWM — 8 bits (0..255) en todas, igual que v2
 * ========================================================================== */
#if defined(LV_ARCH_ESP32)
static uint8_t lv_ledcCh[40];
static uint8_t lv_nextCh = 0;
#endif

static void lv_pwmBegin() {
#if defined(LV_ARCH_ESP32)
  memset(lv_ledcCh, 0xFF, sizeof(lv_ledcCh));
#endif
}

static void lv_pwm(uint8_t pin, uint8_t duty) {
#if defined(LV_ARCH_ESP32)
  if (pin < 40 && lv_ledcCh[pin] == 0xFF) {
    uint8_t ch = (lv_nextCh++) % 8;
    ledcAttachChannel(pin, 1000, 8, ch);
    lv_ledcCh[pin] = ch;
  }
  ledcWrite(pin, duty);
#else
  pinMode(pin, OUTPUT);
  analogWrite(pin, duty);
#endif
}

/* ==========================================================================
 * 7. Arranque comun
 * ========================================================================== */
static void lv_halBegin() {
  lv_adcBegin();
  lv_pwmBegin();
}

#endif /* LV_HAL_H */
