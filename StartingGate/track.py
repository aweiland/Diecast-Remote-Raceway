from deviceio import DeviceIO, SERVO, LANE1, LANE2, LANE3, LANE4
from functools import wraps

import time
from abc import ABC

from views import MainMenuView, ConfigMenu
from config import Config
import deviceio

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


class TrackState(ABC):
    '''A track state'''

    def enter(self, track: 'Track'):
        pass

    def exit(self, track: 'Track'):
        pass

    def loop(self, track: 'Track'):
        pass

    def handle_event(self, event):
        pass


class Track:

    def __init__(self, initial_state: TrackState, config: Config, device: DeviceIO):
        # self.display = display
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
        self.current_state.handle_event(event)

    def reset(self):
        pass


@singleton
class MainMenu(TrackState):

    def __init__(self):
        self.view = MainMenuView()

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
        self.view.draw(track.config)
        # track.display.show_main_menu()
        # time.sleep(0.1)


@singleton
class ConfigureMenu(TrackState):

    def __init__(self):
        pass

    def enter(self, track: 'Track'):
        track.device.push_key_handlers(deviceio.default_key_1_handler, deviceio.default_key_2_handler,
                                       deviceio.default_key_2_handler, deviceio.default_joystick_handler)

    def exit(self, track: Track):
        track.device.pop_key_handlers()

    def loop(self, track):
        track.display.show_main_menu()
        time.sleep(0.1)
