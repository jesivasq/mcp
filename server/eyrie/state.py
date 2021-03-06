# This Source Code Form is subject to the terms of the GNU General Public
# License, version 3. If a copy of the GPL was not distributed with this file,
# You can obtain one at https://www.gnu.org/licenses/gpl.txt.
from mcp.filesystem import File, FileSystem
from mcp.state import StickyNestedStateMachine


class EyrieStateMachine(StickyNestedStateMachine):
    States = {
        'auto': {
            'wakeup',
            'daytime',
            'bedtime',
            'sleep'
        },
        'manual': {
            'on',
            'low',
            'off',
            'sleep',
            'read',
            'unset',
        }
    }
    StickyState = 'manual'


def bind_state_to_filesystem(state: EyrieStateMachine, filesystem: FileSystem):
    """
    We adjust the state as a user by poking /things/eyrie/user_control, but that can
    trigger subsequent state changes which are not reflected in the user's control.
    This exposes /things/state so the user can find the current state, not the last
    set control preference.
    """
    def read_state() -> str:
        lines = [state.current, "Options:"] + sorted(['\t' + str(s) for s in state.all_states()])
        return '\n'.join(lines) + '\n'

    filesystem.root().add_file('state', File(read_state, None))
