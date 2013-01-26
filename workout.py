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


class InstructorLayer(cocos.layer.ColorLayer):
    def __init__(self, position):
        super(InstructorLayer, self).__init__(255, 0, 0, 255, width=240, height=320)
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

    def set_text(self, text):
        self.label.element.text = text


class HeartbeatLayer(cocos.layer.ColorLayer):
    is_event_handler = True

    HEART_SIZE_SMALL = 0.2
    HEART_SIZE_BIG = 0.25
    HEART_BEAT = pyglet.media.load("heartbeat.wav", streaming=False)

    def __init__(self, player, position):
        super(HeartbeatLayer, self).__init__(22, 232, 247, 255, width=240, height=320)
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


class PlayerLayer(cocos.layer.Layer):
    def __init__(self, player, position):
        super(PlayerLayer, self).__init__()
        self.player = player

        self.instuctor_layer = InstructorLayer(position)
        self.instuctor_layer.visible = False
        self.add(self.instuctor_layer)

        self.heartbeat_layer = HeartbeatLayer(player, position)
        self.add(self.heartbeat_layer)

        self.schedule_interval(self.instruct, 4)

    def instruct(self, delta_time):
        rate = self.player.pulse.rate()
        if rate < 120:
            self.show_instructor(text="FASTER")
        elif rate > 140:
            self.show_instructor(text="SLOW DOWN")
        else:
            self.show_instructor(text="PERFECT")

    def show_instructor(self, delta_time=0, text=None, show=True):
        self.unschedule(self.show_instructor)

        if text:
            self.instuctor_layer.set_text(text)

        self.instuctor_layer.visible = show
        self.heartbeat_layer.visible = not show

        self.schedule_interval(self.show_instructor, 1, show=False)


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

    def __init__(self, text):
        super(TextLayer, self).__init__(255, 0, 0, 255)

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

    def on_key_press(self, key, modifiers):
        next_scene()


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
        WorkoutLayer()
    ])

    director.run(scenes[0])
