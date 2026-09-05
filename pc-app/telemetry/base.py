"""Interfaz comun para los lectores de telemetria de cada simulador."""
from abc import ABC, abstractmethod
from typing import Optional, Tuple


class TelemetryReader(ABC):
    """Sabe conectarse a un simulador concreto y exponer velocidad (km/h)
    y si el coche esta activo en pista ahora mismo."""

    name: str = "unknown"

    @abstractmethod
    def update(self) -> None:
        """Se llama en cada ciclo del bucle principal para refrescar el
        estado de conexion (reconectar si hace falta, detectar datos
        obsoletos, etc)."""

    @abstractmethod
    def read(self) -> Optional[Tuple[float, bool]]:
        """Devuelve (speed_kmh, on_track) si el simulador esta activo y
        enviando datos frescos ahora mismo, o None en caso contrario."""
