# esp32-firmware

Firmware para ESP32 (PlatformIO + Arduino framework) que recibe por WiFi/UDP
el duty cycle del ventilador y genera la señal PWM de 25 kHz para un
ventilador de PC de 4 pines.

## Requisitos

- [PlatformIO](https://platformio.org/) (extensión de VS Code o CLI).
- Un ESP32 (dev board genérica, ej. ESP32-DevKitC / NodeMCU-32S) conectado
  por USB.

## Configuración

1. Copia `include/config.h.example` a `include/config.h` (ya hay una copia
   de partida, edítala).
2. Rellena `WIFI_SSID` y `WIFI_PASSWORD` con los de tu red.
3. Ajusta `FAN_PWM_PIN` si conectas el cable PWM del ventilador a otro GPIO
   distinto del 25 (evita GPIO 34-39, son solo entrada).

## Compilar y subir

```powershell
cd esp32-firmware
pio run --target upload
pio device monitor
```

Al arrancar, el ESP32 imprime por el puerto serie la IP que le ha dado tu
router. Usa esa IP en `pc-app/config.ini` (`esp32_ip`). Si tu router lo
permite, resérvale una IP fija (DHCP reservation) por su MAC para que no
cambie entre reinicios.

## Conexionado del ventilador (4 pines)

| Pin ventilador | Conectar a |
|---|---|
| GND (pin 1, negro) | GND común (fuente 12V + GND del ESP32) |
| +12V (pin 2, amarillo) | Fuente de 12V externa |
| Tacómetro (pin 3, verde) | Sin usar en esta versión (libre) |
| PWM control (pin 4, azul) | `FAN_PWM_PIN` del ESP32 (por defecto GPIO 25) |

Importante: el **GND del ESP32 y el GND de la fuente de 12V deben estar
unidos**, aunque las alimentaciones sean independientes (USB para el ESP32,
12V para el ventilador). Sin GND común el PWM no se interpretará bien.

## Comportamiento de seguridad (fail-safe)

Si el ESP32 deja de recibir paquetes UDP válidos durante
`FAILSAFE_TIMEOUT_MS` (3000 ms por defecto), lleva el ventilador a 0% de
duty automáticamente. Esto cubre los casos de: iRacing cerrado, PC apagado,
script de `pc-app` parado, o caída de la red WiFi.

## Protocolo UDP

Texto ASCII, un paquete por actualización:

```
P075\n
```

`P` + 3 dígitos (000-100) con el duty cycle deseado.
