#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2021 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)
#
# SPDX-License-Identifier: MIT

# pylint: disable=no-self-use, invalid-name, too-many-arguments

""" This tool parses strace output to structured format """

import argparse
import os
import sys
import re
import logging

import pandas as pd

from stracepy.utils import (
    df_to_csv_file,
    current_func_name,
    exit_unless_accessible,
    setup_logging,
    function_timeout,
    FunctionTimeoutError,
    LOGGER_NAME,
    LOG_SPAM,
)

###############################################################################

_LOGGER = logging.getLogger(LOGGER_NAME)

###############################################################################


class StraceParser:
    """Implements strace log parser"""

    def __init__(self, strace_log):
        self.strace_log = strace_log
        exit_unless_accessible(self.strace_log)
        # Dictionary to store exec syscall details to be able to map pid with
        # bin_file. Key: pid, Value: bin_file
        self.exec_map = {}
        # Dictionary to store unfinished syscalls encountered when parsing
        # the strace log. Key: str(pid)+str(syscall), Value: [timestamp,args]
        self.unfinished_syscalls_stash = {}
        # Dictionary to store parsed strace log entries
        # Key: column header, Value: list of values for 'column-header'-column
        self.entries = {}

    def parse(self):
        """Parse strace log"""
        _LOGGER.info("Parsing strace log: '%s'", self.strace_log)
        with open(self.strace_log) as in_file:
            for line in in_file:
                self._parse_strace_line(line)

    def to_csv(self, filename):
        """Output the parsed data as csv file"""
        df = pd.DataFrame(self.entries)
        df_to_csv_file(df, filename)

    def _parse_strace_line(self, line):
        line = line.rstrip("\n")
        # _LOGGER.log(LOG_SPAM, "line: %s", line)

        # All strace log entries should contain pid and timestamp
        pid, timestamp, rest = self._match_pid_timestamp(line)

        # Match 'unfinished' entries, where the return status is not yet known
        syscall, args = self._match_unfinished(rest)
        if syscall:
            # Stash the 'unfinished' entry for now, we'll resume processing
            # this entry when we encounter the corresponding 'resumed' entry
            self._stash_unifinished(line, pid, timestamp, syscall, args)
            return

        # Match 'resumed' entries
        syscall, args, ret_int, ret_str, time = self._match_resumed(rest)
        if syscall:
            # Find the 'unfinished' entry that corresponds this 'resumed' entry.
            # For the timestamp, we use the timestamp the syscall resumed, not
            # the timestamp when the call was initiated (_stashed_timestamp)
            _stashed_timestamp, stashed_args = self._unstash_on_resume(
                line, pid, syscall
            )
            args = stashed_args + args
            # Find filepaths that appear in the args or ret_str, limiting
            # the search to first n-characters of each
            filepaths = find_filepaths(args[:500] + ret_str[:500])
            foundby = "resumed"
            # We now have all the fields populated for the previously
            # 'unfinished' entry: store it now and move on to the next log entry
            self._add_entry(
                pid,
                timestamp,
                syscall,
                args,
                filepaths,
                ret_int,
                ret_str,
                time,
                foundby,
                line,
            )
            return

        # Match 'complete' entries
        syscall, args, ret_int, ret_str, time = self._match_complete(rest)
        if syscall:
            # Find filepaths that appear in the args or ret_str, limiting
            # the search to first n-characters of each
            filepaths = find_filepaths(args[:500] + ret_str[:500])
            foundby = "complete"
            # Store the entry and move on to the next log entry
            self._add_entry(
                pid,
                timestamp,
                syscall,
                args,
                filepaths,
                ret_int,
                ret_str,
                time,
                foundby,
                line,
            )
            return

        # For debugging: log entries that didn't match any parsers
        _LOGGER.log(LOG_SPAM, "Nothing parsed from line: '%s'", line)

    def _match_pid_timestamp(self, line):
        re_pid_tstamp = re.compile(r"^(?P<pid>\d+)\s+(?P<tstamp>[^ ]+)\s+(?P<rest>.*)$")
        match = re_pid_tstamp.match(line)
        if not match:
            _LOGGER.error("Strace log is missing pid and/or timestamp: %s", line)
            _LOGGER.error("Hint: run strace with options: '-f -tt -T -y -yy -s 2048'")
            sys.exit(1)
        pid = match.group("pid")
        tstamp = match.group("tstamp")
        rest = match.group("rest")
        return (pid, tstamp, rest)

    def _match_unfinished(self, rest):
        re_unfinished = re.compile(
            r"^(?P<syscall>[0-9a-z_]+)\((?P<args>.*)\s+<unfinished\s+\.\.\.>$"
        )
        syscall = args = ""
        match = re_unfinished.match(rest)
        if match:
            syscall = match.group("syscall")
            args = match.group("args")
        return (syscall, args)

    def _match_resumed(self, rest):
        re_resumed_1 = re.compile(
            r"^<\.\.\.\s+(?P<syscall>[0-9a-z_]+)\s+resumed>(?P<args>.*)\)\s+=\s+"
            r"(?P<ret_int>-?[?\d]+)(?P<ret_str>.*)<(?P<time>[\d][^>]+)>$"
        )
        re_resumed_2 = re.compile(
            r"^<\.\.\.\s+(?P<syscall>[0-9a-z_]+)\s+resumed>(?P<args>.*)\)\s+=\s+"
            r"(?P<ret_int>\?)$"
        )
        match = syscall = args = ret_int = ret_str = time = ""

        # First, try matching re_resumed_1
        if not match:
            match = re_resumed_1.match(rest)
            if match:
                syscall = match.group("syscall")
                args = match.group("args")
                ret_int = match.group("ret_int")
                ret_str = match.group("ret_str")
                time = match.group("time")

        # Try matching re_resumed_2 if the first match failed
        if not match:
            match = re_resumed_2.match(rest)
            if match:
                syscall = match.group("syscall")
                args = match.group("args")
                ret_int = match.group("ret_int")

        return (syscall, args, ret_int, ret_str, time)

    def _match_complete(self, rest):
        re_complete = re.compile(
            r"^(?P<syscall>[0-9a-z_]+)\((?P<args>.*)\)\s+=\s+"
            r"(?P<ret_int>-?\d+|\?)(?P<ret_str>.*)<(?P<time>[\d][^>]+)>$"
        )
        syscall = args = ret_int = ret_str = time = ""
        match = re_complete.match(rest)
        if match:
            syscall = match.group("syscall")
            args = match.group("args")
            ret_int = match.group("ret_int")
            ret_str = match.group("ret_str")
            time = match.group("time")
        return (syscall, args, ret_int, ret_str, time)

    def _stash_unifinished(self, line, pid, timestamp, syscall, args):
        key = str(pid) + str(syscall)
        if key in self.unfinished_syscalls_stash:
            _LOGGER.error("Duplicate unfinished syscalls: %s", line)
            sys.exit(1)
        value = [timestamp, args]
        self.unfinished_syscalls_stash[key] = value

    def _unstash_on_resume(self, line, pid, syscall):
        key = str(pid) + str(syscall)
        if key not in self.unfinished_syscalls_stash:
            _LOGGER.error("No 'unfinished' entry for: %s", line)
            sys.exit(1)
        value = self.unfinished_syscalls_stash[key]
        del self.unfinished_syscalls_stash[key]
        timestamp = value[0]
        args = value[1]
        return (timestamp, args)

    def _get_bin_file(self, syscall, pid, filepath, ret_int, line):
        bin_file = ""

        # Sanity check
        if pid == "" or syscall == "" or ret_int == "" or ret_int == "?":
            return bin_file
        ret_int = int(ret_int)

        # Handle 'exec*' syscalls
        if syscall.startswith("exec") and ret_int >= 0:
            if filepath == "":
                _LOGGER.error("Missing filepath from exec* syscall: '%s'", line)
                sys.exit(1)
            bin_file = filepath
            # Add/replace the entry in exec_map:
            self.exec_map[pid] = bin_file

        # Handle 'clone' from parent process
        elif syscall == "clone" and ret_int >= 0:
            # clone returns the thread id of the child process
            child_pid = str(ret_int)
            # Child process initially executes the same program as the parent
            if pid not in self.exec_map:
                _LOGGER.error("Parent program unknown: '%s'", line)
                sys.exit(1)
            bin_file = self.exec_map[pid]
            # Add/replace the entry in exec_map:
            self.exec_map[child_pid] = bin_file

        # Other syscalls
        else:
            if pid not in self.exec_map:
                _LOGGER.debug("pid '%s' unknown executable", pid)
                bin_file = ""
            else:
                bin_file = self.exec_map[pid]

        return bin_file

    def _add_entry(
        self,
        pid,
        timestamp,
        syscall,
        args,
        filepaths,
        ret_int,
        ret_str,
        time,
        foundby,
        line,
    ):

        # Populate 'first_filepath' and 'all_filepaths'
        first_filepath = ""
        if filepaths:
            first_filepath = filepaths[0]
        all_filepaths = str(filepaths)

        # Populate 'bin_file'
        bin_file = self._get_bin_file(syscall, pid, first_filepath, ret_int, line)

        # Add entry to entries dictionary
        setcol = self.entries.setdefault
        setcol("timestamp", []).append(timestamp)
        setcol("pid", []).append(pid)
        setcol("executable", []).append(bin_file)
        setcol("syscall", []).append(syscall)
        setcol("filepath", []).append(first_filepath)
        setcol("all_filepaths", []).append(all_filepaths)
        setcol("ret_int", []).append(ret_int)
        setcol("ret_str", []).append(ret_str.strip())
        setcol("syscall_time", []).append(time)
        # Following fields are only for debugging purposes
        if _LOGGER.level != logging.NOTSET and _LOGGER.level <= logging.DEBUG:
            setcol("args", []).append(args)
            setcol("found_by", []).append(foundby)
        if _LOGGER.level != logging.NOTSET and _LOGGER.level <= LOG_SPAM:
            setcol("strace_line", []).append(line)


###############################################################################


# Timeout find_filepaths function afer 0.1 seconds
@function_timeout(0.1)
def find_filepaths(from_str, retry=True):
    """Attempt to match strings that look like file paths in strace log entry"""
    try:
        # This is pretty rough heuristic and might match both
        # false positives and false negatives
        re_file = r'\b[^<>*\\"\[\]|\']{1,256}'
        re_filepath = re.compile(
            r"("
            rf"<(?:(?:{re_file})?(?:\.{{0,2}}\/{re_file})+?)>|"
            rf"<(?:(?:{re_file})?(?:\.{{0,2}}\/{re_file})+?)<|"
            rf'"(?:(?:{re_file})?(?:\.{{0,2}}\/{re_file})+?)"'
            r")"
        )
        # matching strings with duplicates removed, maintaining order
        matches = list(dict.fromkeys(re.findall(re_filepath, from_str)))
        # Remove first and last character from each match. This is needed
        # because the above regular expressions include the leading and
        # trailing <, >, or " and we don't want them in the returned list
        # of strings.
        matches = [elem[1:-1] for elem in matches]
        return matches
    except FunctionTimeoutError as _ex:
        _LOGGER.debug("timed-out while matching: '%s'", from_str[:100] + "...")
        if retry:
            # If the regex match timed-out, retry the match
            # reducing the string to 200 characters
            from_str = from_str[0:200]
            return find_filepaths(from_str, False)

        _LOGGER.warning("%s failed matching: '%s'", current_func_name(), from_str)
        return [""]


################################################################################


def getargs():
    """Parse command line arguments"""
    desc = (
        "This tool parses strace output STRACE_LOG to structured format. "
        "Output [OUT] is a CSV file that allows post-processing the "
        "strace output log with other tools that can digest CSV data. "
        "This tool assumes STRACE_LOG "
        "was generated with strace options '-f -tt -T -y -yy -s 2048'. "
    )
    epil = "Example: ./%s strace.log" % os.path.basename(__file__)
    parser = argparse.ArgumentParser(description=desc, epilog=epil)

    helpstr = "path to strace log file"
    parser.add_argument("STRACE_LOG", nargs=1, help=helpstr)

    helpstr = "set the output file name, default is 'strace.csv'"
    parser.add_argument("--out", nargs="?", help=helpstr, default="strace.csv")

    helpstr = "set the verbose level between 0-3 (defaults to --verbose=1)"
    parser.add_argument("--verbose", help=helpstr, type=int, default=1)

    return parser.parse_args()


################################################################################


def main():
    """main entry point"""
    parsed_args = getargs()
    setup_logging(parsed_args.verbose)
    strace_parser = StraceParser(parsed_args.STRACE_LOG[0])
    strace_parser.parse()
    strace_parser.to_csv(parsed_args.out)


if __name__ == "__main__":
    main()

################################################################################
