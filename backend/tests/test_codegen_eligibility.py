"""Контрактные unit-тесты предикатов codegen (без БД)."""
import unittest
from unittest.mock import MagicMock

from api.services.codegen_eligibility import is_successful_terminal_run
from schemas import CaseFinalStatusEnum


class TestCodegenTerminalRun(unittest.TestCase):
    def test_passed(self):
        run = MagicMock()
        run.status = CaseFinalStatusEnum.PASSED.value
        self.assertTrue(is_successful_terminal_run(run))

    def test_failed(self):
        run = MagicMock()
        run.status = CaseFinalStatusEnum.FAILED.value
        self.assertFalse(is_successful_terminal_run(run))


if __name__ == "__main__":
    unittest.main()
