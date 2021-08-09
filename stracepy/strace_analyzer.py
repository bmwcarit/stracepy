#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2021 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)
#
# SPDX-License-Identifier: MIT

# pylint: disable=invalid-name, too-few-public-methods

""" Analyze and query strace log given the strace log in CSV format """

import argparse
import logging
import os

from stracepy.utils import (
    df_regex_filter,
    wrap_text,
    current_func_name,
    print_df,
    exit_unless_accessible,
    setup_logging,
    df_from_csv_file,
    LOGGER_NAME,
)

###############################################################################

_LOGGER = logging.getLogger(LOGGER_NAME)

RE_DEVICE_FILE = "^/dev/|^/sys/devices/|^/sys/.*/gpio"

###############################################################################


def summary(df_strace):
    """
    Summarize strace log file
    """
    programs_executed(df_strace)
    count_errors(df_strace)


def programs_executed(df_strace):
    """
    Programs executed
    """
    df = df_regex_filter(df_strace, "syscall", "^exec.*")
    df = df[["timestamp", "executable", "syscall", "filepath", "ret_int", "ret_str"]]
    df = df.sort_values(["timestamp"], ascending=True)
    if not df.empty:
        print("\n\n%s:\n" % wrap_text(command_dict[current_func_name()][1]))
        print_df(df)


def count_errors(df_strace):
    """
    Count of failed syscalls
    """
    df = df_strace[(df_strace["ret_int"] == "-1")]
    df = (
        df.groupby(["executable", "syscall", "ret_str"])
        .size()
        .reset_index(name="count")
    )
    df = df[["count", "executable", "syscall", "ret_str"]]
    df = df.sort_values(["count"], ascending=False)
    if not df.empty:
        print("\n\n%s:\n" % wrap_text(command_dict[current_func_name()][1]))
        print_df(df)


def count_files(df_strace, filter_filepath=".+", filter_ret_int=".*"):
    """
    Count of file accesses
    """
    df = df_regex_filter(df_strace, "filepath", filter_filepath)
    df = df_regex_filter(df, "ret_int", filter_ret_int)
    df = df.groupby(["executable", "filepath"]).size().reset_index(name="count")
    df = df[["count", "executable", "filepath"]]
    df = df.sort_values(["count"], ascending=False)
    if not df.empty:
        print("\n\n%s:\n" % wrap_text(command_dict[current_func_name()][1]))
        print_df(df)


def count_device_files(df_strace):
    """
    Count of device file accesses
    """
    count_files(df_strace, filter_filepath=RE_DEVICE_FILE)


def file_access(df_strace, filter_filepath=".+", filter_ret_int=".*"):
    """
    All file accesses in chronological order, including
    both success and failed cases
    """
    df = df_regex_filter(df_strace, "filepath", filter_filepath)
    df = df_regex_filter(df, "ret_int", filter_ret_int)
    df = df[["timestamp", "executable", "syscall", "filepath", "ret_int", "ret_str"]]
    if not df.empty:
        print("\n\n%s:\n" % wrap_text(command_dict[current_func_name()][1]))
        print_df(df)


def file_access_errors(df_strace):
    """
    File accesses in chronological order, including only
    syscalls where the return status indicates an error
    """
    file_access(df_strace, filter_ret_int="^-1$")


def device_file_access(df_strace):
    """
    All device file accesses in chronological order, including
    both successful and failed syscalls
    """
    file_access(df_strace, filter_filepath=RE_DEVICE_FILE)


###############################################################################


command_dict = {
    "summary": (summary, "Summarize strace log file"),
    "programs_executed": (programs_executed, "Programs executed"),
    "count_errors": (count_errors, "Count of failed syscalls"),
    "count_files": (count_files, "Count of file accesses"),
    "count_device_files": (count_device_files, "Count of device file accesses"),
    "file_access": (
        file_access,
        "All file accesses in chronological order, including "
        "both success and failed cases",
    ),
    "file_access_errors": (
        file_access_errors,
        "File accesses in chronological order, including only "
        "syscalls where the return status indicates error",
    ),
    "device_file_access": (
        device_file_access,
        "All device file accesses in chronological order, including "
        "both successful and failed syscalls",
    ),
}


class StraceAnalyzer:
    """Implements strace log analyzer"""

    def __init__(self, strace_csv):
        exit_unless_accessible(strace_csv)
        self.df_strace = df_from_csv_file(strace_csv)

    def analyze_command(self, command):
        """Run the specified command"""
        command_tuple = command_dict.get(command)
        if command_tuple:
            func = command_tuple[0]
            func(self.df_strace)
        else:
            _LOGGER.error("Unknown command: '%s'", command)


################################################################################


def _command_help():
    ret = "\n"
    for command, command_tuple in command_dict.items():
        ret = ret + "\n%-10s:\n  %s\n" % (
            "'" + command + "'",
            wrap_text(command_tuple[1], lilen=50, indent="  "),
        )
    return ret + "\n"


class _SmartFormatter(argparse.HelpFormatter):
    def _split_lines(self, text, width):
        if text.startswith("R|"):
            return text[2:].splitlines()
        return argparse.HelpFormatter._split_lines(self, text, width)


def getargs():
    """Parse command line arguments"""
    desc = (
        "Analyze and query strace log given the strace log in CSV format "
        "(STRACE_CSV). See 'strace2csv.py' for converting strace "
        "log to the csv format expected by this tool."
    )
    epil = "Example: ./%s strace.csv summary" % os.path.basename(__file__)
    parser = argparse.ArgumentParser(
        description=desc, epilog=epil, formatter_class=_SmartFormatter
    )

    helpstr = "path to strace log in csv format (output from strace2csv.py)"
    parser.add_argument("STRACE_CSV", nargs=1, help=helpstr)

    helpstr = "R|specify output details, one of the following strings:"
    parser.add_argument("COMMAND", nargs=1, help=helpstr + _command_help())

    helpstr = "set the verbose level between 0-3 (defaults to --verbose=1)"
    parser.add_argument("--verbose", help=helpstr, type=int, default=1)

    return parser.parse_args()


################################################################################


def main():
    """main entry point"""
    args = getargs()
    setup_logging(args.verbose)
    analyzer = StraceAnalyzer(args.STRACE_CSV[0])
    analyzer.analyze_command(args.COMMAND[0])


if __name__ == "__main__":
    main()

################################################################################
