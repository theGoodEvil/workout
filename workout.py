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

    def __init__(self, player, position):
        super(PlayerLayer, self).__init__(255, 0, 0, 255, width=240, height=320)
        self.player = player
        self.position = position

        self.label = cocos.text.Label(
            '0.0',
            font_name='Times New Roman',
            font_size=32,
            anchor_x='center',
            anchor_y='center')
        self.label.position = (120, 40)
        self.add(self.label)

        self.schedule_interval(self.update, 0.2)

    def update(self, delta_time):
        rate = "%3.1f" % (self.player.pulse.rate())
        self.label.element.text = rate

    def on_key_press(self, key, modifiers):
        if key == self.player.key:
            self.player.trigger()


class WorkoutLayer(cocos.layer.Layer):
    is_event_handler = True

    def __init__(self):
        super(WorkoutLayer, self).__init__()

        self.player_layers = [
            PlayerLayer(Player(pyglet.window.key.S), (0, 0)),
            PlayerLayer(Player(pyglet.window.key.L), (240, 0))
        ]

        map(self.add, self.player_layers)


if __name__ == "__main__":
    cocos.director.director.init(width=480, height=320)
    layer = WorkoutLayer()
    scene = cocos.scene.Scene(layer)
    cocos.director.director.run(scene)
