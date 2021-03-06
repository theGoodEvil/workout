#!/usr/bin/env python

import collections
import itertools
import operator
import time

from cocos.actions import MoveBy
from cocos.director import director
from cocos.layer import Layer, ColorLayer
from cocos.scene import Scene
from cocos.scenes.transitions import SlideInRTransition
from cocos.sprite import Sprite
from cocos.text import HTMLLabel

import pyglet


NUM_PLAYERS = 2

PLAYER_KEYS = [
    # For single-button mode, use the same key for left and right,
    # e.g. (pyglet.window.key.LEFT, pyglet.window.key.LEFT)
    (pyglet.window.key.LEFT, pyglet.window.key.RIGHT),
    (pyglet.window.key.UP, pyglet.window.key.DOWN)
]

INSTRUCTOR_INTERVAL = 4

WIDTH = 1920
HEIGHT = 1200

sceneManager = None


def pairwise(iterable):
    a, b = itertools.tee(iterable)
    next(b, None)
    return itertools.izip(a, b)


def make_html(text, color="black"):
    return '<center><font size="7" face="8BIT WONDER" color="%s">%s</font></center>' % (color, text)


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
    def __init__(self, keys):
        self.keys = keys
        self.first_key = True
        self.next_key_id = 0
        self.pulse = Pulse()

    def handle_key_press(self, key):
        if self.first_key and key in self.keys:
            self.first_key = False
            self.next_key_id = self.keys.index(key)

        if key == self.keys[self.next_key_id]:
            self.pulse.tick()
            self.next_key_id = 1 - self.next_key_id
            return True

        return False

    def handle_key_release(self, key):
        if key in self.keys:
            return True

        return False


class MessageLayer(Layer):
    def __init__(self):
        super(MessageLayer, self).__init__()

        self.label = HTMLLabel(
            make_html(""),
            width=WIDTH / NUM_PLAYERS,
            anchor_x="center",
            anchor_y="center",
            multiline=True
        )

        self.label.position = (WIDTH / (2 * NUM_PLAYERS), HEIGHT * 7 / 8)
        self.add(self.label)

    def set_text(self, text):
        self.label.element.text = make_html(text)


class HeartbeatLayer(Layer):
    is_event_handler = True

    HEART_SIZE_SMALL = WIDTH / 2400.0
    HEART_SIZE_BIG = 1.25 * HEART_SIZE_SMALL
    HEART_BEAT = pyglet.media.load("sound/heartbeat.wav", streaming=False)

    def __init__(self, player):
        super(HeartbeatLayer, self).__init__()
        self.player = player
        self.key_is_pressed = False

        self.heart = Sprite("heart.png")
        self.heart.position = (WIDTH / (2 * NUM_PLAYERS), HEIGHT / 2)
        self.heart.scale = self.HEART_SIZE_SMALL
        self.add(self.heart)

    def on_key_press(self, key, modifiers):
        if self.player.handle_key_press(key):
            self.HEART_BEAT.play()
            self.heart.scale = self.HEART_SIZE_BIG

    def on_key_release(self, key, modifiers):
        if self.player.handle_key_release(key):
            self.heart.scale = self.HEART_SIZE_SMALL


class RateLayer(MessageLayer):
    def __init__(self, player):
        super(RateLayer, self).__init__()

        @player.pulse.event
        def on_rate_changed(rate):
            self.set_text("%3.0f" % rate)


class PlayerLayer(ColorLayer):
    WORKOUT_COLOR = (22, 232, 247)
    WARNING_COLOR = (255, 0, 0)

    def __init__(self, player, level, position):
        super(PlayerLayer, self).__init__(0, 0, 0, 255, width=WIDTH / NUM_PLAYERS, height=HEIGHT)
        self.color = self.WORKOUT_COLOR
        self.player = player
        self.level = level
        self.position = position

        self.instructor_layer = MessageLayer()
        self.instructor_layer.visible = False
        self.add(self.instructor_layer)

        self.rate_layer = RateLayer(player)
        self.add(self.rate_layer)

        self.heartbeat_layer = HeartbeatLayer(player)
        self.add(self.heartbeat_layer)

    def instruct(self):
        rate = self.player.pulse.rate
        self.level.instruct(rate, self.show_instructor)

    def show_instructor(self, text="", show=True, color=WORKOUT_COLOR):
        self.instructor_layer.set_text(text)
        self.instructor_layer.visible = show
        self.rate_layer.visible = not show
        self.color = color

        if show:
            pyglet.clock.schedule_once(self.hide_instructor, 1)

    def hide_instructor(self, delta_time):
        self.show_instructor(show=False)

    def show_score(self):
        self.show_instructor(show=False)
        self.remove(self.rate_layer)
        self.remove(self.heartbeat_layer)
        self.remove(self.instructor_layer)
        score_layer = MessageLayer()
        score_layer.set_text(self.level.get_score())
        self.add(score_layer)


class ProgressBar(ColorLayer):
    def __init__(self, duration):
        super(ProgressBar, self).__init__(64, 64, 64, 255, width=WIDTH, height=HEIGHT / 20)

        self.bar = ColorLayer(128, 128, 128, 255, width=WIDTH, height=HEIGHT / 20)
        self.bar.do(MoveBy((WIDTH, 0), duration))
        self.add(self.bar)


class WorkoutLayer(Layer):
    is_event_handler = True

    def __init__(self, level_class, level_args, sound):
        super(WorkoutLayer, self).__init__()
        self.level_class = level_class
        self.is_complete = False

        def make_player_layer(i):
            return PlayerLayer(
                Player(PLAYER_KEYS[i]),
                level_class(*level_args),
                (i * WIDTH / NUM_PLAYERS, 0)
            )

        self.player_layers = map(make_player_layer, range(NUM_PLAYERS))

        map(self.add, self.player_layers)
        self.add(ProgressBar(level_class.time))

        self.schedule_interval(self.instruct, INSTRUCTOR_INTERVAL)
        self.schedule_interval(self.complete, level_class.time)

        self.audio_player = pyglet.media.Player()
        self.audio_player.eos_action = pyglet.media.Player.EOS_LOOP
        self.audio_player.queue(pyglet.media.load(sound, streaming=False))

    def instruct(self, delta_time):
        map(operator.methodcaller("instruct"), self.player_layers)

    def complete(self, delta_time):
        self.is_complete = True

        self.audio_player.pause()
        self.audio_player.next()

        self.unschedule(self.instruct)
        self.unschedule(self.complete)

        map(operator.methodcaller("show_score"), self.player_layers)

    def on_enter(self):
        super(WorkoutLayer, self).on_enter()
        self.audio_player.play()

    def on_key_press(self, key, modifiers):
        if self.is_complete and key == pyglet.window.key.SPACE:
            sceneManager.next_scene()


class TextLayer(ColorLayer):
    is_event_handler = True

    def __init__(self, text):
        super(TextLayer, self).__init__(255, 0, 0, 255)

        label = HTMLLabel(
            make_html(text, color="white"),
            width=WIDTH,
            anchor_x="center",
            anchor_y="center",
            multiline=True
        )

        label.position = (WIDTH / 2, HEIGHT / 2)
        self.add(label)

    def on_key_press(self, key, modifiers):
        if key == pyglet.window.key.SPACE:
            sceneManager.next_scene()


class Level(object):
    time = 30

    scores = [
        "LOSER",
        "OK",
        "GREAT",
        "AWESOME"
    ]

    def __init__(self, min_rate, max_rate):
        self.min_rate = min_rate
        self.max_rate = max_rate
        self.score = 0

        self.slow_warnings = collections.deque([
            "FASTER",
            "ARE YOU KIDDING ME",
            "MORE ENERGY"
        ])

        self.fast_warnings = collections.deque([
            "SLOW DOWN",
            "EASY"
        ])

    def get_score(self):
        max_score = self.time / INSTRUCTOR_INTERVAL
        score_index = (len(self.scores) - 1) * self.score / max_score
        return self.scores[score_index]

    def instruct(self, rate, show_instructor):
        if rate < self.min_rate:
            show_instructor(
                text=self.slow_warnings[0],
                color=PlayerLayer.WARNING_COLOR
            )
            self.slow_warnings.rotate(-1)
        elif rate > self.max_rate:
            show_instructor(
                text=self.fast_warnings[0],
                color=PlayerLayer.WARNING_COLOR
            )
            self.fast_warnings.rotate(-1)
        else:
            self.score += 1
            show_instructor(text="PERFECT")


class SceneManager(object):
    def __init__(self, scene_defs):
        self.scene_defs = scene_defs
        self.current_scene_id = 0

    def current_scene(self):
        scene_def = self.scene_defs[self.current_scene_id]

        layer_class = scene_def[0]
        args = scene_def[1:]

        layer = layer_class(*args)
        return Scene(layer)

    def next_scene(self):
        self.current_scene_id = (self.current_scene_id + 1) % len(self.scene_defs)
        director.replace(SlideInRTransition(self.current_scene(), duration=0.1))


if __name__ == "__main__":
    pyglet.font.add_file("font/8-bit wonder.ttf")
    director.init(width=WIDTH, height=HEIGHT, fullscreen=False)

    scene_defs = [
        [TextLayer, "WORKOUT"],
        [TextLayer, "HELLO<br/>MY NAME IS ARNOLD"],
        [TextLayer, "I AM YOUR INSTRUCTOR"],
        [TextLayer, "WARM UP<br/>80-100 BPM"],
        [WorkoutLayer, Level, [80, 100], "sound/loop90.wav"],
        [TextLayer, "ALL RIGHT<br/>NOW LETS GET SERIOUS"],
        [TextLayer, "LEVEL 1<br/>120-140 BPM"],
        [WorkoutLayer, Level, [120, 140], "sound/loop130.wav"],
        [TextLayer, "COME ON<br/>MORE ENERGY"],
        [TextLayer, "LEVEL 2<br/>OVER 200 BPM"],
        [WorkoutLayer, Level, [200, 1000], "sound/loop220.wav"],
        [TextLayer, "NOW TAKE A SHOWER"]
    ]

    sceneManager = SceneManager(scene_defs)

    # workaround for pyglet refresh issue
    pyglet.clock.schedule_interval(lambda dt: None, 1 / 60.0)

    director.run(sceneManager.current_scene())
