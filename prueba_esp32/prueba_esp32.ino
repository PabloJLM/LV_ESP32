#define MAX_PINS 40
bool pinConfigured[MAX_PINS] = {false};

void setup() {
  Serial.begin(115200);
  Serial.println("ESP32 listo.");
}

void loop() {
  if (Serial.available()) {
    String input = Serial.readStringUntil('\n');  // Lee hasta \n (LabVIEW debe enviarlo)
    input.trim();

    int cmd = input.toInt();

    int tipo = cmd / 1000;
    int pin  = (cmd / 10) % 100;
    int val  = cmd % 10;

    if (tipo == 1) {
      if (pin >= 0 && pin < MAX_PINS) {
        if (!pinConfigured[pin]) {
          pinMode(pin, OUTPUT);
          pinConfigured[pin] = true;
        }
        digitalWrite(pin, val == 1 ? HIGH : LOW);
          Serial.print("Recibido: ");  // <-- Esto imprime lo que se recibe
          Serial.println(input);

      } else {
        Serial.println("ERROR: Pin inválido.");
      }
    } else {
      Serial.println("ERROR: Comando desconocido.");
    }
  }
}
