import enum
import random
import threading
import time

from abc import ABC

import pyray as pr
from pyray import WHITE, RAYWHITE, GRAY, BLACK, ORANGE, LIGHTGRAY



def init_display():
    print("Starting window")
    pr.init_window(240, 240, "Diecast Remote Raceway")
    pr.set_target_fps(30)
    pr.hide_cursor()


class Display(threading.Thread):
    __instance = None

    def __new__(cls, val):
        """
        Override the new operator to enforce that all allocations share a singleton object
        """
        if Display.__instance is None:
            Display.__instance = object.__new__(cls)
        Display.__instance.val = val
        return Display.__instance

    def __init__(self, config):
        threading.Thread.__init__(self, daemon=True)

        self.font = None
        self.main_menu = None
        self.config = config

        self.do_wait = threading.Event()

        self.current_view = None

        # Value between 0.0 and 1.0 used to determine how far each car moves down
        # the screen on each iteration of the display loop. See __race_started() below.
        self.progress_threshold = 0.4
        self.running = True
        self.start()

    def run(self):
        """
        Thread used for actual display updates

        Note, all pyray interactions must be done in this thread as it creates the GL context!
        """
        print("Starting window")
        pr.init_window(240, 240, "Diecast Remote Raceway")
        pr.set_target_fps(30)
        pr.hide_cursor()

        self.main_menu = MainMenuView()
        self.current_view = self.main_menu

        self.font = pr.load_font("fonts/Roboto-Black.ttf")
        # self.menu = Menu(self.font, self.config)

        # Draw loop
        while self.running and not pr.window_should_close():
            self.do_wait.clear()
            pr.begin_drawing()
            pr.clear_background(RAYWHITE)

            self.current_view.draw(self.config)

            pr.end_drawing()

            # if self.current_view.should_wait():
            # print("View said to wait")
            # self.do_wait.wait()

    def show_main_menu(self):
        self.current_view = self.main_menu

    def go(self):
        self.do_wait.clear()
