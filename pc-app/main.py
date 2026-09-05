"""
Lee la velocidad del coche desde iRacing (memoria compartida via pyirsdk) y
envia el duty cycle correspondiente del ventilador a un ESP32 por UDP.

Uso:
    python main.py [--config config.ini]
"""
import argparse
import configparser
import socket
import time

import irsdk


class Config:
    def __init__(self, path: str):
        parser = configparser.ConfigParser()
        if not parser.read(path):
            raise FileNotFoundError(f"No se pudo leer el archivo de configuracion: {path}")

        net = parser["network"]
        self.esp32_ip = net.get("esp32_ip")
        self.esp32_port = net.getint("esp32_port")
        self.send_rate_hz = net.getfloat("send_rate_hz")

        curve = parser["curve"]
        self.min_speed_kmh = curve.getfloat("min_speed_kmh")
        self.max_speed_kmh = curve.getfloat("max_speed_kmh")
        self.min_duty_percent = curve.getfloat("min_duty_percent")
        self.max_duty_percent = curve.getfloat("max_duty_percent")
        self.curve_exponent = curve.getfloat("curve_exponent")

        behavior = parser["behavior"]
        self.fan_off_when_not_on_track = behavior.getboolean("fan_off_when_not_on_track")


def speed_to_duty(speed_kmh: float, on_track: bool, cfg: Config) -> int:
    """Convierte velocidad (km/h) a duty cycle (0-100), aplicando la curva configurada."""
    if cfg.fan_off_when_not_on_track and not on_track:
        return 0

    if speed_kmh <= cfg.min_speed_kmh:
        return int(round(cfg.min_duty_percent))
    if speed_kmh >= cfg.max_speed_kmh:
        return int(round(cfg.max_duty_percent))

    span = cfg.max_speed_kmh - cfg.min_speed_kmh
    fraction = (speed_kmh - cfg.min_speed_kmh) / span
    fraction = fraction ** cfg.curve_exponent

    duty = cfg.min_duty_percent + fraction * (cfg.max_duty_percent - cfg.min_duty_percent)
    return int(round(max(0, min(100, duty))))


class IRacingReader:
    """Envuelve irsdk con reconexion automatica cuando iRacing arranca/cierra."""

    def __init__(self):
        self.ir = irsdk.IRSDK()
        self.connected = False

    def update(self):
        if self.connected and not (self.ir.is_initialized and self.ir.is_connected):
            self.connected = False
            self.ir.shutdown()
            print("iRacing desconectado")
        elif not self.connected:
            if self.ir.startup() and self.ir.is_initialized and self.ir.is_connected:
                self.connected = True
                print("iRacing conectado")

    def read(self):
        """Devuelve (speed_kmh, on_track) o None si no hay datos validos."""
        if not self.connected:
            return None
        try:
            speed_ms = self.ir["Speed"]
            on_track = bool(self.ir["IsOnTrack"])
        except Exception:
            return None
        if speed_ms is None:
            return None
        return speed_ms * 3.6, on_track


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config.ini", help="Ruta al archivo config.ini")
    args = parser.parse_args()

    cfg = Config(args.config)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    reader = IRacingReader()

    period = 1.0 / cfg.send_rate_hz
    last_duty_sent = -1

    print(f"Enviando duty cycle a {cfg.esp32_ip}:{cfg.esp32_port} cada {period*1000:.0f} ms")

    try:
        while True:
            loop_start = time.time()
            reader.update()

            data = reader.read()
            if data is None:
                duty = 0
            else:
                speed_kmh, on_track = data
                duty = speed_to_duty(speed_kmh, on_track, cfg)

            message = f"P{duty:03d}\n".encode("ascii")
            sock.sendto(message, (cfg.esp32_ip, cfg.esp32_port))

            if duty != last_duty_sent:
                print(f"duty={duty:3d}%")
                last_duty_sent = duty

            elapsed = time.time() - loop_start
            time.sleep(max(0.0, period - elapsed))
    except KeyboardInterrupt:
        print("Parando, enviando duty=0 al ventilador...")
        sock.sendto(b"P000\n", (cfg.esp32_ip, cfg.esp32_port))
    finally:
        sock.close()


if __name__ == "__main__":
    main()
