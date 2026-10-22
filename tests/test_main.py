import unittest
from contextlib import redirect_stdout
from io import StringIO

from app.main import main


class TestMain(unittest.TestCase):
    def test_main_prints_startup_message(self):
        output = StringIO()

        with redirect_stdout(output):
            main()

        self.assertEqual(
            output.getvalue().strip(),
            "ProofSprint AI is starting!",
        )


if __name__ == "__main__":
    unittest.main()
