import time
from servo_driver import set_servo_angle

OUTER = 0
INNER = 1
HIP = 2
ROLL = 3
PITCH = 4
YAW = 5

LEG_SERVOS = [
    (0, 1, 2),
    (3, 4, 5),
    (6, 7, 8),
    (9, 10, 11)
]

def set_leg_goal(leg_index, outer, inner, hip):
    outer_servo, inner_servo, hip_servo = LEG_SERVOS[leg_index]
    print(f"Leg {leg_index}: outer={outer} inner={inner} hip={hip}")
    set_servo_angle(outer_servo, outer)
    set_servo_angle(inner_servo, inner)
    set_servo_angle(hip_servo, hip)

def do_step(state_map):
    print("\nExecuting step\n")
    for leg_index, row in enumerate(state_map):
        outer = row[OUTER]
        inner = row[INNER]
        hip = row[HIP]
        set_leg_goal(leg_index, outer, inner, hip)
    roll = state_map[0][ROLL]
    pitch = state_map[0][PITCH]
    yaw = state_map[0][YAW]
    print(f"Orientation target -> Roll:{roll} Pitch:{pitch} Yaw:{yaw}")
    time.sleep(1)
    print("Step complete\n")

def print_state_map(state_map):
    print("\nCurrent State Map\n")
    print("Leg | Outer Inner Hip Roll Pitch Yaw")
    print("-------------------------------------")
    for i, row in enumerate(state_map):
        print(
            f"{i}   | "
            f"{row[0]:>5} "
            f"{row[1]:>5} "
            f"{row[2]:>5} "
            f"{row[3]:>4} "
            f"{row[4]:>5} "
            f"{row[5]:>3}"
        )
    print()

def input_row(leg_index):
    while True:
        cmd = input(f"Enter values for leg {leg_index} (outer inner hip roll pitch yaw): ")
        parts = cmd.split()
        if len(parts) != 6:
            print("Need 6 numbers")
            continue
        try:
            row = [float(x) for x in parts]
            return row
        except:
            print("Invalid input")

def input_state_map():
    state_map = []
    print("\nEnter new state map")
    for i in range(4):
        row = input_row(i)
        state_map.append(row)
    return state_map

def default_state():
    return [
        [90, 90, 90, 0, 0, 0],
        [90, 90, 90, 0, 0, 0],
        [90, 90, 90, 0, 0, 0],
        [90, 90, 90, 0, 0, 0]
    ]

def main():
    state_map = default_state()
    while True:
        print("Robot Controller")
        print("----------------")
        print("1 -> Show state map")
        print("2 -> Enter new state map")
        print("3 -> Execute step")
        print("4 -> Edit one leg")
        print("5 -> Quit")
        cmd = input("Select option: ")
        if cmd == "1":
            print_state_map(state_map)
        elif cmd == "2":
            state_map = input_state_map()
        elif cmd == "3":
            print_state_map(state_map)
            do_step(state_map)
        elif cmd == "4":
            try:
                leg = int(input("Leg index (0-3): "))
                if leg < 0 or leg > 3:
                    print("Invalid leg")
                    continue
                state_map[leg] = input_row(leg)
            except:
                print("Invalid input")
        elif cmd == "5":
            print("Exiting controller")
            break
        else:
            print("Invalid option")

if __name__ == "__main__":
    main()
