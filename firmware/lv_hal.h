#ifndef LV_HAL_H
#define LV_HAL_H

#include <Arduino.h>

#define LV_VERSION    "3.0.0"
#define LV_NUM_PIXELS 16

enum LvType : uint8_t { LV_DI = 0, LV_DO, LV_AI, LV_AO, LV_PWM, LV_SERVO, LV_NEO, LV_NTYPES };

const char* lv_variant();
const char* lv_boardName();
uint8_t     lv_count(LvType t);

void    lv_halBegin();

bool    lv_dWrite(uint8_t ch, uint8_t v);
bool    lv_dRead(uint8_t ch, uint8_t* v);
int16_t lv_aRead(uint8_t ch);
bool    lv_aWrite(uint8_t ch, uint8_t v);
bool    lv_pwm(uint8_t ch, uint8_t duty);
bool    lv_servo(uint8_t ch, uint8_t angle);

bool    lv_neoSelect(uint8_t opt);
void    lv_neoAll(uint8_t r, uint8_t g, uint8_t b);
bool    lv_neoOne(uint8_t i, uint8_t r, uint8_t g, uint8_t b);

#endif
