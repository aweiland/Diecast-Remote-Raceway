import enum
import json
import operator
import select
import time
import traceback
import threading
from abc import ABC

import pyray as pr
from pyray import WHITE, RAYWHITE, GRAY, BLACK, ORANGE

import bluetooth
import deviceio
from deviceio import DeviceIO, SERVO, LANE1, LANE2, LANE3, LANE4

from config import Config, NOT_FINISHED
from coordinator import Coordinator
# from displayv2 import Display, MainMenuView, init_display
# from statemachine import StateMachine, State

from track import Track, MainMenu


def init_display():
    pr.init_window(240, 240, "Diecast Remote Raceway")
    pr.set_target_fps(30)
    pr.hide_cursor()

def main():
    config = Config("/home/aweiland/StartingGate/config/starting_gate.json")
    # display = Display(config)
    init_display()
    device = DeviceIO()

    track = Track(MainMenu(), config, device)

    # display.main_menu()
    # This somehow inits the GL context so actual drawing can happen
    pr.begin_drawing()
    pr.clear_background(RAYWHITE)
    print("startup")
    pr.end_drawing()
    time.sleep(2)

    while not pr.window_should_close():
        # time.sleep(1)
        track.loop()


if __name__ == "__main__":
    main()
