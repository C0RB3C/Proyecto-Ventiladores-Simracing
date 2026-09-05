"""
Lee la velocidad del coche desde el simulador activo (iRacing y/o Assetto
Corsa EVO, segun configuracion) y envia el duty cycle correspondiente del
ventilador a un ESP32 por UDP.

Por defecto abre una ventanita con el duty cycle, la velocidad y el
simulador activo en tiempo real. Usa --headless para desactivarla y
quedarte solo con la consola.

Uso:
    python main.py [--config config.ini] [--headless]
"""
import argparse
import configparser
import socket
import time

from telemetry.ac_evo_reader import AssettoCorsaEvoReader
from telemetry.iracing_reader import IRacingReader
from ui import FanMonitorUI

READER_CLASSES = {
    "iracing": IRacingReader,
    "ac_evo": AssettoCorsaEvoReader,
}


class Config:
    def __init__(self, path: str):
        parser = configparser.ConfigParser()
        if not parser.read(path):
            raise FileNotFoundError(f"No se pudo leer el archivo de configuracion: {path}")

        general = parser["general"]
        self.sim_priority = [s.strip() for s in general.get("priority").split(",") if s.strip()]

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


def build_readers(cfg: Config):
    readers = []
    for sim_key in cfg.sim_priority:
        reader_cls = READER_CLASSES.get(sim_key)
        if reader_cls is None:
            print(f"Aviso: simulador desconocido en config.ini: '{sim_key}' (ignorado)")
            continue
        readers.append(reader_cls())
    if not readers:
        raise ValueError("No hay ningun simulador valido en 'priority' de config.ini")
    return readers


def read_active_sim(readers):
    """Actualiza todos los lectores y devuelve (speed_kmh, on_track, nombre_sim)
    del primero (por prioridad) que tenga datos frescos, o (None, None, None)."""
    for reader in readers:
        reader.update()

    for reader in readers:
        result = reader.read()
        if result is not None:
            speed_kmh, on_track = result
            return speed_kmh, on_track, reader.name

    return None, None, None


def compute_and_send(cfg, readers, sock, state):
    """Un ciclo de trabajo: lee telemetria, calcula duty, lo envia por UDP.
    Devuelve (duty, speed_kmh, active_sim) para que quien llame actualice UI/logs."""
    speed_kmh, on_track, active_sim = read_active_sim(readers)
    duty = 0 if active_sim is None else speed_to_duty(speed_kmh, on_track, cfg)

    sock.sendto(f"P{duty:03d}\n".encode("ascii"), (cfg.esp32_ip, cfg.esp32_port))

    if duty != state["last_duty_sent"]:
        print(f"duty={duty:3d}%")
        state["last_duty_sent"] = duty
    if active_sim != state["last_active_sim"]:
        print(f"Simulador activo: {active_sim or 'ninguno'}")
        state["last_active_sim"] = active_sim

    return duty, speed_kmh, active_sim


def run_headless(cfg, readers, sock, period):
    state = {"last_duty_sent": -1, "last_active_sim": None}
    while True:
        loop_start = time.time()
        compute_and_send(cfg, readers, sock, state)
        elapsed = time.time() - loop_start
        time.sleep(max(0.0, period - elapsed))


def run_with_gui(cfg, readers, sock, period):
    state = {"last_duty_sent": -1, "last_active_sim": None}
    ui = FanMonitorUI(cfg.esp32_ip, cfg.esp32_port)
    period_ms = max(1, int(period * 1000))

    def tick():
        duty, speed_kmh, active_sim = compute_and_send(cfg, readers, sock, state)
        ui.update(duty, speed_kmh, active_sim)
        ui.schedule(period_ms, tick)

    def on_close():
        sock.sendto(b"P000\n", (cfg.esp32_ip, cfg.esp32_port))
        ui.destroy()

    ui.on_close(on_close)
    ui.schedule(0, tick)
    ui.run()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config.ini", help="Ruta al archivo config.ini")
    parser.add_argument("--headless", action="store_true", help="No abrir la ventana, solo consola")
    args = parser.parse_args()

    cfg = Config(args.config)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    readers = build_readers(cfg)
    period = 1.0 / cfg.send_rate_hz

    sim_names = ", ".join(r.name for r in readers)
    print(f"Simuladores habilitados (por prioridad): {sim_names}")
    print(f"Enviando duty cycle a {cfg.esp32_ip}:{cfg.esp32_port} cada {period*1000:.0f} ms")

    try:
        if args.headless:
            run_headless(cfg, readers, sock, period)
        else:
            run_with_gui(cfg, readers, sock, period)
    except KeyboardInterrupt:
        print("Parando, enviando duty=0 al ventilador...")
        sock.sendto(b"P000\n", (cfg.esp32_ip, cfg.esp32_port))
    finally:
        sock.close()


if __name__ == "__main__":
    main()
