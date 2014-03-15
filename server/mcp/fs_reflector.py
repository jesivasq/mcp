__author__ = 'terrence'

import logging
from mcp.abode import Abode, Area
from mcp.filesystem import FileSystem, Directory, File
from mcp.actuators.hue import HueLight

log = logging.getLogger('fs-reflector')


def map_abode_to_filesystem(abode: Abode, fs: FileSystem) -> [Directory]:
    """
    Create a directory hierarchy that mirrors the abode layout.
    """
    directories = {}

    def add_subareas(area: Area, area_dir: Directory):
        "Add sub-areas from the given area to the given directory."
        nonlocal directories
        directories[area] = area_dir
        for name in area.subarea_names():
            subarea_dir = area_dir.add_entry(name, Directory())
            subarea = area.subarea(name)
            add_subareas(subarea, subarea_dir)

    abode_dir = fs.root().add_entry('abode', Directory())
    add_subareas(abode, abode_dir)
    return directories


def add_properties(directory: Directory, area: Area, properties: [str]):
    for prop in properties:
        def read_prop(bound_prop=prop) -> str:
            try:
                return str(area.get(bound_prop)) + "\n"
            except KeyError:
                log.error("key not found looking up property {} on area {}".format(bound_prop, area.name))
                return ""

        def write_prop(data: str, bound_prop=prop):
            area.set(bound_prop, data.strip())

        directory.add_entry(prop, File(read_prop, write_prop))


def add_hue_light(parent: Directory, hue: HueLight):
    subdir = parent.add_entry(hue.name, Directory())

    def read_on() -> str:
        return str(hue.on) + "\n"

    def write_on(data: str):
        hue.on = data.strip() == "True"

    subdir.add_entry("on", File(read_on, write_on))
    """
    subdir.add_entry("hsv")
    subdir.add_entry("rgb")
    subdir.add_entry("colortemp")
    """


def map_devices_to_filesystem(devices: [], fs: FileSystem):
    act_dir = fs.root().add_entry("actuators", Directory())
    for device in devices:
        if isinstance(device, HueLight):
            add_hue_light(act_dir, device)