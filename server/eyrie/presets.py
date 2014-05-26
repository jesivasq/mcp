# This Source Code Form is subject to the terms of the GNU General Public
# License, version 3. If a copy of the GPL was not distributed with this file,
# You can obtain one at https://www.gnu.org/licenses/gpl.txt.
from eyrie.state import EyrieStateMachine

from mcp.color import BHS
from mcp.devices import DeviceSet
from mcp.state import StateEvent

DaylightHue = 34495
DaylightSat = 232
MoonlightHue = 47000
MoonlightSat = 255


def daylight(brightness: float) -> BHS:
    """Return a BHS for pleasant light at the given relative brightness."""
    assert brightness >= 0
    assert brightness <= 1
    return BHS(255 * brightness, DaylightHue, DaylightSat)


with_ambient = """
def daylight_with_ambient(cls):
    Return a BHS for pleasant light, dimming the light when it is light outside, unless it is overcast.
"""


def moonlight(brightness: float) -> BHS:
    """Return a BHS for pleasant light to sleep by."""
    return BHS(255 * brightness, MoonlightHue, MoonlightSat)


def bind_preset_states_to_real_world(state: EyrieStateMachine, actuators: DeviceSet):
    def listen_manual_on(_: StateEvent):
        actuators.set('on', True).set('bhs', daylight(1))

    def listen_manual_low(_: StateEvent):
        actuators.set('on', True).set('bhs', daylight(0))

    def listen_manual_off(_: StateEvent):
        actuators.set('on', False)

    def listen_manual_sleep(_: StateEvent):
        bed = actuators.select('#bed')
        bed              .set('on', False).set('bhs', moonlight(0))
        (actuators - bed).set('on', True).set('bhs', moonlight(0))

    def listen_manual_read(_: StateEvent):
        bed = actuators.select('#bed')
        bed              .set('on', True).set('bhs', daylight(1))
        (actuators - bed).set('on', True).set('bhs', daylight(0))

    state.listen_enter_state('manual:on', listen_manual_on)
    state.listen_enter_state('manual:low', listen_manual_low)
    state.listen_enter_state('manual:off', listen_manual_off)
    state.listen_enter_state('manual:sleep', listen_manual_sleep)
    state.listen_enter_state('manual:read', listen_manual_read)

