#include <Arduino.h>
#include <WiFi.h>
#include <WiFiUdp.h>

#ifndef TARS_WIFI_SSID
#define TARS_WIFI_SSID "TARS-PICO-BRIDGE"
#endif

#ifndef TARS_WIFI_PASSWORD
#define TARS_WIFI_PASSWORD "tarsbridge"
#endif

#ifndef TARS_UDP_PORT
#define TARS_UDP_PORT 15120
#endif

#ifndef TARS_UART_BAUD
#define TARS_UART_BAUD 115200
#endif

#ifndef TARS_UART_TX_PIN
#define TARS_UART_TX_PIN 4
#endif

#ifndef TARS_UART_RX_PIN
#define TARS_UART_RX_PIN 5
#endif

namespace {

WiFiUDP g_udp;
IPAddress g_lastRemoteIp;
uint16_t g_lastRemotePort = 0;
bool g_hasRemotePeer = false;
char g_uartLine[256] = {0};
size_t g_uartLineLen = 0;

void replyUdp(const char *message) {
  if (!g_hasRemotePeer) {
    return;
  }
  g_udp.beginPacket(g_lastRemoteIp, g_lastRemotePort);
  g_udp.write(reinterpret_cast<const uint8_t *>(message), strlen(message));
  g_udp.endPacket();
}

void handleUdpPacket() {
  const int packetSize = g_udp.parsePacket();
  if (packetSize <= 0) {
    return;
  }

  char packet[256] = {0};
  const int readLen = g_udp.read(packet, sizeof(packet) - 1);
  if (readLen <= 0) {
    return;
  }

  g_lastRemoteIp = g_udp.remoteIP();
  g_lastRemotePort = g_udp.remotePort();
  g_hasRemotePeer = true;

  while (g_udp.available() > 0) {
    g_udp.read();
  }

  for (int i = readLen - 1; i >= 0; --i) {
    if (packet[i] == '\r' || packet[i] == '\n' || packet[i] == ' ') {
      packet[i] = '\0';
    } else {
      break;
    }
  }

  if (strcmp(packet, "PING") == 0) {
    replyUdp("PICO:PONG\n");
    return;
  }

  Serial1.print(packet);
  Serial1.print("\n");
}

void handleUartInput() {
  while (Serial1.available() > 0) {
    const char c = static_cast<char>(Serial1.read());
    if (c == '\r') {
      continue;
    }
    if (c == '\n') {
      g_uartLine[g_uartLineLen] = '\0';
      if (g_uartLineLen > 0) {
        replyUdp(g_uartLine);
        replyUdp("\n");
      }
      g_uartLineLen = 0;
      continue;
    }
    if (g_uartLineLen + 1 < sizeof(g_uartLine)) {
      g_uartLine[g_uartLineLen++] = c;
    } else {
      g_uartLineLen = 0;
    }
  }
}

void waitForWifi() {
  WiFi.mode(WIFI_AP);
  const bool started = WiFi.beginAP(TARS_WIFI_SSID, TARS_WIFI_PASSWORD);
  if (!started) {
    while (true) {
      delay(250);
    }
  }
}

}  // namespace

void setup() {
  Serial.begin(115200);
  delay(500);

  Serial1.setTX(TARS_UART_TX_PIN);
  Serial1.setRX(TARS_UART_RX_PIN);
  Serial1.begin(TARS_UART_BAUD);

  waitForWifi();
  g_udp.begin(TARS_UDP_PORT);

  Serial.println("TARS Pico W UDP/UART bridge ready");
  Serial.print("AP IP: ");
  Serial.println(WiFi.localIP());
}

void loop() {
  handleUdpPacket();
  handleUartInput();
  delay(1);
}
