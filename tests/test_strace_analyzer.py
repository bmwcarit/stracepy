#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2021 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)
#
# SPDX-License-Identifier: MIT

# pylint: disable=invalid-name

""" Tests for strace_analyzer.py """

import subprocess
import os
import shutil
from pathlib import Path
import pytest


MYDIR = Path(os.path.dirname(os.path.realpath(__file__)))
TEST_WORK_DIR = MYDIR / "strace_analyzer_test_data"
TEST_DATA_DIR = MYDIR / "data"
TEST_DATA_FIREFOX_STARTUP = TEST_DATA_DIR / "strace_firefox_startup.csv"

STRACE_ANALYZER = MYDIR / ".." / "stracepy" / "strace_analyzer.py"


################################################################################


@pytest.fixture(autouse=True)
def set_up_test_data():
    """Fixture to set up the test data"""
    print("setup")
    shutil.rmtree(TEST_WORK_DIR, ignore_errors=True)
    TEST_WORK_DIR.mkdir(parents=True, exist_ok=True)
    yield "resource"
    print("clean up")
    shutil.rmtree(TEST_WORK_DIR)


def test_help():
    """
    Test 'help' command line argument
    """
    cmd = [STRACE_ANALYZER, "-h"]
    assert subprocess.run(cmd, check=True).returncode == 0


def test_summary():
    """
    Test summary command
    """
    cmd = [STRACE_ANALYZER, TEST_DATA_FIREFOX_STARTUP, "summary"]
    assert subprocess.run(cmd, check=True).returncode == 0


################################################################################


if __name__ == "__main__":
    pytest.main([__file__])


################################################################################
