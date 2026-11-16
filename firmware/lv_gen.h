#ifndef LV_GEN_H
#define LV_GEN_H

#include <Arduino.h>

// Generador de funciones sobre el DAC. Comandos externos D0, D1 y D2.
//   D0 canal forma f3 f2 f1 f0 amp off duty   -> 'AA' o 'XX'
//   D1 canal                                  -> 'AA' o 'XX'
//   D2 canal                                  -> linea de texto
// cmd es el byte de comando que ya leyo el protocolo. Devuelve true si el
// comando es del generador (lo atiende y responde) y false si no lo es.
bool lv_genHandle(uint8_t cmd);

#endif
