/*
 * lv_hal.cpp — LV_ESP32 v3
 * Implementacion de los canales logicos. Los pines salen de lv_boards.h.
 */
#include "lv_hal.h"
#include "lv_boards.h"
#include <Adafruit_NeoPixel.h>

#if !defined(LV_ARCH_ESP32)
  #include <Servo.h>
#endif
#ifdef LV_ONLINE
  #include "lv_online.h"
#endif

/* --- tablas (el -1 final es centinela: permite listas vacias) -------------- */
static const int16_t T_DI[]  = { LV_T_DI    -1 };
static const int16_t T_DO[]  = { LV_T_DO    -1 };
static const int16_t T_AI[]  = { LV_T_AI    -1 };
static const int16_t T_AO[]  = { LV_T_AO    -1 };
static const int16_t T_PWM[] = { LV_T_PWM   -1 };
static const int16_t T_SV[]  = { LV_T_SERVO -1 };
static const int16_t T_NEO[] = { LV_T_NEO   -1 };
#ifdef LV_ARCH_ESP32
static const uint8_t T_AI_ADC2[] = { LV_T_AI_ADC2 0 };
#endif

#define CNT(a) ((uint8_t)(sizeof(a) / sizeof(a[0]) - 1))
static const uint8_t N_DI = CNT(T_DI),  N_DO  = CNT(T_DO), N_AI = CNT(T_AI);
static const uint8_t N_AO = CNT(T_AO),  N_PWM = CNT(T_PWM);
static const uint8_t N_SV = CNT(T_SV),  N_NEO = CNT(T_NEO);

static_assert(N_PWM <= 4 && N_SV <= 4, "Maximo 4 canales PWM y 4 de servo");
static_assert(N_NEO >= 1, "Cada tarjeta necesita al menos una opcion de NeoPixel");
#ifdef LV_ARCH_ESP32
static_assert(sizeof(T_AI_ADC2) - 1 == sizeof(T_AI) / sizeof(T_AI[0]) - 1,
              "LV_T_AI_ADC2 debe tener un valor por cada canal AI");
#endif

/* ESP32: PWM usa LEDC 0..3 a 1 kHz/8 bits y servo usa LEDC 4..7 a 50 Hz/14 bits.
   Los timers del LEDC se reparten por pares de canal, asi que ambos grupos
   nunca comparten timer (no hay conflicto de frecuencia). */
#ifdef LV_ARCH_ESP32
  #define SERVO_CH0 4
#endif

const char* lv_variant()   { return LV_VARIANT; }
const char* lv_boardName() { return LV_BOARD_NAME; }

uint8_t lv_count(LvType t) {
  switch (t) {
    case LV_DI:    return N_DI;
    case LV_DO:    return N_DO;
    case LV_AI:    return N_AI;
    case LV_AO:    return N_AO;
    case LV_PWM:   return N_PWM;
    case LV_SERVO: return N_SV;
    case LV_NEO:   return N_NEO;
    default:       return 0;
  }
}

/* --- NeoPixel -------------------------------------------------------------- */
static Adafruit_NeoPixel* strip = nullptr;
static uint8_t neoOpt = 0;

static void neoMake(uint8_t opt) {
  strip = new Adafruit_NeoPixel(LV_NUM_PIXELS, T_NEO[opt], NEO_GRB + NEO_KHZ800);
  strip->begin();
  strip->clear();
  strip->show();
  neoOpt = opt;
}

bool lv_neoSelect(uint8_t opt) {
  if (opt >= N_NEO) return false;
  if (strip && opt == neoOpt) return true;
  if (strip) {
    strip->clear();
    strip->show();
    delete strip;                      /* el destructor suelta el pin viejo */
    strip = nullptr;
  }
  neoMake(opt);
  return true;
}

void lv_neoAll(uint8_t r, uint8_t g, uint8_t b) {
  for (uint8_t i = 0; i < LV_NUM_PIXELS; i++) strip->setPixelColor(i, strip->Color(r, g, b));
  strip->show();
}

bool lv_neoOne(uint8_t i, uint8_t r, uint8_t g, uint8_t b) {
  if (i >= LV_NUM_PIXELS) return false;
  strip->setPixelColor(i, strip->Color(r, g, b));
  strip->show();
  return true;
}

/* --- digital ---------------------------------------------------------------- */
bool lv_dWrite(uint8_t ch, uint8_t v) {
  if (ch >= N_DO) return false;
  pinMode(T_DO[ch], OUTPUT);
  digitalWrite(T_DO[ch], v ? HIGH : LOW);
  return true;
}

bool lv_dRead(uint8_t ch, uint8_t* v) {
  if (ch >= N_DI) return false;
  pinMode(T_DI[ch], INPUT);
  *v = digitalRead(T_DI[ch]) ? 1 : 0;
  return true;
}

/* --- analogico: SIEMPRE 0..4095 --------------------------------------------- */
int16_t lv_aRead(uint8_t ch) {
  if (ch >= N_AI) return -2;
  int16_t pin = T_AI[ch];
#if defined(LV_ARCH_ESP32)
  #ifdef LV_ONLINE
  if (T_AI_ADC2[ch] && lv_radioActive()) return -1;   /* ADC2 inservible con WiFi */
  #endif
  for (uint8_t i = 0; i < 8; i++) analogRead(pin);    /* descarta transitorios */
  return (int16_t)analogRead(pin);
#elif defined(LV_ARCH_AVR)
  (void)analogRead(pin);
  uint16_t v = (uint16_t)analogRead(pin);             /* 10 bits */
  return (int16_t)(((uint32_t)v * 4095u) / 1023u);    /* escala exacta a 12 bits */
#else
  (void)analogRead(pin);
  return (int16_t)analogRead(pin);
#endif
}

bool lv_aWrite(uint8_t ch, uint8_t v) {
  if (ch >= N_AO) return false;
#if defined(LV_ARCH_ESP32) && defined(CONFIG_IDF_TARGET_ESP32)
  dacWrite(T_AO[ch], v);                              /* DAC real, no PWM */
  return true;
#elif defined(LV_ARCH_STM32) && defined(HAL_DAC_MODULE_ENABLED)
  analogWrite(T_AO[ch], v);
  return true;
#else
  (void)v;
  return false;
#endif
}

/* --- PWM -------------------------------------------------------------------- */
#ifdef LV_ARCH_ESP32
static bool pwmOn[4];
#endif

bool lv_pwm(uint8_t ch, uint8_t duty) {
  if (ch >= N_PWM) return false;
#ifdef LV_ARCH_ESP32
  if (!pwmOn[ch]) {
    if (!ledcAttachChannel(T_PWM[ch], 1000, 8, ch)) return false;
    pwmOn[ch] = true;
  }
  ledcWrite(T_PWM[ch], duty);
#else
  pinMode(T_PWM[ch], OUTPUT);
  analogWrite(T_PWM[ch], duty);
#endif
  return true;
}

/* --- servo ------------------------------------------------------------------ */
#ifdef LV_ARCH_ESP32
static bool svOn[4];
#else
static Servo svObj[4];
#endif

bool lv_servo(uint8_t ch, uint8_t angle) {
  if (ch >= N_SV) return false;
  if (angle > 180) angle = 180;
#ifdef LV_ARCH_ESP32
  if (!svOn[ch]) {
    if (!ledcAttachChannel(T_SV[ch], 50, 14, SERVO_CH0 + ch)) return false;
    svOn[ch] = true;
  }
  uint32_t us = 500 + (uint32_t)angle * (2400 - 500) / 180;
  ledcWrite(T_SV[ch], us * 16384UL / 20000UL);        /* periodo 20 ms */
#else
  if (!svObj[ch].attached()) svObj[ch].attach(T_SV[ch], 500, 2400);
  svObj[ch].write(angle);
#endif
  return true;
}

/* --- arranque --------------------------------------------------------------- */
void lv_halBegin() {
#if defined(LV_ARCH_ESP32) || defined(LV_ARCH_STM32)
  analogReadResolution(12);
#endif
  neoMake(0);
}
