class Dummy:
    def __init__(self, thing = None):
        self.thing = thing
        self.counter = 0

    def do_thing(self, param):
        print(f"Thing done, counter at {self.counter}")

    def get_thing(self): return self.thing

    def set_thing(self, new_thing): self.thing = new_thing