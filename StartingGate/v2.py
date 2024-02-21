import time

import pyray as pr
from pyray import WHITE, RAYWHITE, GRAY, BLACK, ORANGE

import deviceio
from deviceio import DeviceIO, SERVO, LANE1, LANE2, LANE3, LANE4, JOYL, JOYR, JOYD, JOYP, JOYU

from config import Config, NOT_FINISHED
from coordinator import Coordinator
# from displayv2 import Display, MainMenuView, init_display

from track import Track, MainMenu


def init_display():
    pr.init_window(240, 240, "Diecast Remote Raceway")
    pr.set_target_fps(30)
    pr.hide_cursor()

    # display.main_menu()
    # This somehow inits the GL context so actual drawing can happen
    pr.begin_drawing()
    pr.clear_background(RAYWHITE)
    print("startup")
    pr.end_drawing()
    time.sleep(2)

def main():
    config = Config("/home/aweiland/StartingGate/config/starting_gate.json")
    # display = Display(config)
    init_display()
    device = DeviceIO()


    track = Track(config, device)
    track.wait_for_finish()


    while not pr.window_should_close():
        track.loop()


if __name__ == "__main__":
    main()
