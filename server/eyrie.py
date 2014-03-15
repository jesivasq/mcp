#!/usr/bin/env python3
__author__ = 'terrence'

import mcp
import mcp.network as network
from mcp.abode import Abode
from mcp.actuators.hue import HueBridge, HueLight
from mcp.filesystem import FileSystem, Directory, File
from mcp.sensors.nerve import Nerve, NerveEvent
from mcp.dimension import Coord, Size
import mcp.fs_reflector as reflector

import sys
import time


"""
Horizontal: 4/ft
Vert: 2/ft
Reference is upper-left corner.
X is left-to-right.
Y is top-to-bottom.
Z is floor-to-ceiling.

----------------------------------------------------------------------------------------------------+
|                                        |        .            *                                   |
|                                        |        .                                                |
|                                        |        .                                                |
|                                        |        .                                                |
|                                        |        .                                                |
|                                        |        .                                                |
|                                        |        .                                                |
|                                        |        .                                                |
|         Office                         |        .                 Bedroom                        |
|            10ftx13ft                   |________.                    12ftx10ft                   |
|                                        .        |                                                |
|                                        .        |                                                |
|                                        .        |                                                |
|                                        .        |                                                |
|                                        .        |                                                |
|                                        .        |                                                |
|                                        .        |                                                |
|                                        .        |                                                |
|                                        +________+@@@@@@@@@@--------------------------------------+
|                                        @                         @
|                                        @        Hall             @
|                                        @          76" x 31"      @
|                                        @                         @
|@@@@@@-------------------------------------------+          +-----+
@                                                 @          @     |
@                                                 @          @     |
@  Entry                                          @          @     |
@    42" x 42"                                    @          @     |
@                                                 @          @     |
+--------------                                   +          +-----+
|
|
|
|
|
|
|     Living Room
|        13' x 19'9"
|
|
|
|
|
|
|
|
|
|
|
|
|
|
|
|
|
|
|
|
|
|
|
|
+
"""


def build_abode(filesystem: FileSystem):
    abode = Abode("eyrie")
    office = abode.create_room('office', Coord(0, 0), Size('10ft', '13ft', '8ft'))
    bedroom = abode.create_room('bedroom', Coord('13ft', 0), Size('12ft', '10ft', '8ft'))
    livingroom = abode.create_room('livingroom', Coord(0, '13ft'), Size('13ft', '19ft9in', '8ft'))
    entry = livingroom.create_subarea('entry', Coord(0, 0), Size('42in', '42in', '8ft'))

    directories = reflector.map_abode_to_filesystem(abode, filesystem)
    for area in (office, bedroom, livingroom):
        reflector.add_properties(directories[area], area, ('temperature', 'humidity', 'motion'))

    return abode


def add_devices(abode: Abode, bus: network.Bus, filesystem: FileSystem):
    nerves = []
    for name in ['rpi-nerve-bedroom', 'rpi-nerve-office', 'rpi-nerve-livingroom']:
        path = name.replace('rpi-nerve-', '/eyrie/')
        log.info("Building nerve: {} at {}".format(name, path))
        nerve = Nerve(name, (name, network.Bus.DefaultSensorPort))

        def property_forwarder(path: str, propname: str):
            def handler(evt: NerveEvent):
                log.info("Forwarding message to: {}[{}]".format(path, propname))
                abode.lookup(path).set(propname, evt.value)
            return handler

        nerve.listen_temperature(property_forwarder(path, 'temperature'))
        nerve.listen_humidity(property_forwarder(path, 'humidity'))
        nerve.listen_motion(property_forwarder(path, 'motion'))
        bus.add_sensor(nerve)
        nerves.append(nerve)
    bedroom_nerve, office_nerve, livingroom_nerve = nerves


    bedroom_huebridge = HueBridge('hue-bedroom', 'MasterControlProgram')
    bed_hue = HueLight('hue-bedroom-bed', bedroom_huebridge, 1)
    desk_hue = HueLight('hue-bedroom-desk', bedroom_huebridge, 2)
    dresser_hue = HueLight('hue-bedroom-dresser', bedroom_huebridge, 3)
    devices = [bedroom_nerve, office_nerve, livingroom_nerve, bed_hue, desk_hue, dresser_hue]

    reflector.map_devices_to_filesystem(devices, filesystem)
    return devices


def add_reactions(abode, devices, filesystem):
    #abode.lookup('/eyrie/bedroom').listen('temperature', 'propertyTouched', lambda event: print("BED:", event.property_value))
    #abode.lookup('/eyrie/livingroom').listen('temperature', 'propertyTouched', lambda event: print("LIV:", event.property_value))
    #DatabaseLocation = "/storage/raid/data/var/db/mcp/{}.rrd"
    #subprocess.check_output(["rrdtool", "update", self.database_filename, "--",
    #                         "N:{}:{}".format(self.last_temperature, self.last_humidity)])

    bedroom_lighting_preset = "unset"
    def read_lighting_preset() -> str:
        return "Current Value is: {} -- Possible Values are: on, off, sleep, reading".format(bedroom_lighting_preset)

    def write_lighting_preset(data: str):
        data = data.strip()
        states = {
            'off':
                   {'hue-bedroom-bed': {'on': False},
                    'hue-bedroom-desk': {'on': False},
                    'hue-bedroom-dresser': {'on': False}},
            'on':
                   {'hue-bedroom-bed': {'on': True, 'hsv': (255, 34495, 232)},
                    'hue-bedroom-desk': {'on': True, 'hsv': (255, 34495, 232)},
                    'hue-bedroom-dresser': {'on': True, 'hsv': (255, 34495, 232)}},
            'read':
                   {'hue-bedroom-bed': {'on': True, 'control': 'preset', 'hsv': (255, 34495, 232)},
                    'hue-bedroom-desk': {'on': True, 'hsv': (0, 34495, 232)},
                    'hue-bedroom-dresser': {'on': True, 'hsv': (0, 34495, 232)}},
            'sleep':
                   {'hue-bedroom-bed': {'on': False},
                    'hue-bedroom-desk': {'on': True, 'hsv': (0, 47000, 255)},
                    'hue-bedroom-dresser': {'on': True, 'hsv': (0, 47000, 255)}}
        }
        if data not in states:
            return
        state = states[data]
        for device_name, presets in state.items():
            matches = [d for d in devices if d.name == device_name]
            if not len(matches):
                return
            device = matches[0]
            for prop, value in presets.items():
                setattr(device, prop, value)

        nonlocal bedroom_lighting_preset
        bedroom_lighting_preset = data

    presets = filesystem.root().add_entry("presets", Directory())
    bedroom = presets.add_entry("bedroom", Directory())
    lighting = bedroom.add_entry("lighting", File(read_lighting_preset, write_lighting_preset))



def main():
    global log
    log = mcp.enable_logging(level='DEBUG')
    filesystem = FileSystem('/things')
    bus = network.Bus()
    abode = build_abode(filesystem)
    devices = add_devices(abode, bus, filesystem)
    add_reactions(abode, devices, filesystem)

    bus.start()

    filesystem.run()

    bus.exit()
    bus.join()
    return 0


if __name__ == '__main__':
    sys.exit(main())