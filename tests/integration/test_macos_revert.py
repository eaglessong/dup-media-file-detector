from tests.macos_fixtures import MacFixture
from tests.revert_fixtures import RevertCases, RevertFaultCases


class MacRevert(RevertFaultCases, RevertCases, MacFixture):
    pass
