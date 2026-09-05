# pc-app

Lee la telemetría del simulador activo (**iRacing** y/o **Assetto Corsa
EVO**) y envía el duty cycle del ventilador al ESP32 por UDP.

## Arquitectura interna

`telemetry/` contiene un lector por simulador, todos con la misma interfaz
(`update()` + `read() -> (speed_kmh, on_track) | None`):

- `telemetry/iracing_reader.py` — memoria compartida oficial via `pyirsdk`.
- `telemetry/ac_evo_reader.py` — memoria compartida de Assetto Corsa EVO
  (formato heredado del AC clásico, ver comentarios en el archivo).

`main.py` prueba los lectores en el orden indicado en `config.ini`
(`[general] priority`) y usa el primero que tenga datos frescos. Si ninguno
está activo, envía duty 0. Así puedes dejar el script corriendo y arrancar
el simulador que quieras sin tocar nada.

## Requisitos

- Windows (ambos simuladores exponen su telemetría vía memoria compartida
  específica de Windows).
- Python 3.9+.
- iRacing y/o Assetto Corsa EVO instalados.

## Instalación

```powershell
cd pc-app
pip install -r requirements.txt
```

(La dependencia `pyirsdk` solo hace falta para iRacing; el lector de
Assetto Corsa EVO usa únicamente la librería estándar de Python.)

## Configuración

Edita `config.ini`:

- `priority`: lista separada por comas de los simuladores a comprobar, en
  orden de prioridad (`iracing,ac_evo` por defecto). Si tienes los dos
  instalados pero solo usas uno, puedes dejar solo ese nombre.
- `esp32_ip` / `esp32_port`: IP y puerto UDP del ESP32 (por defecto `4210`,
  ver `esp32-firmware/include/config.h.example`). El ESP32 imprime su IP por
  el puerto serie al arrancar; si tu router lo permite, resérvale una IP fija
  (DHCP reservation) para que no cambie.
- `min_speed_kmh` / `max_speed_kmh`: rango de velocidades que mapea a
  0-100% de duty.
- `min_duty_percent` / `max_duty_percent`: límites del duty cycle enviado.
- `curve_exponent`: `1.0` = lineal; `>1` = sube más suave al principio y más
  fuerte al final; `<1` = al revés.
- `fan_off_when_not_on_track`: si `true`, el ventilador se para cuando el
  coche no está activo en pista. Solo aplica a iRacing (canal `IsOnTrack`);
  Assetto Corsa EVO no distingue esto de forma fiable todavía (ver más
  abajo), así que para ese simulador el ventilador sigue la velocidad
  directamente (a 0 km/h ya se va a duty mínimo por la propia curva).

## Ejecución

Arranca primero el simulador (iRacing o Assetto Corsa EVO) y después:

```powershell
python main.py
```

Verás por consola qué simulador se detecta como activo y cada vez que
cambia el duty enviado. Ctrl+C para parar (envía un último paquete de
duty=0 al ventilador antes de salir).

> **Importante para Assetto Corsa EVO:** arranca siempre el juego *antes*
> de lanzar `main.py`. El lector abre la memoria compartida por nombre y,
> si no existe todavía, Windows la crea vacía con el tamaño que pide
> nuestro script; si luego el juego arranca y pide un tamaño distinto,
> puede no coincidir. Empezando el juego primero se evita el problema.

## Limitación conocida: Assetto Corsa EVO

A fecha de esta implementación, AC EVO está en Early Access y su
telemetría es más limitada que la de ACC/AC clásico (sin estado de sesión
fiable, entre otras cosas). El lector de este proyecto solo usa velocidad
y considera el juego "activo" mientras el contador interno de paquetes de
física siga avanzando; si Kunos cambia el layout de memoria compartida en
una actualización futura, puede que `telemetry/ac_evo_reader.py` necesite
ajustarse (los offsets están documentados en el propio archivo).

## Protocolo enviado al ESP32

Texto ASCII simple por UDP, un paquete por ciclo de envío:

```
P075\n
```

`P` + 3 dígitos con el duty cycle (0-100) + salto de línea. Igual que
antes: no ha cambiado por soportar varios simuladores.
