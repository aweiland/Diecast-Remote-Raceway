import asyncio
import math
import threading
from dataclasses import dataclass

from deviceio import DeviceIO, SERVO, LANE1, LANE2, LANE3, LANE4
from functools import wraps

import time
import random
import select
import bluetooth
from abc import ABC, abstractmethod

from views import MainMenuView, ConfigMenuView, WaitForFinishView, CountdownView, RaceRunningView, WaitForCarsView
from config import Config
import deviceio
from deviceio import DeviceIO, SERVO, LANE1, LANE2, LANE3, LANE4, JOYL, JOYR, JOYD, JOYP, JOYU

READ_ONLY = select.POLLIN | select.POLLPRI | select.POLLHUP | select.POLLERR


def purge_bluetooth_messages(socket):
    """ Read any residual data from the Finish Line bluetooth connection.

    Before adding the BGIN/ENDR message exchange to prevent the finish line
    from sending results when something passed over a lane when no race was
    active, this purge was critical. Otherwise pending messages (for example
    from someone picking up a car from the finish line) would register before
    a car actually reached the finish line.

    Now reading data should be rare and probably indicates a problem in the
    finish line's debounce logic for the IR sensors. Nevertheless, a millisecond
    delay to read any outstanding data on the socket seems like a reasonable
    defensive act.
    """

    prior_timeout = socket.gettimeout()
    socket.settimeout(0.01)  # wait 1ms for any residual messages
    try:
        socket.recv(1024)  # Purge any messages from the Finish Line
    except bluetooth.btcommon.BluetoothError as exc:
        if exc.args[0] == 'timed out':
            print("purge_bluetooth_messages(): BluetoothError = timed out, ignoring.")
        else:
            # Re raise any other bluetooth exception so the main loop will reconnect
            print("purge_bluetooth_messages(): BluetoothError, other reason =", exc.args)
            raise exc
    socket.settimeout(prior_timeout)


def reset_starting_gate(config):
    """ Set servo to midpoint position to close the starting gate """
    SERVO.value = config.servo_up_value
    time.sleep(0.1)
    SERVO.value = None  # Stop PWM signal to servo to prevent humm/jitter and reduce wear


def release_starting_gate(config):
    """ Set servo to max position to release the starting gate """
    SERVO.value = config.servo_down_value


class TrackState(ABC):
    '''A track state'''

    def __init__(self):
        self._context = None

    @property
    def context(self) -> 'Track':
        return self._context

    @context.setter
    def context(self, context: 'Track'):
        self._context = context

    def enter(self):
        pass

    def exit(self):
        pass

    @abstractmethod
    def loop(self):
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

        self.socket = None
        self.poller = select.poll()

        self._main_menu = MainMenu()
        self._main_menu.context = self

        self._configure_menu = ConfigureMenu()
        self._configure_menu.context = self

        self._wait_for_finish = WaitForFinish()
        self._wait_for_finish.context = self

        self._wait_for_cars = WaitForCars()
        self._wait_for_cars.context = self

        self._countdown = Countdown()
        self._countdown.context = self

        self._race_running = RaceRunning()
        self._race_running.context = self

        # self.states = StateStack(initial_state)
        self.current_state: TrackState = self._main_menu
        self.current_state.enter()

    def set_state(self, new_state: TrackState):
        self.current_state.exit()
        new_state.enter()
        self.current_state = new_state

    def loop(self):
        # self.states.current().loop(self)
        self.current_state.loop()

    def reset(self):
        self.set_state(self._main_menu)

    def main_menu(self):
        self.set_state(self._main_menu)

    def wait_for_finish(self):
        self.set_state(self._wait_for_finish)

    def wait_for_cars(self):
        self.set_state(self._wait_for_cars)

    def countdown(self):
        self.set_state(self._countdown)

    def configure_menu(self):
        self.set_state(self._configure_menu)

    def run_race(self):
        self.set_state(self._race_running)


class MainMenu(TrackState):

    def __init__(self):
        super().__init__()
        self.view = MainMenuView()
        self.track = None

    def __start_race(self):
        print('race')
        self.context.wait_for_finish()

    def __configure(self):
        print('configure')
        self.context.configure_menu()

    def enter(self):
        self.context.device.push_key_handlers(self.__start_race, deviceio.default_key_2_handler,
                                              self.__configure, deviceio.default_joystick_handler)

    def exit(self):
        self.context.device.pop_key_handlers()

    def loop(self):
        self.view.draw(self.context.config)


class WaitForFinish(TrackState):

    def __init__(self):
        super().__init__()
        self.view = WaitForFinishView()

    def enter(self):
        print("Waiting for finish line...")

        # clear old socket if exists
        if self.context.socket is not None:
            self.context.poller.unregister(self.context.socket)

    def loop(self):
        self.view.draw(self.context.config)

        target_address = None
        port = 1

        nearby_devices = bluetooth.discover_devices()

        for bdaddr in nearby_devices:
            if self.context.config.finish_line_name == bluetooth.lookup_name(bdaddr):
                target_address = bdaddr
                break

        if target_address is None:
            print("could not find ", self.context.config.finish_line_name, " nearby")
        else:
            print("Found ", self.context.config.finish_line_name, ", connecting...")
            socket = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
            socket.connect((target_address, port))
            self.context.poller.register(socket, READ_ONLY)
            self.context.socket = socket
            print("Connected to finish line")
            socket.send("HELO")

            self.context.wait_for_cars()


class WaitForCars(TrackState):
    """Wait for cars to be places on track sensors"""
    def __init__(self):
        super().__init__()
        self.lanes = [LANE1, LANE2, LANE3, LANE4]
        self.view = WaitForCarsView()

    def _all_lanes_ready(self):
        ready = True
        for x in range(self.context.config.num_lanes):
            ready = ready and self.lanes[x].value == 1

        return ready

    def enter(self):
        print("Waiting for cars")

    def loop(self):
        """ Scan the lane sensors to see if all lanes have cars present. """
        if self._all_lanes_ready():
            self.context.countdown()

        car_status = [lane.value == 1 for lane in self.lanes]
        self.view.draw(self.context.config, car_status=car_status)


class Countdown(TrackState):
    def __init__(self):
        super().__init__()
        self.start_time = 0
        self.view = CountdownView()

    def enter(self):
        print("Starting countdown")
        self.start_time = time.monotonic()
        self.view.load_car_images(self.context.config)
        print("Done loading car images")

    def loop(self):
        timer = 3 - math.floor(time.monotonic() - self.start_time)
        self.view.draw(self.context.config, timer=timer)


class RaceRunning(TrackState):

    def __init__(self):
        super().__init__()
        self.race_aborted = False
        self.start_time = 0
        self.view = RaceRunningView()
        self.car_positions = [0] * 4
        self.progress_threshold = 0.4

    def enter(self):
        self.start_time = time.monotonic()
        self.race_aborted = False
        self.start_time = 0
        self.car_positions = [0] * 4

        self.context.socket.send("BGIN")

        purge_bluetooth_messages(self.context.socket)

        print("Start the race!")
        release_starting_gate(self.context.config)

    def exit(self):
        pass

    def loop(self):
        delta = time.monotonic() - self.start_time

        for car in range(self.context.config.num_lanes):
            if random.random() < self.progress_threshold and self.car_positions[car] < self.view.MAX_Y:
                self.car_positions[car] += 1

        if not all_lanes_finished() and not self.race_aborted and time.monotonic_ns() < timeout:
            try:
                events = self.context.poller.poll(100)
                if events:
                    data = self.context.socket.recv(5)

                    msg = data.decode('utf-8')
                    print("received ", msg)

                    if msg.startswith("FIN"):
                        lane_finished(lane_index(msg), finish_times)

            except bluetooth.btcommon.BluetoothError as exc:
                if exc.args[0] == 'timed out':
                    print("Timeout waiting for race results. Finishing race")
                else:
                    print("purge_bluetooth_messages(): BluetoothError, other reason =", exc.args)
                    raise exc
        else:
            self.context.socket.send("ENDR")
            self.context.race_finished()

        # Send end of race message to Finish Line to disable further completion messages

        # for car in range(self.config.remote_num_lanes):
        #     if random.random() < self.progress_threshold and self.remote_y[car] < Display._MAX_Y:
        #         self.remote_y[car] += 1

        self.view.draw(self.context.config, car_positions=self.car_positions, time_delta=delta)


class RaceFinished(TrackState):

    def enter(self):
        pass

    def exit(self):
        pass

    def loop(self):
        pass


class DummyMenu(TrackState):
    def enter(self):
        pass

    def exit(self):
        pass

    def loop(self):
        pass


# @singleton
class ConfigureMenu(TrackState):
    @dataclass
    class MenuItem:
        label: str
        next_state: TrackState

    def __init__(self):
        super().__init__()
        self.current_menu_item = 0
        self.menu_items = [
            ConfigureMenu.MenuItem("Track Name", DummyMenu()),
            ConfigureMenu.MenuItem("# of Lanes", DummyMenu()),
            ConfigureMenu.MenuItem("Car Icons", DummyMenu()),
            ConfigureMenu.MenuItem("Circuit Name", DummyMenu()),
            ConfigureMenu.MenuItem("Race Timeout", DummyMenu()),
            ConfigureMenu.MenuItem("WiFi Setup", DummyMenu()),
            ConfigureMenu.MenuItem("Coordinator", DummyMenu()),
            ConfigureMenu.MenuItem("Servo Limits", DummyMenu()),
            ConfigureMenu.MenuItem("Reset", DummyMenu())
        ]
        self.view = ConfigMenuView()

    def enter(self):
        def __joystick_handler(btn):
            print("menu: btn.pin: ", btn.pin, "self.cursor_pos: ", self.current_menu_item)
            if btn.pin == JOYL.pin:
                self.context.main_menu()

        self.context.device.push_key_handlers(deviceio.default_key_1_handler, deviceio.default_key_2_handler,
                                              deviceio.default_key_2_handler, __joystick_handler)

    def exit(self):
        self.context.device.pop_key_handlers()

    def loop(self):
        self.view.draw(self.context.config, menu_items=self.menu_items[4:])


def run_track(track):
    while True:
        track.loop()


def run_race(track):
    time.sleep(2)
    track.main_menu()
    time.sleep(2)
    track.wait_for_finish()
    time.sleep(2)
    track.countdown()


def run_sample_race():
    from v2 import init_display

    config = Config("/home/aweiland/StartingGate/config/starting_gate.json")
    # display = Display(config)
    init_display()
    device = DeviceIO()
    track = Track(config, device)

    # t = threading.Thread(target=run_race, args=(track,))
    # t.start()

    time.sleep(2)
    track.main_menu()
    track.loop()
    time.sleep(2)
    track.wait_for_finish()
    track.loop()
    time.sleep(2)

    track.countdown()
    track.loop()
    time.sleep(1)
    track.loop()
    time.sleep(1)
    track.loop()

    time.sleep(3)

    # while True:
    #     track.loop()
    #     pass

    # loop = asyncio.create_task(run_track(track))
    # await asyncio.gather(
    #     run_race(track),
    #     run_track(track),
    # )
    # async with asyncio.TaskGroup as tg:
    #     tg.create_task(run_race(track))
    #     tg.create_task(run_race(track))


if __name__ == '__main__':
    run_sample_race()
    # asyncio.run(run_sample_race())
