import threading
import time
import pigpio


class ServoController:
    """
    Asynchronous servo controller using pigpio.

    Features:
      - Set a goal angle (degrees) at any time via set_goal().
      - Background thread updates the servo toward the goal at a controlled rate.
      - Optional smoothing via max_speed_dps (degrees per second).
    """

    def __init__(
        self,
        gpio_pin: int = 18,
        min_pulse_us: int = 500,
        max_pulse_us: int = 2500,
        min_angle_deg: float = 0.0,
        max_angle_deg: float = 285.0,
        update_hz: int = 50,
        max_speed_dps: float = 360.0,
        start_angle_deg: float = 90.0,
        pigpio_host: str = "localhost",
        pigpio_port: int = 8888,
    ) -> None:
        self.gpio_pin = gpio_pin
        self.min_pulse_us = int(min_pulse_us)
        self.max_pulse_us = int(max_pulse_us)
        self.min_angle_deg = float(min_angle_deg)
        self.max_angle_deg = float(max_angle_deg)

        self.update_hz = float(update_hz)
        self.max_speed_dps = float(max_speed_dps)

        self._lock = threading.Lock()
        self._goal_deg = float(start_angle_deg)
        self._pos_deg = float(start_angle_deg)

        self._stop_evt = threading.Event()
        self._thread: threading.Thread | None = None

        self._pi = pigpio.pi(pigpio_host, pigpio_port)
        if not self._pi.connected:
            raise RuntimeError("Could not connect to pigpio daemon (pigpiod).")
        self._write_angle(self._pos_deg)
        self._pi.set_PWM_frequency(gpio_pin,update_hz)


    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_evt.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_evt.set()
        if self._thread:
            self._thread.join(timeout=2.0)
        self._pi.set_servo_pulsewidth(self.gpio_pin, 0)
        self._pi.stop()

    def set_goal(self, angle_deg: float) -> None:
        angle = self._clamp(float(angle_deg), self.min_angle_deg, self.max_angle_deg)
        with self._lock:
            self._goal_deg = angle

    def get_goal(self) -> float:
        with self._lock:
            return float(self._goal_deg)

    def get_position_estimate(self) -> float:
        with self._lock:
            return float(self._pos_deg)

    def _run_loop(self) -> None:
        dt = 1.0 / self.update_hz
        max_step = self.max_speed_dps * dt

        next_t = time.monotonic()
        while not self._stop_evt.is_set():
            now = time.monotonic()
            if now < next_t:
                time.sleep(next_t - now)
                continue
            next_t += dt

            with self._lock:
                goal = self._goal_deg
                pos = self._pos_deg

            delta = goal - pos
            if abs(delta) <= max_step:
                pos = goal
            else:
                pos += max_step if delta > 0 else -max_step

            with self._lock:
                self._pos_deg = pos

            self._write_angle(pos)

    def _write_angle(self, angle_deg: float) -> None:
        pw = self._angle_to_pulsewidth_us(angle_deg)
        self._pi.set_servo_pulsewidth(self.gpio_pin, pw)

    def _angle_to_pulsewidth_us(self, angle_deg: float) -> int:
        angle = self._clamp(angle_deg, self.min_angle_deg, self.max_angle_deg)
        span_angle = self.max_angle_deg - self.min_angle_deg
        if span_angle <= 0:
            raise ValueError("max_angle_deg must be greater than min_angle_deg")

        t = (angle - self.min_angle_deg) / span_angle
        pw = self.min_pulse_us + (angle/self.max_angle_deg)*(self.max_pulse_us-self.min_pulse_us)
        return pw

    @staticmethod
    def _clamp(value: float, low: float, high: float) -> float:
        if value < low:
            return low
        if value > high:
            return high
        return value


if __name__ == "__main__":
    servo = ServoController(gpio_pin=18, start_angle_deg=0.0, max_speed_dps=180.0)
    servo.start()
    MAX_ANGLE = 270
    new_max = 270
    servo.max_angle_deg = new_max
    prev_angle = 90
    angle = 90
    try:
        while True:
            angle = input(f"A: Set MAX_ANGLE\nQ: Quit\nInput Angle (0-{MAX_ANGLE}): ").lower()
            if angle == "q":
                print("Exiting...")
                break
            elif angle == "a":
                new_max = float(input("Enter Max Angle (TYPE IN AN INTEGER): "))
                if 180 < new_max < 360:
                    print("Updating angle based on max angle...")
                    MAX_ANGLE = new_max
                    servo.max_angle_deg = new_max
                    servo.set_goal(prev_angle)
                else:
                    print("Only type in angles less than 360 or greater than 180")

            elif angle.isdigit():
                angle = int(angle)
                if 0 > angle > MAX_ANGLE:
                    print(f"ONLY INPUT ANGLESS BETWEEN 0 AND {MAX_ANGLE}")
                else:
                    print("Setting angle...")
                    servo.set_goal(angle)
                    prev_angle = angle
                    time.sleep(.75)
    finally:
        servo.stop()
