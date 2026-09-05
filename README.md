# Proyecto Ventiladores Simracing

Sistema que lee la velocidad del coche en **iRacing** y controla en tiempo real
la velocidad de un **ventilador PC de 4 pines (PWM)** mediante un **ESP32**,
para simular el flujo de aire según la velocidad.

## Arquitectura

```
 iRacing (Windows)                ESP32                    Ventilador
 ┌────────────────┐   WiFi/UDP   ┌──────────────┐   PWM    ┌──────────┐
 │ pc-app/main.py │ ───────────► │ firmware.ino │ ───────► │ 4-pin fan│
 │ (irsdk shared  │   "P075\n"   │ WiFiUDP +    │  25 kHz  │          │
 │  memory)       │              │ LEDC PWM     │          │          │
 └────────────────┘              └──────────────┘          └──────────┘
```

1. **`pc-app/`** (Python): se conecta a la memoria compartida de iRacing con
   `pyirsdk`, lee `Speed` y `IsOnTrack`, calcula un porcentaje de duty cycle
   (0-100%) según una curva configurable, y lo envía por UDP al ESP32 varias
   veces por segundo.
2. **`esp32-firmware/`** (PlatformIO/Arduino): se conecta a tu WiFi, escucha
   paquetes UDP con el duty cycle, y genera la señal PWM de 25 kHz que
   entienden los ventiladores de PC de 4 pines. Si deja de recibir paquetes
   (el PC se apaga, se cierra iRacing, se cae el WiFi...) el ventilador se
   frena solo por seguridad (fail-safe).

## Hardware necesario

- ESP32 (cualquier dev board, ej. ESP32-DevKitC / NodeMCU-32S).
- Ventilador de PC de 4 pines (PWM), con su fuente de 12V.
- Cables para conectar:
  - `GND` del ventilador y `GND` de la fuente de 12V → **GND común** con el ESP32.
  - Cable **PWM (azul)** del ventilador → un GPIO del ESP32 (ver `esp32-firmware/include/config.h.example`).
  - `+12V` del ventilador → fuente de 12V (NO al ESP32).
- El ESP32 se alimenta por su propio USB (5V).

> El ESP32 solo pone la señal de control (3.3V lógicos) en el cable PWM del
> ventilador; no necesita mover corriente de potencia, así que no hace falta
> MOSFET para un ventilador PWM estándar de 4 pines.

## Puesta en marcha rápida

1. **ESP32**: copia `esp32-firmware/include/config.h.example` a
   `esp32-firmware/include/config.h`, rellena tu SSID/contraseña de WiFi, y
   sube el firmware con PlatformIO. Anota la IP que imprime por el puerto
   serie.
2. **PC**: instala dependencias (`pip install -r pc-app/requirements.txt`),
   edita `pc-app/config.ini` con la IP del ESP32, arranca iRacing, y ejecuta
   `python pc-app/main.py`.
3. Sal a pista: el ventilador debería acelerar con la velocidad del coche.

Más detalles en `pc-app/README.md` y `esp32-firmware/README.md`.

## Próximos pasos posibles (no implementados aún)

- Soporte para otros simuladores (Assetto Corsa, AMS2, SimHub genérico).
- Lectura del tacómetro del ventilador (RPM real) para control en bucle cerrado.
- Varias curvas de velocidad seleccionables (ciudad/circuito, lineal/exponencial).
- Descubrimiento automático del ESP32 en la red (mDNS) en vez de IP fija.
