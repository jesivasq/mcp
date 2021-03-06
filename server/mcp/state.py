# This Source Code Form is subject to the terms of the GNU General Public
# License, version 3. If a copy of the GPL was not distributed with this file,
# You can obtain one at https://www.gnu.org/licenses/gpl.txt.
from mcp.typeclass import DerivingEq

from collections import defaultdict

import logging

log = logging.getLogger('state')


class NestedState(DerivingEq):
    """
    A state that nests two deep in the form state:sub.
    """
    def __init__(self, value: str):
        self.left, _, self.right = value.partition(":")
        assert ":" not in self.right

    def __str__(self):
        return "{0.left}:{0.right}".format(self)


class StateEvent:
    def __init__(self, prior: NestedState, new: NestedState):
        self.prior_state = prior
        self.new_state = new

    def __str__(self):
        return "StateEvent({} -> {})".format(self.prior_state, self.new_state)


class StickyNestedStateMachine:
    """
    Must be sub-classed to specify valid states. Example:

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
            'sleep'
        }
    }
    StickyState = 'manual'
    """
    States = {}
    StickyState = ""

    def __init__(self, initial: str):
        self.state_ = NestedState(initial)
        assert self.valid_state(self.state_)

        self.enter_callbacks_ = defaultdict(list)  # {str: [callable]}
        self.exit_callbacks_ = defaultdict(list)  # {str: [callable]}

    @property
    def current(self) -> str:
        return str(self.state_)

    @property
    def current_state(self) -> NestedState:
        return self.state_

    def all_states(self) -> {str}:
        return {"{}:{}".format(key, value) for key, values in self.States.items() for value in values}

    def valid_state(self, state: NestedState):
        return state.left in self.States and state.right in self.States[state.left]

    def allow_transition_(self, old_state: NestedState, new_state: NestedState) -> bool:
        return old_state.left != self.StickyState or new_state.left == self.StickyState

    @staticmethod
    def dispatch_(callbacks: [callable], event: StateEvent) -> bool:
        """
        Call all callbacks, return False if any callbacks returned False.
        All callbacks are called, regardless of the result of any specific callback.
        """
        results = [callback(event) for callback in callbacks]
        return not any((res is False for res in results))

    def dispatch_enter_(self, state: str, event: StateEvent) -> bool:
        if state in self.enter_callbacks_:
            return self.dispatch_(self.enter_callbacks_[state], event)
        return True

    def dispatch_exit_(self, state: str, event: StateEvent) -> bool:
        if state in self.exit_callbacks_:
            return self.dispatch_(self.exit_callbacks_[state], event)
        return True

    def switch_state_(self, new_state: NestedState) -> bool:
        log.info("switching state: {} -> {}".format(self.state_, new_state))
        event = StateEvent(self.state_, new_state)

        # Dispatch exit events. Abort state change if any returned false.
        if not self.dispatch_exit_(str(self.state_), event):
            log.info("ABORTED state change {} -> {} because of False exit callback.".format(self.state_, new_state))
            return False

        self.state_ = new_state

        return self.dispatch_enter_(str(self.state_), event)

    def listen_exit_state(self, state: str, callback: callable):
        """
        Receive a callback when leaving the given state.
        """
        log.debug("listen for exit-state: {}".format(state))
        assert self.valid_state(NestedState(state))
        self.exit_callbacks_[state].append(callback)

    def listen_enter_state(self, state: str, callback: callable):
        """
        Receive a callback when entering the given state.
        """
        log.debug("listen for enter-state: {}".format(state))
        assert self.valid_state(NestedState(state))
        self.enter_callbacks_[state].append(callback)

    def change_state(self, state: str) -> bool:
        """
        Switch to a new state, but fail if we try to leave the "sticky" state.
        """
        new_state = NestedState(state)
        if not self.allow_transition_(self.state_, new_state):
            log.info("change_state skipping change state {} -> {}: transition not allowed".format(self.state_, new_state))
            return False
        if self.state_ == new_state:
            log.info("Skipping change state {} -> {}: same state".format(self.state_, new_state))
            return False
        log.debug("change_state triggering _switch_state for {} -> {}".format(self.state_, new_state))
        return self.switch_state_(new_state)

    def change_user_state(self, new_state: str) -> bool:
        """
        Switch to a new state. Does not check if the transition is allowed.
        """
        log.debug("change_user_state triggering _switch_state for {} -> {}".format(self.state_, new_state))
        return self.switch_state_(NestedState(new_state))
