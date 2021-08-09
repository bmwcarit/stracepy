<!--
SPDX-FileCopyrightText: 2021 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)

SPDX-License-Identifier: MIT
-->

# Stracepy

This repository is a collection of scripts to help parse and analyze [strace](https://strace.io/) logs. The tools are capable of handling strace logs from multithreaded applications.

Table of Contents
=================

 * [Getting Started](#getting-started)
    * [Installation](#installation)
 * [Getting strace logs](#getting-strace-logs)
    * [Convert strace log to csv](#convert-strace-log-to-csv)
    * [Using strace_analyzer to analyze strace session](#using-strace_analyzer-to-analyze-strace-session)
    * [Show strace session summary](#show-strace-session-summary)
    * [Summarize files accessed](#summarize-files-accessed)
    * [Show all file accesses chronologically](#show-all-file-accesses-chronologically)
    * [Summarize device files accessed](#summarize-device-files-accessed)
    * [Show device file accesses chronologically](#show-device-file-accesses-chronologically)
 * [Contribute](#contribute)
 * [License](#license)

## Getting Started
Scripts require python3:
```
$ sudo apt install python3 python3-pip
```

In addition, the scripts rely on a number of python packages specified in [requirements.txt](./requirements.txt). You can install the required packages with:
```
$ pip3 install -r requirements.txt
```
### Installation
This README.md assumes you have installed the stracepy command line tools on your system. To install the tools from source, run:
```
$ python3 setup.py install
```

## Getting strace logs
The tools in this repository help parse and analyze [strace](https://strace.io/) logs. As the main input, the tools expect strace log from strace session where the strace was invoked with the following flags: `-f -tt -T -y -yy -s 2048`. For the sake of example, in the following sections of this README, we will use a strace log from running command `firefox` as follows:
```
$ strace -f -tt -T -y -yy -s 2048 -o strace_firefox.log firefox & \
sleep 5; \
killall firefox
```
The above command generates strace log to file `strace_firefox.log` which contains the syscalls from the first five seconds of running the firefox command.

### Convert strace log to csv
To begin, you first need to convert the collected strace log to structured format by using the [strace2csv.py](./stracepy/strace2csv.py). To continue our [earlier example](#getting-strace-logs) with firefox, convert the collected strace log to csv:
```
$ strace2csv strace_firefox.log --out strace_firefox.csv
INFO     Parsing strace log: 'strace_firefox.log'
INFO     Wrote: strace_firefox.csv
```
Output file `strace_firefox.csv` is a CSV database that lists all syscalls from the strace log in chronological order by the timestamp the syscall returned. For each syscall, the CSV database includes fields such as: 'timestamp', 'pid', 'executable', and 'syscall' parsed from the strace log. Fields 'ret_int' and 'ret_str' specify syscall return status information. Fields 'filepath' and 'all_filepaths' include filepaths parsed from the strace log entry for the specific syscall based on [heuristic](./stracepy/strace2csv.py#L316).

The output from [strace2csv.py](strace2csv.py) (`strace_firefox.csv`) can be used as an input file to [strace_analyzer.py](./stracepy/strace_analyzer.py) to query the structured strace data. For examples, see the following section.

### Using strace_analyzer to analyze strace session
[strace_analyzer.py](./stracepy/strace_analyzer.py) allows analyzing and querying strace session details, given the strace log in [CSV format](#convert-strace-log-to-csv). For the full list of supported commands, see the command line help with `strace_analyzer --help`. Below sections show selected example queries using the CSV database from the [example strace session](#getting-strace-logs) as a demonstration.

### Show strace session summary
Command `summary` shows overview of executed programs in the strace session, as well as summary of the failed syscalls:
```
$ strace_analyzer strace_firefox.csv summary
INFO     Reading: strace_firefox.csv


Programs executed:

 timestamp       | executable               | syscall   | filepath                 |   ret_int | ret_str
-----------------+--------------------------+-----------+--------------------------+-----------+-----------
 12:02:35.655632 | /usr/bin/firefox         | execve    | /usr/bin/firefox         |         0 |
 12:02:35.663762 | /usr/bin/which           | execve    | /usr/bin/which           |         0 |
 12:02:35.670262 | /usr/lib/firefox/firefox | execve    | /usr/lib/firefox/firefox |         0 |
 12:02:36.125408 | /usr/bin/lsb_release     | execve    | /usr/bin/lsb_release     |         0 |
 12:02:37.369263 | /usr/lib/firefox/firefox | execve    | /usr/lib/firefox/firefox |         0 |
 12:02:38.726665 | /usr/lib/firefox/firefox | execve    | /usr/lib/firefox/firefox |         0 |



Count of failed syscalls:

   count | executable               | syscall      | ret_str
---------+--------------------------+--------------+-------------------------------------------
    6251 | /usr/lib/firefox/firefox | recvmsg      | EAGAIN (Resource temporarily unavailable)
    2066 | /usr/lib/firefox/firefox | futex        | EAGAIN (Resource temporarily unavailable)
    1922 | /usr/lib/firefox/firefox | stat         | ENOENT (No such file or directory)
    1674 | /usr/lib/firefox/firefox | openat       | ENOENT (No such file or directory)
     599 | /usr/lib/firefox/firefox | access       | ENOENT (No such file or directory)
     300 | /usr/lib/firefox/firefox | futex        | ETIMEDOUT (Connection timed out)
     297 | /usr/lib/firefox/firefox | readlink     | EINVAL (Invalid argument)
     105 | /usr/bin/lsb_release     | stat         | ENOENT (No such file or directory)
      65 | /usr/bin/lsb_release     | ioctl        | ENOTTY (Inappropriate ioctl for device)
      36 | /usr/lib/firefox/firefox | mkdir        | EEXIST (File exists)
      ...
```

### Summarize files accessed
Command `count_files` shows summary of all files accessed in the strace session ordered by the number of times the specific file was accessed. The below output is truncated to include only the topmost entries from our [example strace session](#getting-strace-logs).

```
$ strace_analyzer strace_firefox.csv count_files
INFO     Reading: strace_firefox.csv


Count of file accesses:

   count | executable               | filepath
---------+--------------------------+------------------------------------------------------------------------
    1429 | /usr/lib/firefox/firefox | /memfd:mozilla-ipc (deleted)
     350 | /usr/lib/firefox/firefox | /etc/hosts
     221 | /usr/lib/firefox/firefox | /usr/lib/firefox/browser/features/webcompat@mozilla.org.xpi
     184 | /usr/lib/firefox/firefox | /etc/ld.so.cache
      89 | /usr/lib/firefox/firefox | /sys/devices/system/cpu/present
      73 | /usr/lib/firefox/firefox | /proc/588127/maps
      68 | /usr/lib/firefox/firefox | /usr/lib/firefox/browser/features/pictureinpicture@mozilla.org.xpi
      66 | /usr/lib/firefox/firefox | /proc/588244/maps
      66 | /usr/lib/firefox/firefox | /proc/588195/maps
      ...
```

### Show all file accesses chronologically
Command `file_access` lists all syscalls that accessed files in chronological order by the syscall timestamp. The below output is truncated to include only the first few entries from our [example strace session](#getting-strace-logs).
```
$ All file accesses in chronological order, including both success and failed
cases:

 timestamp       | executable         | syscall  | filepath            | ret_int | ret_str
-----------------+--------------------+----------+---------------------+---------+-------------------------------------
 12:02:35.655632 | /usr/bin/firefox   | execve   | /usr/bin/firefox    |       0 |
 12:02:35.656172 | /usr/bin/firefox   | access   | /etc/ld.so.preload  |      -1 | ENOENT (No such file or directory)
 12:02:35.657436 | /usr/bin/firefox   | openat   | /etc/ld.so.cache    |       3 | </etc/ld.so.cache>
 12:02:35.657501 | /usr/bin/firefox   | fstat    | /etc/ld.so.cache    |       0 |
 12:02:35.657576 | /usr/bin/firefox   | close    | /etc/ld.so.cache    |       0 |
...
```
### Summarize device files accessed
Command `count_device_files` shows summary of all device files accessed in the strace session ordered by the number of times the specific file was accessed. Device files are identified based on matching the file path with [heuristic](./stracepy/strace_analyzer.py#L30).
```
$ strace_analyzer strace_firefox.csv count_device_files
INFO     Reading: strace_firefox.csv


Count of file accesses:

   count | executable               | filepath
---------+--------------------------+----------------------------------
      89 | /usr/lib/firefox/firefox | /sys/devices/system/cpu/present
      22 | /usr/lib/firefox/firefox | /dev/urandom
      16 | /usr/lib/firefox/firefox | /sys/devices/system/cpu
      13 | /usr/bin/lsb_release     | /dev/pts/18
       9 | /usr/lib/firefox/firefox | /dev/pts/18
       5 | /usr/lib/firefox/firefox | /dev/null
       4 | /usr/lib/firefox/firefox | /dev/dri/card0
       4 | /usr/lib/firefox/firefox | /dev/shm
       ...
```

### Show device file accesses chronologically
Command `device_file_access` lists all syscalls that accessed any device files in chronological order by the syscall timestamp. 
```
$ strace_analyzer strace_firefox.csv device_file_access
INFO     Reading: strace_firefox.csv


All file accesses in chronological order, including both success and failed
cases:

 timestamp       | executable               | syscall    | filepath    | ret_int | ret_str
-----------------+--------------------------+------------+-------------+---------+------------------------
 12:02:35.661337 | /usr/bin/firefox         | dup2       | /dev/pts/18 |       1 | <pipe:[357072124]>
 12:02:35.767046 | /usr/lib/firefox/firefox | openat     | /dev/null   |       3 | </dev/null<char 1:3>>
 12:02:35.767170 | /usr/lib/firefox/firefox | dup2       | /dev/null   |       1 | </dev/null<char 1:3>>
 12:02:35.767296 | /usr/lib/firefox/firefox | dup2       | /dev/null   |       2 | </dev/null<char 1:3>>
 12:02:35.767322 | /usr/lib/firefox/firefox | close      | /dev/null   |       0 |
 ...
```
## Contribute
Any pull requests, suggestions, and error reports are welcome.
To start development, we recommend using lightweight [virtual environments](https://docs.python.org/3/library/venv.html) by running the following commands:
```
$ git clone https://github.com/bmwcarit/stracepy.git
$ cd stracepy/
$ python3 -mvenv venv
$ source venv/bin/activate
$ export PYTHONPATH=$PYTHONPATH:$(pwd)
```
Next, run `make install-requirements` to set up the virtualenv:
```
$ make install-requirements
```
Run `make help` to see the list of other make targets.
Prior to sending any pull requests, make sure at least the `make pre-push` runs successfully.

To deactivate the virtualenv, run `deactivate` in your shell.


## License
This project is licensed under the MIT license - see the [MIT.txt](LICENSES/MIT.txt) file for details.
