#include "lv_gen.h"
#include "lv_hal.h"
#include "lv_boards.h"

// Frecuencia de actualizacion del DAC (muestras por segundo). Se puede
// sobreescribir con -DLV_GEN_FS=... y hay que medir el limite real en la placa.
#ifndef LV_GEN_FS
  #define LV_GEN_FS 20000UL
#endif
// Minimo de muestras por periodo: define la frecuencia maxima (fs / 10).
#define LV_GEN_MIN_PTS 10UL
#define LV_GEN_FMAX_MHZ ((LV_GEN_FS * 1000UL) / LV_GEN_MIN_PTS)

#define TIMEOUT_MS 200

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

#if defined(LV_ARCH_ESP32) && defined(CONFIG_IDF_TARGET_ESP32)
  #define LV_GEN_HW 1
#endif

#ifdef LV_GEN_HW

static const int16_t T_AO[] = { LV_T_AO -1 };

enum GenShape : uint8_t { GEN_SINE = 0, GEN_TRI, GEN_SQUARE, GEN_SAW, GEN_NSHAPES };

// Estado del generador. ph es el acumulador de fase de 32 bits y dph su paso
// por muestra, asi que f_real = dph * fs / 2^32.
static struct {
  volatile bool     on;
  volatile uint8_t  shape;
  volatile uint8_t  pin;
  volatile uint32_t ph;
  volatile uint32_t dph;
  volatile int32_t  amp;   // pico a pico, cuentas del DAC
  volatile int32_t  off;   // centro, cuentas del DAC
  volatile uint32_t thr;   // umbral de la cuadrada, de 0 a 65536
} gen;

// Seno en Q15 con 256 tramos (un punto extra para interpolar). Va en RAM
// porque la rutina de interrupcion no puede leer de flash.
static DRAM_ATTR int16_t sinTab[257];
static bool sinReady = false;

static hw_timer_t* tm = nullptr;

static void sinInit() {
  if (sinReady) return;
  for (int i = 0; i <= 256; i++) {
    sinTab[i] = (int16_t)lroundf(32767.0f * sinf(2.0f * (float)PI * i / 256.0f));
  }
  sinReady = true;
}

static void IRAM_ATTR genTick() {
  if (!gen.on) return;
  uint32_t ph = gen.ph;
  gen.ph = ph + gen.dph;
  uint32_t x = ph >> 16;   // fase de 16 bits, 0 a 65535
  int32_t w;               // forma de onda normalizada, -32768 a 32767
  switch (gen.shape) {
    case GEN_SINE: {
      uint32_t i = x >> 8;
      int32_t  fr = (int32_t)(x & 0xFF);
      w = sinTab[i] + ((((int32_t)sinTab[i + 1] - sinTab[i]) * fr) >> 8);
      break;
    }
    case GEN_TRI:
      w = (x < 32768) ? (2 * (int32_t)x - 32768) : (98303 - 2 * (int32_t)x);
      break;
    case GEN_SQUARE:
      w = (x < gen.thr) ? 32767 : -32768;
      break;
    default:
      w = (int32_t)x - 32768;
      break;
  }
  int32_t v = gen.off + ((gen.amp * w + 32768) >> 16);
  if (v < 0) v = 0; else if (v > 255) v = 255;
  dacWrite(gen.pin, (uint8_t)v);
}

static uint32_t realMilliHz() {
  return (uint32_t)((((uint64_t)gen.dph * LV_GEN_FS * 1000ULL) + (1ULL << 31)) >> 32);
}

static bool genStart(uint8_t ch, uint8_t shape, uint32_t fmhz,
                     uint8_t amp, uint8_t off, uint8_t duty) {
  if (ch >= lv_count(LV_AO) || shape >= GEN_NSHAPES) return false;
  if (fmhz < 1 || fmhz > LV_GEN_FMAX_MHZ) return false;
  if (duty < 1) duty = 1; else if (duty > 99) duty = 99;
  sinInit();
  uint8_t pin = (uint8_t)T_AO[ch];
  const uint64_t den = LV_GEN_FS * 1000ULL;
  uint32_t dph = (uint32_t)((((uint64_t)fmhz << 32) + den / 2) / den);
  if (!gen.on) {
    gen.ph = 0;
    dacWrite(pin, off);   // inicializa el pad del DAC fuera de la interrupcion
  }
  gen.pin   = pin;
  gen.shape = shape;
  gen.amp   = amp;
  gen.off   = off;
  gen.thr   = ((uint32_t)duty * 65536UL) / 100UL;
  gen.dph   = dph;
  if (!tm) {
    tm = timerBegin(1000000);
    if (!tm) return false;
    timerAttachInterrupt(tm, &genTick);
    timerAlarm(tm, 1000000UL / LV_GEN_FS, true, 0);
  }
  gen.on = true;
  return true;
}

static void genStop(uint8_t ch) {
  gen.on = false;
  if (tm) { timerEnd(tm); tm = nullptr; }
  dacWrite((uint8_t)T_AO[ch], 0);
}

#endif  // LV_GEN_HW

bool lv_genHandle(uint8_t cmd) {
  uint8_t p[9];
  switch (cmd) {

    case 0xD0: {
      if (!readBytes(p, 9)) { nack(); return true; }
#ifdef LV_GEN_HW
      uint32_t fmhz = ((uint32_t)p[2] << 24) | ((uint32_t)p[3] << 16) |
                      ((uint32_t)p[4] << 8)  |  (uint32_t)p[5];
      if (genStart(p[0], p[1], fmhz, p[6], p[7], p[8])) ack(); else nack();
#else
      nack();
#endif
      return true;
    }

    case 0xD1: {
      if (!readBytes(p, 1)) { nack(); return true; }
#ifdef LV_GEN_HW
      if (p[0] < lv_count(LV_AO)) { genStop(p[0]); ack(); } else nack();
#else
      nack();
#endif
      return true;
    }

    case 0xD2: {
      if (!readBytes(p, 1)) { Serial.println(-2); return true; }
#ifdef LV_GEN_HW
      if (p[0] >= lv_count(LV_AO)) { Serial.println(-2); return true; }
      // activo,forma,mHz reales,fs,mHz maximos
      Serial.print(gen.on ? 1 : 0);        Serial.print(',');
      Serial.print(gen.shape);             Serial.print(',');
      Serial.print(gen.on ? realMilliHz() : 0UL); Serial.print(',');
      Serial.print(LV_GEN_FS);             Serial.print(',');
      Serial.println(LV_GEN_FMAX_MHZ);
#else
      Serial.println(-2);
#endif
      return true;
    }

    default:
      return false;
  }
}
