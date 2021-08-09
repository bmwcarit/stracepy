#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2021 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)
#
# SPDX-License-Identifier: MIT

# pylint: disable=invalid-name, protected-access, unnecessary-pass

""" Stracepy utils """

import os
import sys
import re
import csv
import logging
import signal
import errno
from functools import wraps

from tabulate import tabulate
import pandas as pd
from colorlog import ColoredFormatter, default_log_colors

###############################################################################

LOGGER_NAME = "stracepy-logger"
LOG_SPAM = logging.DEBUG - 1

###############################################################################


def current_func_name():
    """Return the name of the current function"""
    return sys._getframe(1).f_code.co_name


def df_to_csv_file(df, name):
    """Write dataframe to csv file"""
    df.to_csv(
        path_or_buf=name, quoting=csv.QUOTE_ALL, sep=",", index=False, encoding="utf-8"
    )
    logging.getLogger(LOGGER_NAME).info("Wrote: %s", name)


def df_from_csv_file(name):
    """Read csv file into dataframe"""
    logging.getLogger(LOGGER_NAME).info("Reading: %s", name)
    try:
        df = pd.read_csv(name, keep_default_na=False, dtype=str)
        df.reset_index(drop=True, inplace=True)
        return df
    except pd.errors.ParserError:
        logging.getLogger(LOGGER_NAME).fatal("Not a csv file: '%s'", name)
        sys.exit(1)


def exit_unless_accessible(filename):
    """Exit if filename is not accessible"""
    if filename and not os.path.isfile(filename):
        sys.stderr.write("Error: file not found or no permissions: %s\n" % filename)
        sys.exit(1)


def setup_logging(verbosity=1):
    """Setup logging with specified verbosity"""
    project_logger = logging.getLogger(LOGGER_NAME)

    if verbosity == 0:
        level = logging.NOTSET
    elif verbosity == 1:
        level = logging.INFO
    elif verbosity == 2:
        level = logging.DEBUG
    else:
        level = LOG_SPAM

    if level <= logging.DEBUG:
        logformat = (
            "%(log_color)s%(levelname)-8s%(reset)s "
            "%(filename)s:%(funcName)s():%(lineno)d - "
            "%(message)s"
        )
    else:
        logformat = "%(log_color)s%(levelname)-8s%(reset)s %(message)s"

    default_log_colors["INFO"] = "fg_bold_white"
    default_log_colors["DEBUG"] = "fg_bold_white"
    default_log_colors["SPAM"] = "fg_bold_white"
    formatter = ColoredFormatter(logformat, log_colors=default_log_colors)
    stream = logging.StreamHandler()
    stream.setFormatter(formatter)
    logging.addLevelName(LOG_SPAM, "SPAM")
    project_logger.addHandler(stream)
    project_logger.setLevel(level)


def print_df(df, tablefmt="presto"):
    """Pretty-print dataframe to stdout"""
    if df.empty:
        return
    df = df.fillna("")
    print(
        tabulate(
            df, headers="keys", tablefmt=tablefmt, stralign="left", showindex=False
        )
    )
    print("")


def df_regex_filter(df, column, regex):
    """Filter dataframe based on regex matching for specified column"""
    return df[df[column].str.contains(regex, regex=True, na=False)]


def wrap_text(text, lilen=80, indent=""):
    """Wrap text to max lilen length lines"""
    text = text.replace("\n", " ")
    text = text.replace("\t", " ")
    text = " ".join(text.split())
    return ("\n%s" % indent).join(
        line.strip() for line in re.findall(r".{1,%s}(?:\s+|$)" % lilen, text)
    )


###############################################################################


class FunctionTimeoutError(Exception):
    """Function timeout exception"""

    pass


def function_timeout(seconds, error_message=os.strerror(errno.ETIME)):
    """
    Decorator that can be applied to long running functions for timeout.
    Notice: this is not thread-safe!
    Ref: https://stackoverflow.com/questions/2281850
    """

    def decorator(func):
        def _handle_timeout(signum, frame):
            raise FunctionTimeoutError(error_message)

        def wrapper(*args, **kwargs):
            signal.signal(signal.SIGALRM, _handle_timeout)
            signal.setitimer(signal.ITIMER_REAL, seconds)
            try:
                result = func(*args, **kwargs)
            finally:
                signal.alarm(0)
            return result

        return wraps(func)(wrapper)

    return decorator


################################################################################
