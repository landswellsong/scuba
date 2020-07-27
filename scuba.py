#!/usr/bin/env python3

from subprocess import Popen, PIPE, call
import json
import os
import sys
import argparse

# TODO: exceptions everywhere

def popen_text(cmd):
    """
    Shortcut for Popen, universal_newlines is for compatibility with python3.5
    Otherwise use text=True
    """
    return Popen(cmd, stdout=PIPE, universal_newlines=True)

def containers():
    """
    Yield currently running containers for iteration
    """
    # TODO: can there be multiple names?
    cmd = [ 'docker', 'ps', '--format', '{{.Names}}' ]
    with popen_text(cmd) as docker:
        for ln in docker.stdout:
            yield ln[:-1]

def probe_path_in_container(container, path):
    """
    Try to resolve the path argument to a path inside container

    Returns path on sucess and None on failure
    """
    cmd = [ 'docker', 'inspect', '--format', '{{json .Mounts}}', container ]
    with popen_text(cmd) as docker:
        for volume in json.load(docker.stdout):
            # TODO: do we need to skip some of the types? D'uh
            if path.startswith(volume['Source']):
                # TODO: may the path have a trailing slash?
                return volume['Destination'] + path[len(volume['Source']):]
    return None

def lookup_container(path):
    """
    Look for a [first!] container that has the path mounted

    Returns a container name and resolved path tuple
    """
    for container in containers():
        rpath = probe_path_in_container(container, path)
        if rpath:
            return container, rpath
    return None, None


parser = argparse.ArgumentParser(description="Run a docker command in a container that mounts the current directory.")
parser.add_argument('-s', '--superuser', action='store_true', help = "Run as superuser")
parser.add_argument('-y', '--notty', action='store_true', help = "Disable interactive mode and don't allocate a TTY (-it options for docker)")
parser.add_argument('command', metavar="CMD", help = "Command to run")
parser.add_argument('args', metavar="ARG", nargs=argparse.REMAINDER, help = "Command arguments")
args = parser.parse_args()

# TODO: no program to run etc arguments checks
container, path = lookup_container(os.getcwd())
if container and path and args.command:
    opts = []
    # TODO: shell expansion? (you won't be able to easily use them anyway tho)
    opts += ['-w', path]
    if not args.superuser:
        opts += ['-u', '{}:{}'.format(os.getuid(), os.getgid())]
    if not args.notty:
        opts += ['-it']
    # TODO: tty/interactive mode
    call(['docker', 'exec'] +  opts + [ container, args.command ] + args.args)
else:
    # TODO: stderr
    print("No container mounting path: '%s' is found. Forgot to start?" % os.getcwd())
