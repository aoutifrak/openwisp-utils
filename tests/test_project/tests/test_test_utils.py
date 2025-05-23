import sys
from unittest.mock import patch

from django.dispatch import Signal
from django.test import TestCase, override_settings
from openwisp_utils.tests import (
    AssertNumQueriesSubTestMixin,
    TimeLoggingTestRunner,
    capture_any_output,
    capture_stderr,
    capture_stdout,
    catch_signal,
)
from openwisp_utils.utils import deep_merge_dicts, print_color, retryable_request
from requests.exceptions import ConnectionError, RetryError
from urllib3.response import HTTPResponse

from ..models import Shelf

status_signal = Signal()  # providing_args=['status']


class TestUtils(TestCase):
    def _generate_signal(self):
        status_signal.send(sender=self, status="working")

    def test_status_signal_emitted(self):
        """Tests the catch_signal test utility function"""
        with catch_signal(status_signal) as handler:
            self._generate_signal()
        handler.assert_called_once_with(
            status="working", sender=self, signal=status_signal
        )

    def test_deep_merge_dicts(self):
        dict1 = {
            "key1": "value1",
            "key2": {"key2-1": "value2-1", "unchanged": "unchanged"},
            "unchanged": "unchanged",
        }
        dict2 = {
            "key1": "value1-final",
            "key2": {"key2-1": "value2-1-final", "key2-2": "value2-2"},
        }
        merged = {
            "key1": "value1-final",
            "key2": {
                "key2-1": "value2-1-final",
                "key2-2": "value2-2",
                "unchanged": "unchanged",
            },
            "unchanged": "unchanged",
        }
        self.assertDictEqual(deep_merge_dicts(dict1, dict2), merged)

    @override_settings(OPENWISP_SLOW_TEST_THRESHOLD=[0.0, 0.0])
    @capture_any_output()
    def test_time_logging_runner(self, stdout, stderr):
        runner = TimeLoggingTestRunner()
        suite = runner.build_suite(
            ["test_project.tests.test_test_utils.TestUtils.test_status_signal_emitted"]
        )
        runner.run_suite(suite)
        self.assertIn("slow tests (>0.0s)", stdout.getvalue())
        self.assertIn("Total slow tests detected: 1", stdout.getvalue())
        self.assertIn("Ran 1 test", stderr.getvalue())
        self.assertIn("OK", stderr.getvalue())

    @capture_stdout()
    def test_print_color(self, captured_output):
        print_color("This is the printed in Red Bold", color_name="red_bold")
        expected = "\033[31;1mThis is the printed in Red Bold\033[0m\n"
        self.assertEqual(captured_output.getvalue(), expected)
        # cleaning captured_ouput for next assertion
        captured_output.truncate(0)
        captured_output.seek(0)
        print_color("This is the printed in Red Bold", color_name="red_bold", end="")
        expected = "\033[31;1mThis is the printed in Red Bold\033[0m"
        self.assertEqual(captured_output.getvalue(), expected)
        captured_output.truncate(0)
        captured_output.seek(0)
        print_color("This is the printed in Red Bold", color_name="invalid")
        expected = "\033[0mThis is the printed in Red Bold\033[0m\n"
        self.assertEqual(captured_output.getvalue(), expected)
        captured_output.truncate(0)

    @capture_stderr()
    def test_capture_stderr(self, captured_error):
        print("Testing capture_stderr", file=sys.stderr, end="")
        self.assertEqual(captured_error.getvalue(), "Testing capture_stderr")

    @patch("urllib3.util.retry.Retry.sleep")
    def test_retryable_request(self, *args):
        with self.subTest("Test failure to connect to server"):
            with patch(
                "urllib3.connectionpool.HTTPConnectionPool._get_conn",
                side_effect=OSError,
            ) as mocked__get_conn:
                with self.assertRaises(ConnectionError) as error:
                    retryable_request("get", url="https://openwisp.org")
                self.assertEqual(len(mocked__get_conn.mock_calls), 4)
                self.assertIn(
                    "OSError",
                    str(error.exception),
                )

        with self.subTest("Test retry on server error"):
            # Simulates the test never recovered
            with patch(
                "urllib3.connectionpool.HTTPConnection.getresponse",
                return_value=HTTPResponse(status=500, version="1.1"),
            ) as mocked_getResponse:
                with self.assertRaises(RetryError) as error:
                    retryable_request("get", url="https://openwisp.org")
                self.assertEqual(len(mocked_getResponse.mock_calls), 4)
                self.assertIn(
                    "too many 500 error responses",
                    str(error.exception),
                )

        with self.subTest("Test customization with retry_kwargs"):
            with patch(
                "openwisp_utils.utils.Retry",
            ) as mocked_retry, patch("openwisp_utils.utils.requests.Session"):
                retryable_request(
                    method="get",
                    url="https://openwisp.org",
                    max_retries=10,
                    backoff_factor=2,
                    backoff_jitter=0.2,
                    status_forcelist=(429, 500),
                    allowed_methods=("HEAD",),
                    retry_kwargs={"raise_on_redirect": False},
                )
                self.assertDictEqual(
                    mocked_retry.call_args.kwargs,
                    {
                        "total": 10,
                        "backoff_factor": 2,
                        "status_forcelist": (429, 500),
                        "allowed_methods": ("HEAD",),
                        "backoff_jitter": 0.2,
                        "raise_on_redirect": False,
                    },
                )
                self.assertEqual(mocked_retry.call_args[1]["total"], 10)


class TestAssertNumQueriesSubTest(AssertNumQueriesSubTestMixin, TestCase):
    def test_assert_num_queries(self):
        with patch.object(self, "subTest", wraps=self.subTest) as patched_subtest:
            with self.assertNumQueries(1):
                Shelf.objects.count()
            patched_subtest.assert_called_once()
