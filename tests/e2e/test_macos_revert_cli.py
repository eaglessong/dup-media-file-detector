from tests.macos_fixtures import MacFixture
from tests.revert_fixtures import RevertCases, RevertSignalCases


class MacRevertCli(RevertSignalCases, RevertCases, MacFixture):
    cli_mode = True
