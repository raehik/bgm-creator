#!/usr/bin/env python3
#
# Create a 'BGM' track for a given 'main' track and merge them.
#

import sys
import os
import subprocess
import random
import argparse

## Argument parsing (inc. default values) {{{
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
parser.add_argument("outfile",
                    help="name of output file")
parser.add_argument("-b", "--bgm-volume", default="0.01",
		    help="volume of BGM between 0-1 (default: 0.01)")
parser.add_argument("-d", "--track-root", default=os.environ["HOME"] + "/media/music",
		    help="directory of all tracks in given playlist (default: ~/media/music")
parser.add_argument("-f", "--fade-duration", default=10,
		    help="fade in/out duration for BGM (default: 10)")
parser.add_argument("-p", "--playlist", default="best",
		    help="MPD playlist to use (default: best)")

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

    proc = subprocess.Popen(args, stdout=subprocess.PIPE)
    out, err = proc.communicate()

    if proc.returncode != 0:
        was_successful = False

    return out.decode("utf-8").strip(), was_successful

def file_of_track(track):
    """Get a track's filepath."""
    return "{}/{}".format(args.track_root, track)

def length_of_file(f):
    """Get the length of an audio file in seconds."""
    if not os.path.isfile(f):
        error("not a file: {}".format(f))
    length, successful = run_command(["ffprobe", "-i", f, "-show_entries", "format=duration", "-v", "quiet", "-of", "csv=p=0"])
    return float(length)

tracks_str, successful = run_command(["mpc", "playlist", "-f", "%file%", args.playlist])
tracks = tracks_str.splitlines()
random.shuffle(tracks)

main_length = length_of_file(args.main_file)
bgm_length = 0
bgm_files = []
while main_length > bgm_length:
    track = tracks.pop()
    print("BGM: {}".format(track))
    bgm_files.append(file_of_track(track))
    bgm_length += length_of_file(file_of_track(track))

## Form conversion command {{{
### Filtergraph {{{
concat_inputs = "".join(["[{}:0]".format(track_num) for track_num in range(1, len(bgm_files)+1)])

f_concat = "{} concat=n={}:v=0:a=1".format(concat_inputs, len(bgm_files))
f_atrim = "atrim=duration={}".format(main_length)
f_afade_in = "afade=type=in:duration={}".format(args.fade_duration)
f_afade_out = "afade=type=out:start_time={}:duration={}".format(main_length - args.fade_duration, args.fade_duration)
chain_bgm = "{}, {}, {}, {} [bgm]".format(f_concat, f_atrim, f_afade_in, f_afade_out)

f_amerge = "[bgm][0:0] amerge=inputs=2"
f_pan = "pan=stereo|FL<{0}*FL+FC|FR<{0}*FR+FC".format(args.bgm_volume)
chain_merge = "{}, {} [merged]".format(f_amerge, f_pan)

filtergraph = "{}; {}".format(chain_bgm, chain_merge)
### }}}

out_quality = ["-q:a", "3"]
convert_cmd = ["ffmpeg"]
convert_cmd.extend(["-i", args.main_file])
convert_cmd.extend([part for f in bgm_files for part in ("-i", f)])
convert_cmd.extend(["-filter_complex", filtergraph, "-map", "[merged]"])
convert_cmd.extend(out_quality)
convert_cmd.append(args.outfile)
## }}}

run_command(convert_cmd)
