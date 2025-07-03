#include <WiFi.h>
#include <PubSubClient.h>
#include <Adafruit_NeoPixel.h>

#define MAX_PINS 40
bool pinConfigured[MAX_PINS] = {false};

#define PIN_NEOPIXEL 25
#define NUM_PIXELS 3
Adafruit_NeoPixel pixels(NUM_PIXELS, PIN_NEOPIXEL, NEO_GRB + NEO_KHZ800);

// Cambia aquí tus credenciales WiFi
const char* ssid = "CLARO1_8383C6";
const char* password = "021S4WVSGC";

// Config MQTT
WiFiClient espClient;
PubSubClient client(espClient);

bool wifiDisponible = false;

void setup() {
  Serial.begin(115200);
  delay(1000);

  // Verifica si el usuario quiere conexión WiFi (no empieza con "%%" y no está vacío)
  if (!String(ssid).startsWith("%%") && String(ssid).length() > 0) {
    Serial.print("Conectando a WiFi: ");
    Serial.println(ssid);

    WiFi.begin(ssid, password);

    int intentos = 0;
    while (WiFi.status() != WL_CONNECTED && intentos < 20) {
      delay(500);
      Serial.print(".");
      intentos++;
    }

    if (WiFi.status() == WL_CONNECTED) {
      Serial.println("\nWiFi conectado.");
      Serial.print("IP local: ");
      Serial.println(WiFi.localIP());
      wifiDisponible = true;
    } else {
      Serial.println("\nNo se pudo conectar a WiFi. Modo local.");
    }
  } else {
    Serial.println("Modo sin WiFi. Solo comandos por USB/Serial.");
  }

  pixels.begin();
  pixels.show();
  Serial.println("ESP32 listo.");
}

void loop() {
  if (Serial.available()) {
    String input = Serial.readStringUntil('\n');
    input.trim();

    Serial.print("Input recibido: '");
    Serial.print(input);
    Serial.println("'");

    if (input.length() < 2) {
      Serial.println("ERROR: Comando muy corto.");
      return;
    }

    char tipo = input.charAt(0);
    String data = input.substring(1);
    data.trim();

    // Si el primer caracter de data es '|', eliminarlo para no arruinar el parseo
    if (data.length() > 0 && data.charAt(0) == '|') {
      data = data.substring(1);
      data.trim();
    }

    Serial.print("Tipo: ");
    Serial.println(tipo);
    Serial.print("Data: '");
    Serial.print(data);
    Serial.println("'");

    // ----------- Tipo 1: Digital Write (1ppv) -----------
    if (tipo == '1') {
      if (data.length() != 3) {
        Serial.println("ERROR: Formato digital invalido.");
        return;
      }

      int pin = data.substring(0, 2).toInt();
      int val = data.charAt(2) - '0';

      if (pin < 4 || pin >= MAX_PINS) {
        Serial.println("ERROR: Pin invalido o reservado.");
        return;
      }

      if (!pinConfigured[pin]) {
        pinMode(pin, OUTPUT);
        pinConfigured[pin] = true;
      }

      digitalWrite(pin, val == 1 ? HIGH : LOW);
      Serial.printf("Pin %d <- %s\n", pin, val == 1 ? "HIGH" : "LOW");
    }

    // ----------- Tipo 2: NeoPixel (2<decimalColor>) -----------
    else if (tipo == '2') {
      unsigned long color = strtoul(data.c_str(), NULL, 10);

      uint8_t blue  = (color >> 0) & 0xFF;
      uint8_t green = (color >> 8) & 0xFF;
      uint8_t red   = (color >> 16) & 0xFF;

      for (int i = 0; i < NUM_PIXELS; i++) {
        pixels.setPixelColor(i, pixels.Color(red, green, blue));
      }
      pixels.show();

      Serial.printf("NeoPixel: R=%d G=%d B=%d\n", red, green, blue);
    }

    // ----------- Tipo 3: MQTT publish (3|ip|topic|mensaje) -----------
    else if (tipo == '3') {
      if (!wifiDisponible) {
        Serial.println("ERROR: No hay WiFi, MQTT no disponible.");
        return;
      }

      int pos1 = data.indexOf('|');
      int pos2 = data.indexOf('|', pos1 + 1);

      if (pos1 < 0 || pos2 < 0) {
        Serial.println("ERROR: Formato MQTT invalido.");
        return;
      }

      String brokerIP = data.substring(0, pos1);
      String topic    = data.substring(pos1 + 1, pos2);
      String message  = data.substring(pos2 + 1);

      brokerIP.trim();
      topic.trim();
      message.trim();

      Serial.print("IP recibida: ");
      Serial.println(brokerIP);
      Serial.print("Topic recibido: ");
      Serial.println(topic);
      Serial.print("Mensaje recibido: ");
      Serial.println(message);

      IPAddress mqttServer;
      if (!mqttServer.fromString(brokerIP)) {
        Serial.println("ERROR: IP de broker invalida.");
        return;
      }

      client.setServer(mqttServer, 1883);

      if (!client.connected()) {
        String clientId = "ESP32_" + String(random(0xffff), HEX);
        if (!client.connect(clientId.c_str())) {
          Serial.println("ERROR: No se pudo conectar al broker MQTT.");
          return;
        }
      }

      if (client.publish(topic.c_str(), message.c_str())) {
        Serial.printf("MQTT publicado: [%s] -> %s\n", topic.c_str(), message.c_str());
      } else {
        Serial.println("ERROR: En MQTT.");
      }
    }

    else {
      Serial.println("ERROR: Tipo de comando desconocido.");
    }
  }
}
