from mpu6050 import MPU6050
import time

sensor = MPU6050()

print("--- STARTING FREEZE TEST ---")
print("1. You have 5 seconds of 'Normal' reading...")
for _ in range(20):
    p = sensor.get_pose().pitch
    print(f"Live Pitch: {p:.2f}", end='\r')
    time.sleep(0.1)

print("\n\n2. MAIN THREAD IS NOW FROZEN FOR 5 SECONDS.")
print("--> ACTION: Tilt the robot 45 degrees NOW and HOLD IT THERE.")
time.sleep(5) 

print("\n3. MAIN THREAD WOKE UP.")
# This call happens the microsecond the sleep ends
final_pose = sensor.get_pose()
print(f"Immediate Pose after wakeup: Pitch={final_pose.pitch:.2f}")

if abs(final_pose.pitch) > 30:
    print("\nSUCCESS: The background thread updated the pose while the main thread was asleep!")
else:
    print("\nFAILURE: The pose didn't update, or you didn't tilt it enough.")