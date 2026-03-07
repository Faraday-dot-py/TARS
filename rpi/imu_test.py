import time
from mpu6050 import mpu6050

sensor = mpu6050()

print("MPU6050 initialized successfully!")
print("Reading data... Press Ctrl+C to stop.\n")

try:
    while True:
        accel_data = sensor.read_accel_g()
        gyro_data = sensor.read_gyro_dps()

        # Use [0] for X, [1] for Y, and [2] for Z
        print(f"Accel [g]: X={accel_data[0]:.2f}, Y={accel_data[1]:.2f}, Z={accel_data[2]:.2f}")
        print(f"Gyro [dps]: X={gyro_data[0]:.2f}, Y={gyro_data[1]:.2f}, Z={gyro_data[2]:.2f}")
        print("-" * 40)

        time.sleep(0.5)

except KeyboardInterrupt:
    print("\nExiting IMU reader.")