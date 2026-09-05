"""Lector de telemetria para Assetto Corsa EVO via memoria compartida.

Assetto Corsa EVO (Kunos, en Early Access a fecha de esta implementacion)
publica su telemetria en memoria compartida de Windows heredando el formato
del Assetto Corsa clasico, pero bajo nombres nuevos:

    Local\\acevo_pmf_physics
    Local\\acevo_pmf_graphics
    Local\\acevo_pmf_static

Esta implementacion solo lee el bloque de fisica (es el que trae la
velocidad y se actualiza a frecuencia de fisica, no de HUD). El layout de
cabecera coincide con el AC clasico bien documentado:

    packetId (int32), gas (float), brake (float), fuel (float),
    gear (int32), rpms (int32), steerAngle (float), speedKmh (float), ...

Referencia comunitaria (no es documentacion oficial de Kunos; el juego esta
en Early Access y el layout puede cambiar entre versiones):
https://github.com/albertowd/live-telemetry-evo/blob/develop/docs/SHARED_MEMORY.md

Limitacion conocida: el campo `status` del bloque de graficos no es fiable
en EVO durante el Early Access (la telemetria puede llegar antes de estar
realmente en pista). Por eso este lector NO depende de `status`: considera
el simulador "activo" solo si el `packetId` de fisica esta avanzando (el
juego esta emitiendo datos de verdad). Con el coche parado la velocidad ya
sera 0 y el ventilador se ira a duty minimo por la propia curva.

Importante: para evitar que este script cree la memoria compartida con un
tamano distinto al que espera el juego, arranca siempre Assetto Corsa EVO
ANTES de lanzar pc-app/main.py.
"""
import mmap
import struct
import time
from typing import Optional, Tuple

from .base import TelemetryReader

PHYSICS_MAP_NAME = "Local\\acevo_pmf_physics"
PHYSICS_MAP_SIZE = 800  # tal y como documenta live-telemetry-evo

# packetId(i) gas(f) brake(f) fuel(f) gear(i) rpms(i) steerAngle(f) speedKmh(f)
PHYSICS_HEADER_FORMAT = "<ifffiiff"
PHYSICS_HEADER_SIZE = struct.calcsize(PHYSICS_HEADER_FORMAT)

STALE_TIMEOUT_S = 2.0


class AssettoCorsaEvoReader(TelemetryReader):
    name = "Assetto Corsa EVO"

    def __init__(self):
        self._mmap: Optional[mmap.mmap] = None
        self._last_packet_id: Optional[int] = None
        self._last_change_time: float = 0.0
        self._was_live = False

    def _ensure_open(self) -> bool:
        if self._mmap is not None:
            return True
        try:
            self._mmap = mmap.mmap(-1, PHYSICS_MAP_SIZE, tagname=PHYSICS_MAP_NAME)
            return True
        except OSError:
            self._mmap = None
            return False

    def update(self) -> None:
        self._ensure_open()

    def read(self) -> Optional[Tuple[float, bool]]:
        if not self._ensure_open():
            return None

        try:
            self._mmap.seek(0)
            raw = self._mmap.read(PHYSICS_HEADER_SIZE)
        except (ValueError, OSError):
            # El mapping dejo de ser valido (p.ej. permisos, cierre raro);
            # se reintenta abrir en la siguiente vuelta.
            self._mmap = None
            return None

        if len(raw) < PHYSICS_HEADER_SIZE:
            return None

        packet_id, _gas, _brake, _fuel, _gear, _rpms, _steer, speed_kmh = struct.unpack(
            PHYSICS_HEADER_FORMAT, raw
        )

        now = time.time()
        if packet_id != self._last_packet_id:
            self._last_packet_id = packet_id
            self._last_change_time = now

        is_live = packet_id != 0 and (now - self._last_change_time) < STALE_TIMEOUT_S

        if is_live != self._was_live:
            print("Assetto Corsa EVO: telemetria detectada" if is_live else "Assetto Corsa EVO: sin datos")
            self._was_live = is_live

        if not is_live:
            return None

        return speed_kmh, True
