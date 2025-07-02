import signal
import unittest
from unittest.mock import patch, Mock

from backports.asyncio.runner._int_to_enum import (
    _patched_int_to_enum,
    _orig_int_to_enum,
)


# Ref: https://github.com/python/cpython/blob/3.8/Lib/test/test_signal.py
# We add a dedicated int_to_enum test as one doesn't exist.


class GenericTests(unittest.TestCase):
    def test_patched_int_to_enum(self) -> None:
        enum_klass = Mock(wraps=signal.Handlers)

        # Case 1 - Base Case
        sig_ign_enum = signal.SIG_IGN
        result = _orig_int_to_enum(sig_ign_enum, signal.Handlers)
        self.assertEqual(result, sig_ign_enum)

        # Case 2 - Base Case
        sig_dfl_int = signal._enum_to_int(signal.SIG_DFL)
        result = _orig_int_to_enum(sig_dfl_int, signal.Handlers)
        self.assertEqual(result, signal.SIG_DFL)

        # Case 3 - Base Case
        enum_klass.reset_mock()
        result = _orig_int_to_enum(42, enum_klass)
        self.assertEqual(result, 42)
        enum_klass.assert_called_with(42)

        # Case 4 - Base Case
        enum_klass.reset_mock()
        result = _orig_int_to_enum("bar", enum_klass)
        self.assertEqual(result, "bar")
        enum_klass.assert_called_with("bar")

        # Case 5 - The "Fix"
        enum_klass.reset_mock()
        with patch.object(signal, signal._int_to_enum.__name__, _patched_int_to_enum):
            result = signal._int_to_enum("bar", enum_klass)
            self.assertEqual(result, "bar")
            enum_klass.assert_not_called()

            result = signal._int_to_enum(42, enum_klass)
            self.assertEqual(result, 42)
            enum_klass.assert_called_with(42)


if __name__ == "__main__":
    unittest.main()
