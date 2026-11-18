from tests.move_fixtures import MoveFixture
from tests.revert_fixtures import RevertCases, RevertSignalCases


class LinuxRevertCli(RevertSignalCases, RevertCases, MoveFixture):
    cli_mode = True
