## TARS

Code for TARS from Interstellar.

This repository contains the ROS 2 Humble workspace for the TARS robot controller, motion stack, leg control, state estimation, and base-station (B0) interface.

### Layout

- **Root**: Colcon workspace root. The ROS 2 packages live in `src/`.
- **`src/`**: Contains all ROS 2 packages:
  - `robot_controller`: Top-level robot controller and mode management.
  - `motion`: Motion planner and motion executor nodes.
  - `leg_control`: Leg L0–L3 carriage and actuator control.
  - `state_estimation`: IMU and leg pose/acceleration estimation.
  - `b0_interface`: Base-station (B0) command/telemetry interface.
  - `bringup`: Launch files to start common configurations.

### Prerequisites

- ROS 2 Humble installed and sourced with `source /opt/ros/humble/setup.bash`
  - I recommend running `echo 'source /opt/ros/humble/setup.bash' >> ~/.bashrc` to auto source
- System dependencies installed via `rosdep`:

```bash
cd /path/to/TARS
rosdep install --from-paths src --ignore-src -r -y
```

### Building

From the workspace root:

```bash
cd /path/to/TARS
colcon build
source install/setup.bash
```

You need to re-build the package every time you edit code. Target a package instead of re-building the whole project with:
```bash
colcon build --packages-select <package>
```

### Running core nodes (examples)

After building and sourcing:

```bash
# Robot controller
ros2 run robot_controller robot_controller

# Motion planner
ros2 run motion motion_planner

# Motion executor
ros2 run motion motion_executor

# Leg control (generic leg node, use parameters/namespaces per leg)
ros2 run leg_control leg_controller

# State estimation
ros2 run state_estimation leg_pose_estimator

# B0 interface
ros2 run b0_interface b0_interface

# Bringup example (starts a minimal set of nodes)
ros2 launch bringup minimal_bringup.launch.py

# TODO: Add main bringup file to run the whole robot
```

### Basic systems test

After building and sourcing the workspace, start the full stack:

```bash
ros2 launch bringup minimal_bringup.launch.py
```

You should then see the following nodes (namespaces abbreviated):

```bash
ros2 node list
/robot_controller
/motion_planner
/motion_executor
/leg_pose_estimator
/b0_interface
/L0/leg_controller
/L1/leg_controller
/L2/leg_controller
/L3/leg_controller
```

#### Set target velocity and turn rate from B0 (CLI)

With the stack running, you can command motion via the B0 topics:

```bash
# From B0: set target forward velocity in the range [-1.0, 1.0]
ros2 topic pub /b0/target_velocity std_msgs/msg/Float32 "{data: 0.5}"

# From B0: set target rotational speed in the range [-1.0, 1.0]
ros2 topic pub /b0/target_turn_rate std_msgs/msg/Float32 "{data: 0.3}"
```

The `b0_interface` node receives these CLI commands, republishes them on `target_velocity` and `target_turn_rate`, the `motion` nodes translate them into leg-level commands, and the `leg_control` nodes log the received targets.

#### Observing logging and status

All nodes log their startup and key events to the console. You can also inspect status topics:

```bash
ros2 topic echo /b0/status
ros2 topic echo /state_estimation/status
ros2 topic echo /L0/leg/status
```
