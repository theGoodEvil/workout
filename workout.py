#!/usr/bin/env python

import collections
import itertools
import operator
import time

from cocos.director import director
from cocos.layer import Layer, ColorLayer
from cocos.scene import Scene
from cocos.sprite import Sprite
from cocos.text import HTMLLabel
from cocos.utils import SequenceScene

import pyglet


def pairwise(iterable):
    a, b = itertools.tee(iterable)
    next(b, None)
    return itertools.izip(a, b)


def make_html(text, color="black"):
    return '<center><h1><font face="8BIT WONDER" color="%s">%s</font></h1></center>' % (color, text)


class Pulse(pyglet.event.EventDispatcher):
    def __init__(self, num_ticks=4):
        super(Pulse, self).__init__()
        self.num_ticks = num_ticks
        self.ticks = collections.deque([], num_ticks)
        self.set_rate(0)

    def tick(self):
        pyglet.clock.unschedule(self.reset_rate)
        self.ticks.append(time.time())
        self.set_rate(self.compute_rate())
        pyglet.clock.schedule_once(self.reset_rate, 2)

    def reset_rate(self, delta_time):
        self.set_rate(0)

    def set_rate(self, rate):
        self.rate = rate
        self.dispatch_event("on_rate_changed", rate)

    def compute_rate(self):
        if len(self.ticks) < self.num_ticks:
            return 0
        else:
            diffs = map(lambda t: t[1] - t[0], pairwise(self.ticks))
            return len(diffs) / sum(diffs) * 60


Pulse.register_event_type("on_rate_changed")


class Player(object):
    def __init__(self, key):
        self.key = key
        self.pulse = Pulse()

    def trigger(self):
        self.pulse.tick()


class InstructorLayer(Layer):
    def __init__(self):
        super(InstructorLayer, self).__init__()

        self.label = HTMLLabel(
            make_html(""),
            width=240,
            anchor_x="center",
            anchor_y="center",
            multiline=True
        )

        self.label.position = (120, 260)
        self.add(self.label)

    def set_text(self, text):
        self.label.element.text = make_html(text)


class HeartbeatLayer(Layer):
    is_event_handler = True

    HEART_SIZE_SMALL = 0.2
    HEART_SIZE_BIG = 0.25
    HEART_BEAT = pyglet.media.load("heartbeat.wav", streaming=False)

    def __init__(self, player):
        super(HeartbeatLayer, self).__init__()
        self.player = player

        self.heart = Sprite("heart.png")
        self.heart.position = (120, 120)
        self.heart.scale = self.HEART_SIZE_SMALL
        self.add(self.heart)

    def on_key_press(self, key, modifiers):
        if key == self.player.key:
            self.HEART_BEAT.play()
            self.heart.scale = self.HEART_SIZE_BIG
            self.player.trigger()

    def on_key_release(self, key, modifiers):
        self.heart.scale = self.HEART_SIZE_SMALL


class RateLayer(Layer):
    def __init__(self, player):
        super(RateLayer, self).__init__()

        self.label = HTMLLabel(
            make_html("0"),
            width=240,
            anchor_x="center",
            anchor_y="center",
            multiline=True
        )

        self.label.position = (120, 260)
        self.add(self.label)

        @player.pulse.event
        def on_rate_changed(rate):
            rate_string = "%3.0f" % rate
            self.label.element.text = make_html(rate_string)


class PlayerLayer(ColorLayer):
    WORKOUT_COLOR = (22, 232, 247)
    WARNING_COLOR = (255, 0, 0)

    def __init__(self, player, level, position):
        super(PlayerLayer, self).__init__(0, 0, 0, 255, width=240, height=320)
        self.color = self.WORKOUT_COLOR
        self.player = player
        self.level = level
        self.position = position

        self.instuctor_layer = InstructorLayer()
        self.instuctor_layer.visible = False
        self.add(self.instuctor_layer)

        self.rate_layer = RateLayer(player)
        self.add(self.rate_layer)

        self.heartbeat_layer = HeartbeatLayer(player)
        self.add(self.heartbeat_layer)

    def instruct(self):
        rate = self.player.pulse.rate
        self.level.instruct(rate, self.show_instructor)

    def show_instructor(self, text="", show=True, color=WORKOUT_COLOR):
        self.instuctor_layer.set_text(text)
        self.instuctor_layer.visible = show
        self.rate_layer.visible = not show
        self.color = color

        if show:
            pyglet.clock.schedule_once(self.hide_instructor, 1)

    def hide_instructor(self, delta_time):
        self.show_instructor(show=False)


class ProgressBar(ColorLayer):
    def __init__(self):
        super(ProgressBar, self).__init__(128, 128, 128, 255, width=480, height=16)
        self.progress = ColorLayer(64, 64, 64, 255, width=0, height=16)
        self.add(self.progress)

    def set_progress(self, progress):
        self.progress.width = int(progress * 480)


class WorkoutLayer(Layer):
    def __init__(self, make_level):
        super(WorkoutLayer, self).__init__()

        self.player_layers = [
            PlayerLayer(Player(pyglet.window.key.S), make_level(), (0, 0)),
            PlayerLayer(Player(pyglet.window.key.L), make_level(), (240, 0))
        ]

        map(self.add, self.player_layers)

        self.progress_bar = ProgressBar()
        self.progress_bar.set_progress(0.4)
        self.add(self.progress_bar)

        self.schedule_interval(self.instruct, 4)

    def instruct(self, delta_time):
        map(operator.methodcaller("instruct"), self.player_layers)


class TextLayer(ColorLayer):
    is_event_handler = True

    def __init__(self, text):
        super(TextLayer, self).__init__(255, 0, 0, 255)

        label = HTMLLabel(
            make_html(text, color="white"),
            width=480,
            anchor_x="center",
            anchor_y="center",
            multiline=True
        )

        label.position = (240, 160)
        self.add(label)

    def on_key_press(self, key, modifiers):
        director.pop()


class Level(object):
    def instruct(self, rate, show_instructor):
        raise NotImplementedError


class WarmUp(Level):
    def __init__(self):
        self.slow_warnings = collections.deque([
            "FASTER",
            "ARE YOU KIDDING ME",
            "MAN UP"
        ])

        self.fast_warnings = collections.deque([
            "SLOW DOWN",
            "EASY"
        ])

    def instruct(self, rate, show_instructor):
        if rate < 120:
            show_instructor(
                text=self.slow_warnings[0],
                color=PlayerLayer.WARNING_COLOR
            )
            self.slow_warnings.rotate(-1)
        elif rate > 140:
            show_instructor(
                text=self.fast_warnings[0],
                color=PlayerLayer.WARNING_COLOR
            )
            self.fast_warnings.rotate(-1)
        else:
            show_instructor(text="PERFECT")


if __name__ == "__main__":
    pyglet.font.add_file('8-bit wonder.ttf')
    director.init(width=480, height=320)

    scenes = map(Scene, [
        TextLayer("WORKOUT"),
        TextLayer("HELLO<br/>MY NAME IS ARNOLD"),
        TextLayer("I AM YOUR INSTRUCTOR"),
        TextLayer("WARM UP<br/>120-140 BPM"),
        WorkoutLayer(WarmUp)
    ])

    # workaround for pyglet refresh issue
    pyglet.clock.schedule(lambda dt: None)

    director.run(SequenceScene(*scenes))
