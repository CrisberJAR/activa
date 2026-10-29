/*
  ACTIVA – Sensor de clima (ESP32 + DHT22) simulado en Wokwi.
  Lee temperatura y humedad y las envía a Firebase Realtime Database.
  Para cuidar el plan gratuito, se detiene solo tras MAX_ENVIOS envíos.
*/
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include "DHTesp.h"

// ===== Configuración (cambiar aquí) =====
const char* FIREBASE_URL = "https://activa-729e7-default-rtdb.firebaseio.com";
const char* SENSOR_ID    = "sensor-agricola-01";  // identificador único del sensor
const char* SECTOR       = "agricola";            // agricola | comerciante | ambulante | taxista
const unsigned long INTERVALO_MS = 30000;         // un envío cada 30 segundos
const int MAX_ENVIOS = 20;                        // 20 x 30 s = 10 minutos y se detiene

const int PIN_DHT = 15;
const int PIN_LED = 4;                            // parpadea en cada envío

DHTesp dht;
int envios = 0;
unsigned long ultimoEnvio = 0;

void conectarWiFi() {
  Serial.print("Conectando a Wokwi-GUEST");
  WiFi.begin("Wokwi-GUEST", "", 6);
  while (WiFi.status() != WL_CONNECTED) {
    delay(250);
    Serial.print(".");
  }
  Serial.println(" conectado");
}

// Envía un JSON a Firebase por HTTPS. metodo: "POST" (agrega) o "PUT" (reemplaza)
bool enviar(const String& ruta, const char* metodo, const String& json) {
  WiFiClientSecure cliente;
  cliente.setInsecure();  // simulación: sin verificar certificado
  HTTPClient http;
  http.begin(cliente, String(FIREBASE_URL) + ruta + ".json");
  http.addHeader("Content-Type", "application/json");
  int codigo = http.sendRequest(metodo, json);
  http.end();
  return codigo == 200;
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_LED, OUTPUT);
  dht.setup(PIN_DHT, DHTesp::DHT22);
  conectarWiFi();
  Serial.printf("Sensor %s (%s): %d envíos, uno cada %lu s\n", SENSOR_ID, SECTOR, MAX_ENVIOS, INTERVALO_MS / 1000);
}

void loop() {
  if (envios >= MAX_ENVIOS) {  // demo terminada: no envía nada más
    delay(1000);
    return;
  }
  if (ultimoEnvio != 0 && millis() - ultimoEnvio < INTERVALO_MS) {
    delay(100);
    return;
  }
  ultimoEnvio = millis();

  TempAndHumidity d = dht.getTempAndHumidity();
  if (isnan(d.temperature) || isnan(d.humidity)) {
    Serial.println("Error leyendo el DHT22");
    return;
  }
  if (WiFi.status() != WL_CONNECTED) conectarWiFi();

  // "ts" lo completa el servidor de Firebase con su hora actual
  String json = "{\"temperatura\":" + String(d.temperature, 1) +
                ",\"humedad\":" + String(d.humidity, 1) +
                ",\"sector\":\"" + SECTOR + "\"" +
                ",\"ts\":{\".sv\":\"timestamp\"}}";

  digitalWrite(PIN_LED, HIGH);
  bool ok = enviar(String("/lecturas/") + SENSOR_ID, "POST", json) &&
            enviar(String("/ultima/") + SENSOR_ID, "PUT", json);
  digitalWrite(PIN_LED, LOW);

  envios++;
  Serial.printf("[%d/%d] T=%.1f C  H=%.1f %%  -> %s\n", envios, MAX_ENVIOS, d.temperature, d.humidity,
                ok ? "OK" : "ERROR");

  if (envios >= MAX_ENVIOS) {
    Serial.println("Demo terminada: se alcanzó el límite de envíos. Reinicia la simulación para enviar más.");
    WiFi.disconnect(true);
  }
}
