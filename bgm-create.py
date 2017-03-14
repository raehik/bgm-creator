#!/usr/bin/env python3
#
# Create a 'BGM' track for a given 'main' track and merge them.
#

import sys
import os
import subprocess
import random
import argparse

track_root = os.environ["HOME"] + "/media/music"
playlist = "best"

## Argument parsing {{{
"""Argparse override to print usage to stderr on argument error."""
class ArgumentParserUsage(argparse.ArgumentParser):
    def error(self, message):
        sys.stderr.write("error: %s\n" % message)
        self.print_help(sys.stderr)
        sys.exit(2)

parser = ArgumentParserUsage(description="Create a 'BGM' track for a given 'main' track and merge them.")

# add arguments
parser.add_argument("-v", "--verbose", action="store_true",
                    help="be verbose")
parser.add_argument("main_file",
                    help="main file to fit the BGM to")
parser.add_argument("out_with_bgm",
                    help="name of output file")
parser.add_argument("-b", "--bgm-volume", default="0.5",
		    help="volume of BGM between 0-1 (default: 0.01)")

# parse arguments
args = parser.parse_args()
## }}}

## Logging {{{
FILENAME = sys.argv[0]

"""Log a message to a specific pipe (defaulting to stdout)."""
def log_message(message, pipe=sys.stdout):
    print(FILENAME + ": " + message, file=pipe)

"""If verbose, log an event."""
def log(message):
    if not args.verbose:
        return
    log_message(message)

"""Log an error. If given a 2nd argument, exit using that error code."""
def error(message, exit_code=None):
    log_message("error: " + message, sys.stderr)
    if exit_code:
        sys.exit(exit_code)
## }}}

def run_command(args):
    """Run a command, returning the output and a boolean value indicating
    whether the command failed or not."""
    was_successful = True

    # execute using a shell so we can use piping & redirecting
    proc = subprocess.Popen(args, stdout=subprocess.PIPE)
    out, err = proc.communicate()

    if proc.returncode != 0:
        was_successful = False

    return out.decode("utf-8").strip(), was_successful

def file_of_track(track):
    """Get a track's filepath."""
    return "{}/{}".format(track_root, track)

def length_of_file(f):
    """Get the length of an audio file in seconds."""
    if not os.path.isfile(f):
        error("not a file: {}".format(f))
    length, successful = run_command(["ffprobe", "-i", f, "-show_entries", "format=duration", "-v", "quiet", "-of", "csv=p=0"])
    return float(length)

tracks_str, successful = run_command(["mpc", "playlist", "-f", "%file%", playlist])
tracks = tracks_str.splitlines()
random.shuffle(tracks)

main_length = length_of_file(args.main_file)
bgm_length = 0
bgm_files = []
while main_length > bgm_length:
    track = tracks.pop()
    log("BGM: {}".format(track))
    bgm_files.append(file_of_track(track))
    bgm_length += length_of_file(file_of_track(track))

## Form FFmpeg command {{{
### Filtergraph {{{
concat_inputs = "".join(["[{}:0]".format(track_num) for track_num in range(1, len(bgm_files)+1)])
filter_concat = "{} concat=n={}:v=0:a=1 [bgm]".format(concat_inputs, len(bgm_files))
filter_amerge_pan = "[bgm][0:0] amerge=inputs=2, pan=stereo|FL<{0}*FL+FC|FR<{0}*FR+FC [merged]".format(args.bgm_volume)

filtergraph = "{};{}".format(filter_concat, filter_amerge_pan)
### }}}

out_quality = ["-q:a", "3"]
concat_cmd = ["ffmpeg"]
concat_cmd.extend(["-i", args.main_file])
concat_cmd.extend([part for f in bgm_files for part in ("-i", f)])
concat_cmd.extend(["-filter_complex", filtergraph, "-map", "[merged]"])
concat_cmd.extend(out_quality)
concat_cmd.append(args.out_with_bgm)
## }}}

run_command(concat_cmd)
