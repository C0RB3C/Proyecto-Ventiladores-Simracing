// Firmware ESP32: recibe por WiFi/UDP un duty cycle (0-100%) y lo aplica
// como PWM de 25kHz al cable de control de un ventilador de PC de 4 pines.
//
// Protocolo UDP esperado (texto ASCII): "P075\n" -> duty = 75%
//
// Fail-safe: si no llega ningun paquete valido durante FAILSAFE_TIMEOUT_MS,
// el ventilador se lleva a duty 0 automaticamente.

#include <Arduino.h>
#include <WiFi.h>
#include <WiFiUdp.h>

#include "config.h"

WiFiUDP udp;
unsigned long lastPacketMillis = 0;
int currentDutyPercent = 0;
bool failsafeActive = false;

void connectWiFi() {
  Serial.printf("Conectando a WiFi \"%s\"...\n", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println();
  Serial.print("WiFi conectado. IP: ");
  Serial.println(WiFi.localIP());
}

void applyDutyPercent(int dutyPercent) {
  dutyPercent = constrain(dutyPercent, 0, 100);
  currentDutyPercent = dutyPercent;
  int maxDutyValue = (1 << FAN_PWM_RESOLUTION_BITS) - 1;
  int dutyValue = map(dutyPercent, 0, 100, 0, maxDutyValue);
  ledcWrite(FAN_PWM_CHANNEL, dutyValue);
}

// Parsea un paquete "Pxxx" y devuelve el duty (0-100), o -1 si no es valido.
int parseDutyPacket(const char *buf, int len) {
  if (len < 2 || buf[0] != 'P') {
    return -1;
  }
  int value = 0;
  int digits = 0;
  for (int i = 1; i < len && isDigit(buf[i]); i++) {
    value = value * 10 + (buf[i] - '0');
    digits++;
  }
  if (digits == 0) {
    return -1;
  }
  return constrain(value, 0, 100);
}

void setup() {
  Serial.begin(115200);
  delay(200);

  ledcSetup(FAN_PWM_CHANNEL, FAN_PWM_FREQ_HZ, FAN_PWM_RESOLUTION_BITS);
  ledcAttachPin(FAN_PWM_PIN, FAN_PWM_CHANNEL);
  applyDutyPercent(0);

  connectWiFi();

  udp.begin(UDP_LISTEN_PORT);
  Serial.printf("Escuchando UDP en puerto %d\n", UDP_LISTEN_PORT);

  lastPacketMillis = millis();
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi desconectado, reintentando...");
    connectWiFi();
    udp.begin(UDP_LISTEN_PORT);
  }

  int packetSize = udp.parsePacket();
  if (packetSize > 0) {
    char buf[16];
    int len = udp.read(buf, sizeof(buf) - 1);
    if (len > 0) {
      buf[len] = '\0';
      int duty = parseDutyPacket(buf, len);
      if (duty >= 0) {
        applyDutyPercent(duty);
        lastPacketMillis = millis();
        if (failsafeActive) {
          failsafeActive = false;
          Serial.println("Fail-safe desactivado, recibiendo datos de nuevo.");
        }
      }
    }
  }

  if (!failsafeActive && (millis() - lastPacketMillis > FAILSAFE_TIMEOUT_MS)) {
    Serial.println("Fail-safe: sin datos del PC, parando ventilador.");
    applyDutyPercent(0);
    failsafeActive = true;
  }
}
