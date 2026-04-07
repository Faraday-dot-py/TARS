import json
import time

from servo import Servo

F = 0
A = 1
I = 2
R = 3
P = 4
Y = 5


def load_config():
    with open("config.json", "r") as f:
        return json.load(f)


def create_servos(config):
    legs = config["legs"]

    servos = []

    for leg_name in ["l0", "l1", "l2", "l3"]:
        leg = legs[leg_name]

        leg_servos = {
            "F": Servo(pin=leg["a_car_pins"][0]),
            "A": Servo(pin=leg["a_car_pins"][1]),
            "I": Servo(pin=leg["a_car_pins"][2]) if leg["hip"] else None
        }

        servos.append(leg_servos)

    return servos


def do_step(state_map, servos):
    for leg_index, row in enumerate(state_map):
        f_goal = row[F]
        a_goal = row[A]
        i_goal = row[I]

        servos[leg_index]["F"].set_goal(f_goal)
        servos[leg_index]["A"].set_goal(a_goal)

        if servos[leg_index]["I"] is not None:
            servos[leg_index]["I"].set_goal(i_goal)


def update_servos(servos):
    for leg in servos:
        for actuator in leg.values():
            if actuator is not None:
                actuator.update()


def cleanup_servos(servos):
    for leg in servos:
        for actuator in leg.values():
            if actuator is not None:
                actuator.cleanup()


def goals_reached(servos, tolerance=1.0):
    for leg in servos:
        for actuator in leg.values():
            if actuator is None:
                continue
            if abs(actuator._goal - actuator._current) > tolerance:
                return False
    return True


def main():
    config = load_config()
    servos = create_servos(config)

    state_map = [
        [90, 90, 90, 0, 0, 0],
        [90, 90, 90, 0, 0, 0],
        [90, 90, 90, 0, 0, 0],
        [90, 90, 90, 0, 0, 0]
    ]

    do_step(state_map, servos)

    try:
        while not goals_reached(servos):
            update_servos(servos)
            time.sleep(0.02)
    finally:
        cleanup_servos(servos)


if __name__ == "__main__":
    main()
