from dataclasses import dataclass
from abc import ABC, abstractmethod
from typing import Type
import pyray as pr
from pyray import WHITE, RAYWHITE, GRAY, BLACK, ORANGE, LIGHTGRAY
from config import Config


def load_texture(filename):
    img = pr.load_image(filename)
    texture = pr.load_texture_from_image(img)
    pr.unload_image(img)
    return texture


class View(ABC):
    def __init__(self):
        self.font = pr.load_font_ex("fonts/Roboto-Black.ttf", 32, None, 0)

    def draw(self, config, **kwargs):
        pr.begin_drawing()
        pr.clear_background(RAYWHITE)
        self._draw(config, **kwargs)

        pr.end_drawing()

    @abstractmethod
    def _draw(self, config, **kwargs):
        assert 0, "draw not implemented"

    def _text_box(self, text, x, y, width, height, size, gray=False):
        """
        Draw a box at position (x,y) with specified width and height.
        Display text with point size size within the box.
        If gray=True, set the box fill color to gray and the text color to white
        """
        if gray:
            pr.draw_rectangle(x, y, width, height, LIGHTGRAY)
        else:
            pr.draw_rectangle(x, y, width, height, WHITE)
        pr.draw_rectangle_lines(x, y, width, height, BLACK)
        pr.draw_text_ex(self.font, text, pr.Vector2(x + 10, y + 2), size, 5, BLACK)

    def _menu_line(self, text, x, y, width, height, size):
        """
        Display line of menu text corresponding to specified MenuState location
        """
        self._text_box(text, x, y, width, height, size, False)

    def _text_message(self, text, inverted=False):
        if len(text) >= 16:
            # Two line text box
            self._text_box(text, 10, 90, 215, 68, self.__font_size(text), inverted)
        else:
            # One line textbox
            self._text_box(text, 10, 90, 215, 40, self.__font_size(text), inverted)

    @staticmethod
    def __font_size(text):
        """
        Compute font size that will fit within text box based on length of text string
        """
        length = len(text)
        if length <= 14:
            return 34
        if length < 30:
            return 26
        return 24


class TrackView(View, ABC):
    '''A View that has a track on it'''

    def __init__(self):
        super().__init__()
        self.background_texture = load_texture("images/raceoff-2.png")
        self.checkerboard_small_texture = load_texture("images/checkerboard-34.png")
        self.checkerboard_large_texture = load_texture("images/checkerboard-64.png")
        self.question_small_texture = load_texture("cars/question-24.png")
        self.question_large_texture = load_texture("cars/question-48.png")

        self.car_textures = [None] * 4

    def load_car_images(self, config: Config):
        # cleanup existing textures (if they exist)
        for texture in self.car_textures:
            if texture:
                pr.unload_texture(texture)

        for car in range(4):
            car_icon_size = 24
            icon = config.car_icons[car]
            self.car_textures[car] = load_texture("cars/{}-{}.png".format(icon, car_icon_size))

    def _draw_background(self, config):
        pr.draw_texture(self.background_texture, 0, 0, WHITE)
        self._draw_lanes(config)

    def _draw_lanes(self, config):
        if config.multi_track:
            pr.draw_text(config.track_name, 10, 10, 24, ORANGE)
            pr.draw_text(config.remote_track_name, 130, 10, 24, BLACK)
            pr.draw_line_ex([120, 5], [120, 235], 4.0, BLACK)

            pr.draw_line_ex([35, 40], [35, 230], 34.0, ORANGE)
            pr.draw_line_ex([80, 40], [80, 230], 34.0, ORANGE)

            pr.draw_texture(self.checkerboard_small_texture, 18, 196, WHITE)
            pr.draw_texture(self.checkerboard_small_texture, 63, 196, WHITE)

            pr.draw_line_ex([155, 40], [155, 230], 34.0, ORANGE)
            pr.draw_line_ex([200, 40], [200, 230], 34.0, ORANGE)

            pr.draw_texture(self.checkerboard_small_texture, 138, 196, WHITE)
            pr.draw_texture(self.checkerboard_small_texture, 183, 196, WHITE)
        else:
            pr.draw_line_ex([35, 40], [35, 230], 34.0, ORANGE)
            pr.draw_line_ex([80, 40], [80, 230], 34.0, ORANGE)

            pr.draw_texture(self.checkerboard_small_texture, 18, 196, WHITE)
            pr.draw_texture(self.checkerboard_small_texture, 63, 196, WHITE)

            pr.draw_line_ex([155, 40], [155, 230], 34.0, ORANGE)
            pr.draw_line_ex([200, 40], [200, 230], 34.0, ORANGE)

            pr.draw_texture(self.checkerboard_small_texture, 138, 196, WHITE)
            pr.draw_texture(self.checkerboard_small_texture, 183, 196, WHITE)
            # pr.draw_line_ex([64, 10], [64, 230], 64.0, ORANGE)
            # pr.draw_line_ex([164, 10], [164, 230], 64.0, ORANGE)

            # pr.draw_texture(self.checkerboard_texture, 32, 166, WHITE)
            # pr.draw_texture(self.checkerboard_texture, 132, 166, WHITE)

    def _draw_cars(self, config, car_positions, car_status=None):
        # pylint: disable=bad-whitespace
        if car_status is None:
            car_status = [True, True, True, True]

        if config.num_lanes < 3:
            question_texture = self.question_large_texture
        else:
            question_texture = self.question_small_texture

        car_textures = [self.car_textures[ind] if status else question_texture for ind, status in enumerate(car_status)]

        if config.multi_track:
            # FIXME
            pr.draw_texture(car_textures[0], 22, car_positions[0], WHITE)
            pr.draw_texture(car_textures[1], 68, car_positions[1], WHITE)
            pr.draw_texture(car_textures[2], 142, car_positions[2], WHITE)
            pr.draw_texture(car_textures[3], 188, car_positions[3], WHITE)
        else:
            # pr.draw_texture(texture1,  40, self.local_y[CAR1],  WHITE)
            # pr.draw_texture(texture2, 140, self.local_y[CAR2],  WHITE)
            pr.draw_texture(car_textures[0], 22, car_positions[0], WHITE)
            pr.draw_texture(car_textures[1], 68, car_positions[1], WHITE)
            pr.draw_texture(car_textures[2], 142, car_positions[2], WHITE)
            pr.draw_texture(car_textures[3], 188, car_positions[3], WHITE)


class DummyView(View):

    def draw(self):
        self._text_box("Hi", 10, 10, 10, 10, 8)


class MainMenuView(View):

    def __init__(self):
        super().__init__()
        print("Loading main menu textures")

        background_image = pr.load_image("images/background.png")
        self.background_texture = pr.load_texture_from_image(background_image)
        pr.unload_image(background_image)

        single_track_image = pr.load_image("images/Single-Track.png")
        self.single_track_texture = pr.load_texture_from_image(single_track_image)
        pr.unload_image(single_track_image)

        multi_track_image = pr.load_image("images/Multi-Track.png")
        self.multi_track_texture = pr.load_texture_from_image(multi_track_image)
        pr.unload_image(multi_track_image)

        configure_image = pr.load_image("images/Configure.png")
        self.configure_texture = pr.load_texture_from_image(configure_image)
        pr.unload_image(configure_image)

    def _draw(self, config: Config, **kwargs):
        pr.draw_texture(self.background_texture, 0, 0, WHITE)

        pr.draw_texture(self.single_track_texture, 10, 45, WHITE)

        if config.allow_multi_track:
            pr.draw_texture(self.multi_track_texture, 10, 100, WHITE)
        else:
            pr.draw_texture(self.multi_track_texture, 10, 100, LIGHTGRAY)

        pr.draw_texture(self.configure_texture, 10, 155, WHITE)


class WaitForFinishView(TrackView):

    def _draw(self, config, **kwargs):
        self._draw_background(config)
        self._text_message("Connecting to " + config.finish_line_name)


class WaitForCarsView(TrackView):

    def _draw(self, config, **kwargs):
        car_status = kwargs['car_status']
        self._draw_background(config)
        self._draw_cars(config, [0, 0, 0, 0], car_status)


class CountdownView(TrackView):
    def _draw(self, config, **kwargs):
        self._draw_background(config)
        self._draw_cars(config, [0, 0, 0, 0])
        timer = kwargs['timer']
        self._text_message(f"Starting in {timer}")


class RaceRunningView(TrackView):

    MAX_Y = 150

    def _draw(self, config, **kwargs):
        car_positions = kwargs['car_positions']
        time_delta = kwargs['time_delta']
        delta_bytes = bytes('{:06.3f}'.format(time_delta), 'ascii')

        self._draw_cars(config, car_positions)
        self._text_box(delta_bytes, 26, 95, 180, 55, 50)
        pass


class ConfigMenuView(View):

    def __init__(self):
        super().__init__()
        # self.menu_items = [
        #     MenuItem("Track Name", DummyView),
        #     MenuItem("# of Lanes", DummyView),
        #     MenuItem("Car Icons", DummyView),
        #     MenuItem("Circuit Name", DummyView),
        #     MenuItem("Race Timeout", DummyView),
        #     MenuItem("WiFi Setup", DummyView),
        #     MenuItem("Coordinator Setup", DummyView),
        #     MenuItem("Servo Limits", DummyView),
        #     MenuItem("Reset", DummyView)
        # ]
        # self.menu_items = [
        #     "Track Name",
        #     "# of Lanes",
        #     "Car Icons",
        #     "Circuit Name",
        #     "Race Timeout",
        #     "WiFi Setup",
        #     "Coordinator Setup",
        #     "Servo Limits",
        #     "Reset"
        # ]

    def _draw(self, config, **kwargs):
        for idx, menu in enumerate(kwargs['menu_items']):
            self._menu_line(menu.label, 10, idx * 56 + 16, 210, 40, 26)

    # def __menu_line(self, text, x, y, width, height, size):
    #     """
    #     Display line of menu text corresponding to specified MenuState location
    #     """
    #     self.__text_box(text, x, y, width, height, size)
    #
    # def __text_box(self, text, x, y, width, height, size, gray=False):
    #     """
    #     Draw a box at position (x,y) with specified width and height.
    #     Display text with point size size within the box.
    #     If gray=True, set the box fill color to gray and the text color to white
    #     """
    #     if gray:
    #         pr.draw_rectangle(x, y, width, height, LIGHTGRAY)
    #     else:
    #         pr.draw_rectangle(x, y, width, height, WHITE)
    #     pr.draw_rectangle_lines(x, y, width, height, BLACK)
    #     pr.draw_text_ex(self.font, text, pr.Vector2(x+10, y+2), size, 5, BLACK)
