"""Lector de telemetria para iRacing via memoria compartida (pyirsdk)."""
from typing import Optional, Tuple

import irsdk

from .base import TelemetryReader


class IRacingReader(TelemetryReader):
    name = "iRacing"

    def __init__(self):
        self.ir = irsdk.IRSDK()
        self.connected = False

    def update(self) -> None:
        if self.connected and not (self.ir.is_initialized and self.ir.is_connected):
            self.connected = False
            self.ir.shutdown()
            print("iRacing desconectado")
        elif not self.connected:
            if self.ir.startup() and self.ir.is_initialized and self.ir.is_connected:
                self.connected = True
                print("iRacing conectado")

    def read(self) -> Optional[Tuple[float, bool]]:
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
