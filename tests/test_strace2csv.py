#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2021 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)
#
# SPDX-License-Identifier: MIT

# pylint: disable=invalid-name

""" Tests for strace2csv.py """

import subprocess
import os
import shutil
from pathlib import Path
import pytest
import pandas as pd


MYDIR = Path(os.path.dirname(os.path.realpath(__file__)))
TEST_WORK_DIR = MYDIR / "strace2csv_test_data"
TEST_DATA_DIR = MYDIR / "data"
TEST_DATA_FIREFOX_STARTUP = TEST_DATA_DIR / "strace_firefox_startup.log"
TEST_DATA_MISSING_OPTIONS = TEST_DATA_DIR / "strace_missing_options.log"

STRACE2CSV = MYDIR / ".." / "stracepy" / "strace2csv.py"


################################################################################


def df_to_string(df):
    """Return dataframe df as string"""
    return (
        "\n"
        + df.to_string(max_rows=None, max_cols=None, index=False, justify="left")
        + "\n"
    )


def df_difference(df_left, df_right):
    """Compare dataframes df_left and df_right and return diff"""
    df = df_left.merge(df_right, how="outer", indicator=True)
    # Keep only the rows that differ (that are not in both)
    df = df[df["_merge"] != "both"]
    # Rename 'left_only' and 'right_only' values in '_merge' column
    df["_merge"] = df["_merge"].replace(["left_only"], "EXPECTED ==>  ")
    df["_merge"] = df["_merge"].replace(["right_only"], "RESULT ==>  ")
    # Re-order columns: last column ('_merge') becomes first
    cols = df.columns.tolist()
    cols = cols[-1:] + cols[:-1]
    df = df[cols]
    # Rename '_merge' column to empty string
    df = df.rename(columns={"_merge": ""})
    return df


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
    cmd = [STRACE2CSV, "-h"]
    assert subprocess.run(cmd, check=True).returncode == 0


def test_basic():
    """
    Test that strace2csv.py runs and generates expected output
    """
    outfile = TEST_WORK_DIR / "strace_firefox_startup.csv"
    reference = TEST_DATA_DIR / "strace_firefox_startup.csv"
    df_reference = pd.read_csv(reference)

    cmd = [STRACE2CSV, "--out", outfile, "--verbose=3", TEST_DATA_FIREFOX_STARTUP]
    assert subprocess.run(cmd, check=True).returncode == 0
    assert Path(outfile).exists()
    df_outfile = pd.read_csv(outfile)
    df_diff = df_difference(df_reference, df_outfile)
    assert df_diff.empty, df_to_string(df_diff)


def test_stracelog_missing_options():
    """
    Test that strace2csv.py handles strace log generated with invalid options
    """
    outfile = TEST_WORK_DIR / "strace_firefox_startup.csv"

    cmd = [STRACE2CSV, "--out", outfile, TEST_DATA_MISSING_OPTIONS]
    assert subprocess.run(cmd, check=False).returncode == 1


################################################################################


if __name__ == "__main__":
    pytest.main([__file__])


################################################################################
