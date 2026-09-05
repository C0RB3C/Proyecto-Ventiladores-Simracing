# pc-app

Lee la telemetría de **iRacing** (memoria compartida, vía `pyirsdk`) y envía
el duty cycle del ventilador al ESP32 por UDP.

## Requisitos

- Windows (iRacing solo corre en Windows, y su SDK de memoria compartida es
  específico de Windows).
- Python 3.9+.
- iRacing instalado. **No hace falta estar en pista** para que el script se
  conecte, pero solo tiene sentido enviar duty > 0 cuando estás corriendo.

## Instalación

```powershell
cd pc-app
pip install -r requirements.txt
```

## Configuración

Edita `config.ini`:

- `esp32_ip` / `esp32_port`: IP y puerto UDP del ESP32 (por defecto `4210`,
  ver `esp32-firmware/include/config.h.example`). El ESP32 imprime su IP por
  el puerto serie al arrancar; si tu router lo permite, resérvale una IP fija
  (DHCP reservation) para que no cambie.
- `min_speed_kmh` / `max_speed_kmh`: rango de velocidades que mapea a
  0-100% de duty.
- `min_duty_percent` / `max_duty_percent`: límites del duty cycle enviado.
- `curve_exponent`: `1.0` = lineal; `>1` = sube más suave al principio y más
  fuerte al final; `<1` = al revés.
- `fan_off_when_not_on_track`: si `true`, el ventilador se para en menús/pits
  con sesión no activa (usa el canal `IsOnTrack` de iRacing).

## Ejecución

Con iRacing abierto (en menú o en pista):

```powershell
python main.py
```

Verás por consola cuándo se conecta a iRacing y cada vez que cambia el duty
enviado. Ctrl+C para parar (envía un último paquete de duty=0 al ventilador
antes de salir).

## Protocolo enviado al ESP32

Texto ASCII simple por UDP, un paquete por ciclo de envío:

```
P075\n
```

`P` + 3 dígitos con el duty cycle (0-100) + salto de línea.
