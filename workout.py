#!/usr/bin/env python

import collections
import itertools
import time

import cocos
import pyglet


def pairwise(iterable):
    a, b = itertools.tee(iterable)
    next(b, None)
    return itertools.izip(a, b)


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


class PlayerLayer(cocos.layer.ColorLayer):
    is_event_handler = True

    HEART_SIZE_SMALL = 0.2
    HEART_SIZE_BIG = 0.25
    HEART_BEAT = pyglet.media.load("heartbeat.wav", streaming=False)

    def __init__(self, player, position):
        super(PlayerLayer, self).__init__(22, 232, 247, 255, width=240, height=320)
        self.player = player
        self.position = position

        self.label = cocos.text.Label(
            '',
            font_name='8BIT WONDER',
            font_size=24,
            color=(0, 0, 0, 255),
            anchor_x='center',
            anchor_y='center'
        )

        self.label.position = (120, 280)
        self.add(self.label)

        self.heart = cocos.sprite.Sprite("heart.png")
        self.heart.position = (120, 140)
        self.heart.scale = self.HEART_SIZE_SMALL
        self.add(self.heart)

        self.schedule_interval(self.update, 0.2)

    def update(self, delta_time):
        rate = "%3.0f" % (self.player.pulse.rate())
        self.label.element.text = rate

    def on_key_press(self, key, modifiers):
        if key == self.player.key:
            self.HEART_BEAT.play()
            self.heart.scale = self.HEART_SIZE_BIG
            self.player.trigger()

    def on_key_release(self, key, modifiers):
        self.heart.scale = self.HEART_SIZE_SMALL


class WorkoutLayer(cocos.layer.Layer):
    def __init__(self):
        super(WorkoutLayer, self).__init__()

        self.player_layers = [
            PlayerLayer(Player(pyglet.window.key.S), (0, 0)),
            PlayerLayer(Player(pyglet.window.key.L), (240, 0))
        ]

        map(self.add, self.player_layers)


class TextLayer(cocos.layer.ColorLayer):
    is_event_handler = True

    def __init__(self, text, color=(255, 0, 0, 255)):
        super(TextLayer, self).__init__(*color)

        html = '<center><h1><font face="8BIT WONDER" color="white">%s</font></h1></center>' % text
        label = cocos.text.HTMLLabel(
            html,
            width=480,
            anchor_x='center',
            anchor_y='center',
            multiline=True
        )

        label.position = (240, 160)
        self.add(label)


def make_scene(layer):
    scene = cocos.scene.Scene(layer)
    return scene


def follow(scene, next_scene):
    layer = scene.get_children()[0]
    layer.on_key_press = lambda k, m: director.replace(next_scene)


if __name__ == "__main__":
    pyglet.font.add_file('8-bit wonder.ttf')
    director = cocos.director.director
    director.init(width=480, height=320)

    title = make_scene(TextLayer("WORKOUT"))
    instructions = make_scene(TextLayer("HELLO.<br/>My name is Arnold."))
    level_1 = make_scene(TextLayer("WARM UP.<br/>120-140 BPM"))
    workout = make_scene(WorkoutLayer())

    follow(title, instructions)
    follow(instructions, level_1)
    follow(level_1, workout)

    director.run(title)
