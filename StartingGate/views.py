from dataclasses import dataclass
from abc import ABC
from typing import Type
import pyray as pr
from pyray import WHITE, RAYWHITE, GRAY, BLACK, ORANGE, LIGHTGRAY

class View(ABC):
    def __init__(self):
        self.font = pr.load_font_ex("fonts/Roboto-Black.ttf", 32, None, 0)

    def draw(self, config, **kwargs):
        pr.begin_drawing()
        pr.clear_background(RAYWHITE)
        self._draw(config, **kwargs)

        pr.end_drawing()

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

    def _draw(self, config, **kwargs):
        pr.draw_texture(self.background_texture, 0, 0, WHITE)

        pr.draw_texture(self.single_track_texture, 10, 45, WHITE)

        if config.allow_multi_track:
            pr.draw_texture(self.multi_track_texture, 10, 100, WHITE)
        else:
            pr.draw_texture(self.multi_track_texture, 10, 100, LIGHTGRAY)

        pr.draw_texture(self.configure_texture, 10, 155, WHITE)


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
            self._menu_line(menu.label, 10, idx*56+16, 210, 40, 26)


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
