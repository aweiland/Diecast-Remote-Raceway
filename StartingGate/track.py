import asyncio
import math
import operator
import threading
from dataclasses import dataclass

from deviceio import DeviceIO, SERVO, LANE1, LANE2, LANE3, LANE4
from functools import wraps

import time
import random
import select
import bluetooth
from abc import ABC, abstractmethod

from views import MainMenuView, ConfigMenuView, WaitForFinishView, CountdownView, RaceRunningView, WaitForCarsView, \
    ResultsView
from config import Config, NOT_FINISHED
import deviceio
from deviceio import DeviceIO, SERVO, LANE1, LANE2, LANE3, LANE4, JOYL, JOYR, JOYD, JOYP, JOYU
from starting_gate import purge_bluetooth_messages, reset_starting_gate, all_lanes_ready, all_lanes_empty, \
    release_starting_gate, NANOSECONDS_TO_SECONDS

READ_ONLY = select.POLLIN | select.POLLPRI | select.POLLHUP | select.POLLERR


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


class Track:

    def __init__(self, config: Config, device: DeviceIO):
        # self.display = display
        self.config = config
        self.device = device

        self.socket = None
        self.poller = select.poll()
        self.car_positions = [0] * 4
        self.finish_times = [NOT_FINISHED] * 4

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

        self._race_finished = RaceFinished()
        self._race_finished.context = self

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

    def race_finished(self):
        self.set_state(self._race_finished)


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

        print("Looking for BT devices")
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


def lane_index(msg):
    """
    Convert finished message received from the Finish Line to a lane index.

    Lanes are named Lane1 through Lane4, but arrays are zero indexed.  So the "FIN1"
    message indicates that the lane with an index position of 0 is finished.
    """
    lane_number = int(msg[3])
    return lane_number - 1


class RaceRunning(TrackState):

    def __init__(self):
        super().__init__()
        self.race_aborted = False
        self.start_time = 0
        self.timeout = 0
        self.view = RaceRunningView()
        self.car_positions = [0] * 4
        self.progress_threshold = 0.4

    def enter(self):
        self.start_time = time.monotonic()
        self.race_aborted = False
        self.car_positions = [0] * 4
        self.context.finish_times = [NOT_FINISHED] * 4

        self.timeout = (self.start_time + self.context.config.race_timeout) * NANOSECONDS_TO_SECONDS

        # Prevent errors when running a demo
        if self.context.socket:
            self.context.socket.send("BGIN")
            purge_bluetooth_messages(self.context.socket)

        self.view.load_car_images(self.context.config)

        print("Start the race!")
        release_starting_gate(self.context.config)

    def lane_finished(self, lane):
        """
        Record the finish time for the specified lane in the times array
        """
        if self.context.finish_times[lane] != NOT_FINISHED:
            print("lane ", lane + 1, " reported redundant finish")
            return

        end = time.monotonic_ns()
        delta = float(end - self.start_time) / NANOSECONDS_TO_SECONDS
        print("Lane %d finished. Elapsed time: %6.3f" % (lane + 1, delta))
        self.context.finish_times[lane] = delta

    def all_lanes_finished(self):
        """
        Returns True if all configured lanes have finished.  False otherwise.
        """
        for lane in range(self.context.config.num_lanes):
            if self.context.finish_times[lane] == NOT_FINISHED:
                return False
        return True

    def loop(self):
        delta = time.monotonic() - self.start_time

        for car in range(self.context.config.num_lanes):
            if random.random() < self.progress_threshold and self.car_positions[car] < self.view.MAX_Y:
                # print("Incrementing car")
                self.car_positions[car] += 5

        if not self.all_lanes_finished() and not self.race_aborted and time.monotonic() < self.timeout:
            try:
                events = self.context.poller.poll(100)
                if events:
                    data = self.context.socket.recv(5)

                    msg = data.decode('utf-8')
                    print("received ", msg)

                    if msg.startswith("FIN"):
                        self.lane_finished(lane_index(msg), self.context.finish_times)

            except bluetooth.btcommon.BluetoothError as exc:
                if exc.args[0] == 'timed out':
                    print("Timeout waiting for race results. Finishing race")
                    self.context.race_finished()
                else:
                    print("purge_bluetooth_messages(): BluetoothError, other reason =", exc.args)
                    raise exc
        else:
            print(
                f"finished {self.all_lanes_finished()}, aborted {self.race_aborted}, timeout at {time.monotonic_ns()} < {self.timeout}")
            self.context.socket.send("ENDR")
            self.context.car_positions = self.car_positions
            self.context.race_finished()

        self.view.draw(self.context.config, car_positions=self.car_positions, time_delta=delta)

        # Send end of race message to Finish Line to disable further completion messages

        # for car in range(self.config.remote_num_lanes):
        #     if random.random() < self.progress_threshold and self.remote_y[car] < Display._MAX_Y:
        #         self.remote_y[car] += 1


class RaceFinished(TrackState):
    @dataclass
    class FinishData:
        track_name: str
        lane_number: int
        lane_time: float

    def __init__(self):
        super().__init__()
        self.view = ResultsView()
        self.results = []

    def enter(self):
        results = []
        for lane in range(self.context.config.num_lanes):
            # result = {}
            # result["trackName"] = self.context.config.track_name
            # result["laneNumber"] = lane + 1
            # result["laneTime"] = self.context.finish_times[lane]
            # results.append(result)
            results.append(RaceFinished.FinishData(
                track_name=self.context.config.track_name,
                lane_number=lane + 1,
                lane_time=self.context.finish_times[lane]
            ))

        # results.sort(key=operator.itemgetter('laneTime'))
        results.sort(key=lambda result: result.lane_time)
        self.results = results
        self.view.load_car_images(self.context.config)

    def loop(self):
        self.view.draw(self.context.config, results=self.results)


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


def run_sample_race():
    from v2 import init_display

    config = Config("/home/aweiland/StartingGate/config/starting_gate.json")
    init_display()
    device = DeviceIO()
    track = Track(config, device)

    time.sleep(2)
    track.main_menu()
    track.loop()
    time.sleep(2)
    # track.wait_for_finish()
    # track.loop()
    # time.sleep(2)

    track.wait_for_cars()
    track.loop()
    time.sleep(1)

    track.countdown()
    track.loop()
    time.sleep(1)
    track.loop()
    time.sleep(1)
    track.loop()

    track.run_race()
    for x in range(5):
        track.loop()
        time.sleep(0.01)
    time.sleep(1)

    track.finish_times = [5.0, 2.3, 6.0, 4.2]
    track.race_finished()
    track.loop()
    time.sleep(15)


if __name__ == '__main__':
    run_sample_race()
