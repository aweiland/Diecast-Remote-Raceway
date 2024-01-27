import enum
import json
import operator
import select
import time
import traceback
import threading

import pyray as pr
from pyray import WHITE, RAYWHITE, GRAY, BLACK, ORANGE

import bluetooth
import deviceio
from deviceio import DeviceIO, SERVO, LANE1, LANE2, LANE3, LANE4

from config import Config, NOT_FINISHED
from coordinator import Coordinator
from displayv2 import Display

# from statemachine import StateMachine, State

from functools import wraps


def singleton(orig_cls):
    orig_new = orig_cls.__new__
    instance = None

    @wraps(orig_cls.__new__)
    def __new__(cls, *args, **kwargs):
        nonlocal instance
        if instance is None:
            instance = orig_new(cls, *args, **kwargs)
        return instance

    orig_cls.__new__ = __new__
    return orig_cls


class TrackState:
    def enter(self, track: 'Track'):
        pass

    def exit(self, track: 'Track'):
        pass

    def loop(self, track: 'Track'):
        pass

    def handle_event(self, event):
        pass


class Track:

    def __init__(self, initial_state: TrackState, config: Config, display: Display, device: DeviceIO):
        self.display = display
        self.config = config
        self.device = device
        self.current_state: TrackState = initial_state
        self.current_state.enter(self)

    def set_state(self, new_state: TrackState):
        self.current_state.exit(self)
        self.current_state = new_state
        self.current_state.enter(self)

    def loop(self):
        self.current_state.loop(self)

    def handle_event(self, event):
        pass

    def reset(self):
        pass


@singleton
class MainMenu(TrackState):

    def __start_race(self):
        print('race')

    def __configure(self):
        print('configure')

    def enter(self, track):
        track.device.push_key_handlers(self.__start_race, deviceio.default_key_2_handler,
                                       self.__configure, deviceio.default_joystick_handler)

    def exit(self, track: Track):
        track.device.pop_key_handlers()

    def loop(self, track):
        track.display.show_main_menu()
        time.sleep(0.1)


# class RaceStateMachine(StateMachine):
#     main_menu = State("MainMenu", initial=True)
#     single_race = State("SingleRace")
#
#     start_single = main_menu.to(single_race)
#
#     def __init__(self, display: Display):
#         self.display = display
#         super(RaceStateMachine, self).__init__()
#
#     def on_enter_main_menu(self):
#         print("Showing main menu")
#         self.display.show_main_menu()

def main():
    config = Config("/home/aweiland/StartingGate/config/starting_gate.json")
    display = Display(config)
    device = DeviceIO()

    track = Track(MainMenu(), config, display, device)

    # display.main_menu()

    while True:
        time.sleep(1)
        track.loop()


if __name__ == "__main__":
    main()
