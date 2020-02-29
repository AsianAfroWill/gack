#!/usr/bin/env python3

import argparse
import sys

from gack import GackRepo

class ArgParser:
    def __init__(self):
        pass

    def parse_args(self, argv):
        parser = argparse.ArgumentParser(prog='gack', description='gack - Git stack utilities', usage='gack <cmmand> [<args>]')
        parser.add_argument('command', help='Subcommand to run')

        if len(argv) == 0:
            parser.print_help()
            exit(1)

        args = parser.parse_args(argv[0:1])
        command = args.command
        if not hasattr(self, command):
            print('Unrecongized command: {}'.format(command))
            parser.print_help()
            exit(1)
        else:
            return command, getattr(self, command)(argv[1:])

    def init(self, argv):
        parser = argparse.ArgumentParser(description='Initialize a gack repo')
        parser.add_argument('stack_root', help='Ref that acts as the bottom of the stack, probably master')
        return parser.parse_args(argv)

    def show(self, argv):
        parser = argparse.ArgumentParser(description='Show gack stack')
        return parser.parse_args(argv)

    def deinit(self, argv):
        parser = argparse.ArgumentParser(description='De-initialize a gack repo')
        return parser.parse_args(argv)

    def push(self, argv):
        parser = argparse.ArgumentParser(description='Push a patch in gack')
        parser.add_argument('--branch', help='If provided, push the branch into gack')
        parser.add_argument('--new', help='If provided, crease and push a new branch into gack')
        return parser.parse_args(argv)

    def pop(self, argv):
        parser = argparse.ArgumentParser(description='Pop a patch in gack')
        return parser.parse_args(argv)


def main(argv):
    parser = ArgParser()
    command, args = parser.parse_args(argv)

    repo = GackRepo()

    if command == 'init':
        if not repo.is_initialized:
            repo.InitializeRepo(args.stack_root)
        else:
            print('This repo is already initialized!')

    else:
        if not repo.is_initialized:
            print('This repo is not a gack repo, run `gack init` to initialize it')
        elif command == 'show':
            repo.PrintStack()
        elif command == 'deinit':
            repo.Deinitialize()
        elif command == 'push':
            repo.Push(branch=args.branch, new=args.new)
        elif command == 'pop':
            repo.Pop()
        else:
            raise Exception('Unknown command!')

if __name__ == '__main__':
    main(sys.argv[1:])
