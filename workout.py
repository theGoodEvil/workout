#!/usr/bin/env python

import collections
import itertools
import time

import cocos
from cocos.director import director
import pyglet


def pairwise(iterable):
    a, b = itertools.tee(iterable)
    next(b, None)
    return itertools.izip(a, b)


def make_html(text, color="black"):
    return '<center><h1><font face="8BIT WONDER" color="%s">%s</font></h1></center>' % (color, text)


class Pulse(object):
    def __init__(self, num_events=4):
        self.num_events = num_events
        self.events = collections.deque([], num_events)

    def tick(self):
        self.events.append(time.time())

    def rate(self):
        if len(self.events) < self.num_events:
            return 0
        else:
            diffs = map(lambda t: t[1] - t[0], pairwise(self.events))
            return len(diffs) / sum(diffs) * 60


class Player(object):
    def __init__(self, key):
        self.key = key
        self.pulse = Pulse()

    def trigger(self):
        self.pulse.tick()


class InstructorLayer(cocos.layer.Layer):
    def __init__(self):
        super(InstructorLayer, self).__init__()

        self.label = cocos.text.HTMLLabel(
            make_html(""),
            width=240,
            anchor_x="center",
            anchor_y="center",
            multiline=True
        )

        self.label.position = (120, 280)
        self.add(self.label)

    def set_text(self, text):
        self.label.element.text = make_html(text)


class HeartbeatLayer(cocos.layer.Layer):
    is_event_handler = True

    HEART_SIZE_SMALL = 0.2
    HEART_SIZE_BIG = 0.25
    HEART_BEAT = pyglet.media.load("heartbeat.wav", streaming=False)

    def __init__(self, player):
        super(HeartbeatLayer, self).__init__()
        self.player = player

        self.heart = cocos.sprite.Sprite("heart.png")
        self.heart.position = (120, 140)
        self.heart.scale = self.HEART_SIZE_SMALL
        self.add(self.heart)

    def on_key_press(self, key, modifiers):
        if key == self.player.key:
            self.HEART_BEAT.play()
            self.heart.scale = self.HEART_SIZE_BIG
            self.player.trigger()

    def on_key_release(self, key, modifiers):
        self.heart.scale = self.HEART_SIZE_SMALL


class RateLayer(cocos.layer.Layer):
    def __init__(self, player):
        super(RateLayer, self).__init__()
        self.player = player

        self.label = cocos.text.HTMLLabel(
            "",
            width=240,
            anchor_x="center",
            anchor_y="center",
            multiline=True
        )

        self.label.position = (120, 280)
        self.add(self.label)

        self.schedule_interval(self.update, 0.2)

    def update(self, delta_time):
        rate = "%3.0f" % (self.player.pulse.rate())
        self.label.element.text = make_html(rate)


class PlayerLayer(cocos.layer.ColorLayer):
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

        self.schedule_interval(self.instruct, 4)

    def instruct(self, delta_time):
        rate = self.player.pulse.rate()
        self.level.instruct(rate, self.show_instructor)

    def show_instructor(self, text="", show=True, color=WORKOUT_COLOR):
        self.instuctor_layer.set_text(text)
        self.instuctor_layer.visible = show
        self.rate_layer.visible = not show
        self.color = color

        if show:
            self.schedule_interval(self.hide_instructor, 1)

    def hide_instructor(self, delta_time):
        self.unschedule(self.hide_instructor)
        self.show_instructor(show=False)


class WorkoutLayer(cocos.layer.Layer):
    def __init__(self, level):
        super(WorkoutLayer, self).__init__()

        self.player_layers = [
            PlayerLayer(Player(pyglet.window.key.S), level, (0, 0)),
            PlayerLayer(Player(pyglet.window.key.L), level, (240, 0))
        ]

        map(self.add, self.player_layers)


class TextLayer(cocos.layer.ColorLayer):
    is_event_handler = True

    def __init__(self, text):
        super(TextLayer, self).__init__(255, 0, 0, 255)

        label = cocos.text.HTMLLabel(
            make_html(text, color="white"),
            width=480,
            anchor_x="center",
            anchor_y="center",
            multiline=True
        )

        label.position = (240, 160)
        self.add(label)

    def on_key_press(self, key, modifiers):
        next_scene()


class WarmUp(object):
    def instruct(self, rate, show_instructor):
        if rate < 120:
            show_instructor(text="FASTER", color=PlayerLayer.WARNING_COLOR)
        elif rate > 140:
            show_instructor(text="SLOW DOWN", color=PlayerLayer.WARNING_COLOR)
        else:
            show_instructor(text="PERFECT")


def next_scene():
    director.replace(director.scene.next_scene)


def make_scenes(layers):
    scenes = map(cocos.scene.Scene, layers)
    for scene, next_scene in pairwise(scenes):
        scene.next_scene = next_scene
    return scenes


if __name__ == "__main__":
    pyglet.font.add_file('8-bit wonder.ttf')
    director.init(width=480, height=320)

    scenes = make_scenes([
        TextLayer("WORKOUT"),
        TextLayer("HELLO<br/>MY NAME IS ARNOLD"),
        TextLayer("I AM YOUR INSTRUCTOR"),
        TextLayer("WARM UP<br/>120-140 BPM"),
        WorkoutLayer(WarmUp())
    ])

    director.run(scenes[0])
