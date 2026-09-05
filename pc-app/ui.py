"""Ventana simple (Tkinter) para ver en pantalla el duty cycle que se esta
enviando al ESP32 en tiempo real, util para verificar el montaje sin tener
que mirar la consola."""
import tkinter as tk
from typing import Optional

BAR_WIDTH = 240
BAR_HEIGHT = 18
COLOR_ACTIVE = "#3aa757"
COLOR_IDLE = "#999999"


class FanMonitorUI:
    def __init__(self, esp32_ip: str, esp32_port: int):
        self.root = tk.Tk()
        self.root.title("Ventilador Simracing")
        self.root.attributes("-topmost", True)
        self.root.resizable(False, False)

        self.duty_var = tk.StringVar(value="--%")
        self.speed_var = tk.StringVar(value="Velocidad: -- km/h")
        self.sim_var = tk.StringVar(value="Simulador: ninguno")
        self.target_var = tk.StringVar(value=f"ESP32: {esp32_ip}:{esp32_port}")

        tk.Label(self.root, textvariable=self.duty_var, font=("Segoe UI", 48, "bold")).pack(pady=(12, 0))
        tk.Label(self.root, textvariable=self.speed_var, font=("Segoe UI", 11)).pack()
        tk.Label(self.root, textvariable=self.sim_var, font=("Segoe UI", 11)).pack()

        self.bar_canvas = tk.Canvas(self.root, width=BAR_WIDTH, height=BAR_HEIGHT, bg="#ddd", highlightthickness=0)
        self.bar_canvas.pack(pady=10)
        self.bar_fill = self.bar_canvas.create_rectangle(0, 0, 0, BAR_HEIGHT, fill=COLOR_IDLE, width=0)

        tk.Label(self.root, textvariable=self.target_var, font=("Segoe UI", 9), fg="gray").pack(pady=(0, 10))

    def update(self, duty: int, speed_kmh: Optional[float], active_sim: Optional[str]):
        self.duty_var.set(f"{duty}%")
        self.speed_var.set("Velocidad: -- km/h" if speed_kmh is None else f"Velocidad: {speed_kmh:.0f} km/h")
        self.sim_var.set(f"Simulador: {active_sim or 'ninguno'}")

        color = COLOR_ACTIVE if active_sim else COLOR_IDLE
        width = int(BAR_WIDTH * duty / 100)
        self.bar_canvas.coords(self.bar_fill, 0, 0, width, BAR_HEIGHT)
        self.bar_canvas.itemconfig(self.bar_fill, fill=color)

    def on_close(self, callback):
        self.root.protocol("WM_DELETE_WINDOW", callback)

    def schedule(self, delay_ms: int, callback):
        self.root.after(delay_ms, callback)

    def run(self):
        self.root.mainloop()

    def destroy(self):
        self.root.destroy()
