# This Source Code Form is subject to the terms of the GNU General Public
# License, version 3. If a copy of the GPL was not distributed with this file,
# You can obtain one at https://www.gnu.org/licenses/gpl.txt.
import logging

import llfuse

from mcp.abode import Abode, Area
from mcp.cronish import Cronish
from mcp.environment import Environment
from mcp.network import Bus as NetworkBus
from mcp.devices import DeviceSet
from mcp.sensors import SensorEvent
from mcp.sensors.listener import Listener, ListenerEvent
from mcp.sensors.nerve import Nerve
from mcp.sensors.wemo import  WeMoManager, WeMoSensor
from mcp.scheduler import Scheduler

log = logging.getLogger("sensors")


def _make_property_forwarder(room: Area, property_name: str):
    def handler(event: SensorEvent):
        log.debug("{}[{}] = {}".format(room.name, property_name, event.value))
        room.set(property_name, event.value)
    return handler


def build_sensors(abode: Abode, environment: Environment, network: NetworkBus, cronish: Cronish, scheduler: Scheduler) -> DeviceSet:
    sensors = DeviceSet()

    # Nerves.
    for unique in ('bedroom-north', 'office-north', 'livingroom-south'):
        name = 'nerve-{}'.format(unique)
        log.info("Building nerve: {}".format(name))
        nerve = sensors.add(Nerve(name, (name, NetworkBus.DefaultSensorPort)))
        path = '/eyrie/{}'.format(nerve.room_name)
        room = abode.lookup(path)

        # Put the properties on the abode with a default unset value so that we can know about them.
        room.set('temperature', 'unset')
        room.set('humidity', 'unset')
        room.set('nerve_motion', 'unset')

        # Forward updates to the sensor to the abode properties we just attached.
        nerve.listen_temperature(_make_property_forwarder(room, 'temperature'))
        nerve.listen_humidity(_make_property_forwarder(room, 'humidity'))
        nerve.listen_motion(_make_property_forwarder(room, 'nerve_motion'))

        # Put on the network.
        network.add_sensor(nerve.remote)

    # WeMo motion.
    wemo_manager = WeMoManager(network.internal_address, scheduler, network, llfuse.lock)
    wemo_motion_sensors = {
        'office': ['desk', 'west', 'east'],
        'kitchen': ['sink', 'west'],
        'utility': ['north'],
        'livingroom': ['north'],
        'bedroom': ['desk', 'south']
    }
    for room_name, sensor_names in wemo_motion_sensors.items():
        room = abode.lookup('/eyrie/{}'.format(room_name))
        for sensor_name in sensor_names:
            sensor_hostname = 'wemomotion-{}-{}'.format(room_name, sensor_name)
            wemo_motion = sensors.add(wemo_manager.add_device(WeMoSensor(sensor_hostname, wemo_manager)))

            motion_property_name = 'wemomotion_{}'.format(sensor_name)
            room.set(motion_property_name, False)  # FIXME: see if we can make this reflect the initial state somehow.
            wemo_motion.listen_motion(_make_property_forwarder(room, motion_property_name))

            defunct_property_name = 'wemomotion_{}_defunct'.format(sensor_name)
            room.set(defunct_property_name, False)
            wemo_motion.listen_defunct(_make_property_forwarder(room, defunct_property_name))

    """
    wemo_bridge = WeMoSensorBridge('127.0.0.1')

    wemo_motion_sensors = {
        'office': ['desk', 'west', 'east'],
        'kitchen': ['sink', 'west'],
        'utility': ['north'],
        'livingroom': ['north'],
        'bedroom': ['desk', 'south']
    }
    for room_name, sensor_names in wemo_motion_sensors.items():
        room = abode.lookup('/eyrie/{}'.format(room_name))
        for sensor_name in sensor_names:
            wemo_motion = wemo_bridge.add_device(WeMoMotion('wemomotion-{}-{}'.format(room_name, sensor_name),
                                                            wemo_bridge))
            property_name = 'wemo_motion_{}'.format(sensor_name)
            room.set(property_name, wemo_motion.get_state())
            wemo_motion.listen_motion(_make_property_forwarder(room, property_name))

    wemo_switch = wemo_bridge.add_device(WeMoSwitch('wemoswitch-office-fountain', wemo_bridge))
    room = abode.lookup('/eyrie/office')
    room.set('wemo_switch_fountain', wemo_switch.get_state())
    wemo_switch.listen_switch_state(_make_property_forwarder(room, 'wemo_switch_fountain'))

    network.add_sensor(wemo_bridge.remote)
    """

    # Listeners.
    abode.set('user_control', 'auto:daytime')
    for (room_name, machine) in [('bedroom', 'lemur')]:
        name = 'listener-{}-{}'.format(room_name, machine)
        log.info("Building listener: {}".format(name))
        listener = sensors.add(Listener(name, (machine, NetworkBus.DefaultSensorPort)))
        assert listener.room_name == room_name

        # Forward the commands to the control property.
        def property_forwarder(event: ListenerEvent):
            log.info("/eyrie[user_control] = {}".format(event.command))
            abode.set('user_control', event.command)
        listener.listen_for_commands(property_forwarder)

        # Put on the network.
        network.add_sensor(listener.remote)

    # Environment.
    def update_environment_on_abode():
        abode.set('sunrise_twilight', environment.sunrise_twilight)
        abode.set('sunrise', environment.sunrise)
        abode.set('sunset', environment.sunset)
        abode.set('sunset_twilight', environment.sunset_twilight)
    cronish.register_task('update_environment_on_abode', update_environment_on_abode)
    cronish.update_task_time('update_environment_on_abode',
                             days_of_week={0, 1, 2, 3, 4, 5, 6}, hours={0}, minutes=set())

    return sensors, [wemo_manager]
