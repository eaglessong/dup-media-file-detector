from tests.move_fixtures import MoveFixture
from tests.revert_fixtures import RevertCases, RevertFaultCases


class LinuxRevert(RevertFaultCases, RevertCases, MoveFixture):
    pass
