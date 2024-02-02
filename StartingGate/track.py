from dataclasses import dataclass

from deviceio import DeviceIO, SERVO, LANE1, LANE2, LANE3, LANE4
from functools import wraps

import time
from abc import ABC, abstractmethod

from views import MainMenuView, ConfigMenuView
from config import Config
import deviceio
from deviceio import DeviceIO, SERVO, LANE1, LANE2, LANE3, LANE4, JOYL, JOYR, JOYD, JOYP, JOYU


# def singleton(orig_cls):
#     orig_new = orig_cls.__new__
#     instance = None
#
#     @wraps(orig_cls.__new__)
#     def __new__(cls, *args, **kwargs):
#         print(f"Looking for instance of {cls}")
#         nonlocal instance
#         if instance is None:
#             print("Instance not found, creating")
#             instance = orig_new(cls, *args, **kwargs)
#         return instance
#
#     orig_cls.__new__ = __new__
#     return orig_cls


class TrackState(ABC):
    '''A track state'''

    @property
    def context(self) -> 'Track':
        return self._context

    @context.setter
    def context(self, context: 'Track'):
        self._context = context

    @abstractmethod
    def enter(self):
        pass

    @abstractmethod
    def exit(self):
        pass

    @abstractmethod
    def loop(self):
        pass

    def handle_event(self, event):
        pass


class StateStack:
    """
    A Stack of states.  The first state added can never be popped off and is
    assumed to be the main menu
    """

    def __init__(self, initial_state):
        self.states = [initial_state]

    def current(self) -> TrackState:
        return self.states[-1]

    def push(self, new_state: TrackState):
        self.states.append(new_state)

    def pop(self) -> TrackState:
        if len(self.states) > 1:
            return self.states.pop()
        return self.current()


class Track:

    def __init__(self, config: Config, device: DeviceIO):
        # self.display = display
        self.config = config
        self.device = device

        self._main_menu = MainMenu()
        self._main_menu.context = self
        # self.states = StateStack(initial_state)
        self.current_state: TrackState = self._main_menu
        self.current_state.enter()

    def set_state(self, new_state: TrackState):
        self.current_state.exit()
        self.current_state = new_state
        self.current_state.enter()

    # def push_state(self, new_state: TrackState):
    #     self.states.current().exit(self)
    #     self.states.push(new_state)
    #     new_state.enter(self)
    #
    # def pop_state(self):
    #     self.states.current().exit(self)
    #     prev = self.states.pop()
    #     prev.enter(self)

    def loop(self):
        # self.states.current().loop(self)
        self.current_state.loop()

    def handle_event(self, event):
        self.current_state.handle_event(event)

    def reset(self):
        pass


# @singleton
class MainMenu(TrackState):

    def __init__(self):
        self.view = MainMenuView()
        self.track = None

    def __start_race(self):
        print('race')

    def __configure(self):
        print('configure')
        self.track.set_state(ConfigureMenu)

    def enter(self):
        self.context.device.push_key_handlers(self.__start_race, deviceio.default_key_2_handler,
                                       self.__configure, deviceio.default_joystick_handler)

    def exit(self):
        self.context.device.pop_key_handlers()

    def loop(self):
        self.view.draw(self.context.config)
        # track.display.show_main_menu()
        # time.sleep(0.1)


class DummyMenu(TrackState):
    pass


# @singleton
class ConfigureMenu(TrackState):
    @dataclass
    class MenuItem:
        label: str
        next_state: TrackState

    def __init__(self):
        self.current_menu_item = 0
        self.menu_items = [
            ConfigureMenu.MenuItem("Track Name", ConfigureMenu),
            ConfigureMenu.MenuItem("# of Lanes", ConfigureMenu),
            ConfigureMenu.MenuItem("Car Icons", ConfigureMenu),
            ConfigureMenu.MenuItem("Circuit Name", ConfigureMenu),
            ConfigureMenu.MenuItem("Race Timeout", ConfigureMenu),
            ConfigureMenu.MenuItem("WiFi Setup", ConfigureMenu),
            ConfigureMenu.MenuItem("Coordinator", ConfigureMenu),
            ConfigureMenu.MenuItem("Servo Limits", ConfigureMenu),
            ConfigureMenu.MenuItem("Reset", ConfigureMenu)
        ]
        self.view = ConfigMenuView()

    def enter(self, track: Track):
        def __joystick_handler(btn):
            print("menu: btn.pin: ", btn.pin, "self.cursor_pos: ", self.current_menu_item)
            if btn.pin == JOYL.pin:
                track.set_state(MainMenu)

        track.device.push_key_handlers(deviceio.default_key_1_handler, deviceio.default_key_2_handler,
                                       deviceio.default_key_2_handler, __joystick_handler)

    def exit(self, track: Track):
        track.device.pop_key_handlers()

    def loop(self, track: Track):
        self.view.draw(track.config, menu_items=self.menu_items[4:])
