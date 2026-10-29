# Sensor IoT en Wokwi (ESP32 + DHT22 → Firebase)

## Circuito

- ESP32 DevKit C v4
- DHT22: VCC → 3V3, GND → GND, SDA (datos) → **GPIO 15**
- LED verde con resistencia de 220 Ω en GPIO 4 (parpadea en cada envío)

El ESP32 se conecta a la red `Wokwi-GUEST`, lee el sensor cada 30 s y envía la lectura a Firebase.
**Se detiene solo tras 20 envíos (10 minutos)** para no gastar el plan gratuito. Para enviar más, reinicia la simulación.

## Montarlo en Wokwi

1. Entra a https://wokwi.com e inicia sesión.
2. Pulsa **New Project** → **ESP32** (plantilla Arduino).
3. Pestaña `sketch.ino`: borra todo y pega el contenido de `iot/sketch.ino`.
4. Pestaña `diagram.json`: borra todo y pega el contenido de `iot/diagram.json`.
5. Agrega la librería: pestaña **Library Manager** → **+** → busca `DHT sensor library for ESPx` → agrégala
   (equivale al archivo `libraries.txt`).
6. Pulsa **Save** (ponle de nombre "ACTIVA sensor agricola") y luego **▶ Start**.
7. En el monitor serie verás: `[1/20] T=18.5 C  H=70.0 %  -> OK`.

Mientras simula, haz clic en el DHT22 y mueve los controles de temperatura y humedad: el siguiente envío llevará los valores nuevos.

## Simular otro sensor

Cambia estas dos líneas al inicio del sketch y guarda como otro proyecto:

```cpp
const char* SENSOR_ID = "sensor-mercado-01";
const char* SECTOR    = "comerciante";   // agricola | comerciante | ambulante | taxista
```

## Estructura en Firebase

```
lecturas/<sensor_id>/<id automático>: { temperatura, humedad, sector, ts }
ultima/<sensor_id>:                   { temperatura, humedad, sector, ts }
```

`ts` lo pone el servidor de Firebase (milisegundos desde 1970).

## Comprobar desde el backend

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m scripts.ver_firebase
```
