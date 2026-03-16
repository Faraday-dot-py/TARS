# Ender Board Hardware Task Plan

This task plan assumes real hardware progress should happen in small, observable steps.
Each task includes a testing section because the task is not complete until something physical is wired, flashed, and observed.

Do not move to the next goal until the previous one is recorded as PASS or consciously accepted as BLOCKED.

## Goal 0: Custom Serial Banner

Purpose:

- prove that a custom firmware image can run on the connected board and speak on the same serial console path that stock firmware uses
- establish a realistic Marlin-based customization path before wiring actuators or sensors

Implementation tasks:

- keep the current bare-metal artifacts only as reference, not as the primary build path
- prepare a Marlin-based build target for the Creality `4.2.2` GD32 board
- add the smallest possible custom banner hook to the selected Marlin tree
- emit a deterministic serial string at `115200`

Testing functionality:

Physical hookup:

- no actuator or sensor wiring required
- only the board, working SD-card flash path, USB serial, and board power

Real-world test:

- flash the custom banner build
- watch the stock CH340 serial console from Windows
- verify the custom banner appears after bootloader handoff

PASS if:

- a custom banner appears reliably after each boot
- the board still boots stably
- the console remains readable at `115200`

FAIL if:

- only bootloader messages appear
- the board becomes silent or unstable after the app jump
- the custom image cannot be distinguished from stock behavior

## Goal 1: Servo

Purpose:

- prove one real output can be controlled safely from board code
- validate that watchdog-safe-stop can zero or disable that output

Implementation tasks:

- choose and document one candidate servo output pin from actual board inspection
- implement servo output in the selected firmware base
- implement safe-stop for the servo path first
- add coarse telemetry or coarse serial diagnostics for the applied servo target

Testing functionality:

Physical hookup:

- connect only the servo
- provide safe servo power and common ground
- do not connect steppers or IMUs yet

Real-world test:

- flash the servo-only firmware build
- send enable, servo target, disable, and safe-stop commands
- observe physical servo motion and observe that timeout or disable stops commanded activity

PASS if:

- the servo moves in response to commands
- timeout or disable returns it to the intended safe state
- serial communication remains stable during repeated servo updates

FAIL if:

- the servo jitters badly
- safe-stop does not reliably stop motion intent
- serial communication becomes unreliable during servo control

## Goal 1+2: Combined Servo + IMU
- keep servo on the proven probe header path
- move IMU signals to separate endstop signal pins
- validate that servo movement and IMU telemetry work concurrently over one UART bridge

Goal 2: IMU

Purpose:

- prove one sensor path can be sampled and reported without destabilizing the control loop

Implementation tasks:

- confirm actual I2C pins on the connected board
- add one MPU6050 driver path in the selected firmware base
- report raw IMU values first, without fusion
- keep servo code present only if Goal 1 already passed cleanly

Testing functionality:

Physical hookup:

- connect one MPU6050 only
- keep the servo connected only if its behavior is already trusted
- do not connect steppers yet

Real-world test:

- flash the IMU-enabled firmware build
- verify telemetry or coarse serial diagnostics change when the sensor is moved by hand
- confirm watchdog, heartbeat, and serial transport still behave normally

PASS if:

- real IMU readings are visible and change plausibly with motion
- telemetry remains coherent over repeated reads
- no regression is introduced in safe-stop behavior

FAIL if:

- IMU reads are unstable or obviously implausible
- telemetry becomes corrupted or stalls
- adding the IMU destabilizes the existing control path

## Goal 3: Stepper

Purpose:

- prove one real motor channel can be commanded and stopped safely

Implementation tasks:

- confirm the first stepper output path on the actual board
- implement a real first stepper path in the selected firmware base
- ensure disable and watchdog behavior actively safe-stop the stepper output
- report applied or estimated stepper state in telemetry or coarse serial diagnostics

Testing functionality:

Physical hookup:

- connect only the first stepper path
- do not connect the second stepper yet
- keep servo or IMU connected only if earlier goals already passed and remain stable

Real-world test:

- flash the first-stepper firmware build
- command movement, then disable, then watchdog timeout
- observe that the motor stops safely and predictably

PASS if:

- the stepper responds to commands
- disable and timeout stop it reliably
- serial transport remains stable while stepping

FAIL if:

- motion continues after safe-stop conditions
- stepping destabilizes transport or the main loop
- the board cannot sustain clean first-stepper behavior

## Goal 4: Second Stepper

Purpose:

- determine whether dual-stepper concurrency is plausible on this board

Implementation tasks:

- add the second stepper channel in the selected firmware base
- keep safe-stop behavior common across both channels
- extend telemetry or serial diagnostics to expose both applied targets or states

Testing functionality:

Physical hookup:

- add the second stepper only after Goal 3 passes

Real-world test:

- flash the dual-stepper firmware build
- command both motors under repeated updates
- verify safe-stop and timeout behavior under concurrency

PASS if:

- both motors can be driven without obvious instability
- safe-stop remains reliable under dual-stepper load

FAIL if:

- the second motor causes timing collapse
- transport stability degrades materially
- safe-stop becomes unreliable under concurrency

## Goal 5: Second IMU

Purpose:

- prove the intended dual-IMU telemetry arrangement is viable

Implementation tasks:

- implement the second MPU6050 path
- keep telemetry raw at first
- add any addressing or bus-selection mechanism required by real hardware

Testing functionality:

Physical hookup:

- add the second MPU6050 only after the first is stable

Real-world test:

- flash the dual-IMU firmware build
- move each sensor independently if possible
- verify both data streams remain distinct and plausible

PASS if:

- both sensors produce usable data without collapsing transport or control timing

FAIL if:

- the dual-IMU arrangement is electrically or timing-wise unstable

## Goal 6: Combined Validation

Purpose:

- determine whether one board can plausibly serve one whole leg

Implementation tasks:

- run servo, IMU, and stepper paths together only after the simpler tests pass
- keep watchdog and safe-stop as the highest priority behavior
- add fault bits for any detected actuator or sensor failure modes

Testing functionality:

Physical hookup:

- connect the validated hardware from earlier goals only
- do not add new electrical unknowns during the combined test

Real-world test:

- flash the combined firmware build
- exercise repeated command traffic, telemetry, safe-stop, and timeouts
- observe whether real-world behavior remains understandable and safe

PASS if:

- outputs remain controllable
- timeout and disable still dominate all other behavior
- telemetry remains usable enough for supervision

FAIL if:

- the combined system becomes unsafe, unstable, or too opaque to trust
