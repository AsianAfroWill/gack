#!/usr/bin/env python3

import argparse
import sys
import textwrap

from gack import GackRepo

PROG='gack'
HELP_STRINGS = {
    'init': 'Initialize a git repo for gack',
    'show': 'Show gack stack',
    'deinit': 'Deinitialize a gack repo',
    'push': 'Push a patch in gack',
    'pop': 'Pop a patch in gack',
    'untrack': 'Stop tracking a patch in gack',
    'diff': 'Show diff since previous patch in gack',
    'log': 'Show logs since previous patch in gack',
    'arcdiff': 'Upload current patch as a diff through arc',
    'arcland': 'Land current patch through arc',
}

class ArgParser:

    def __init__(self):
        pass

    def parse_args(self, argv):
        parser = argparse.ArgumentParser(
                prog=PROG,
                formatter_class=argparse.RawDescriptionHelpFormatter,
                description=textwrap.dedent('''
                gack - Git Stacking utilities

                Repo Management:
                  init      {init}
                  deinit    {deinit}

                Stack Operations:
                  show      {show}
                  push      {push}
                  pop       {pop}
                  diff      {diff} 
                  log       {log} 
                  untrack   {untrack}

                Arcanist/Phabricator Integrations:
                  arcdiff   {arcdiff}
                  arcland   {arcland}

                Run '%(prog)s <command> --help' for more information on a command.
                '''.format(**HELP_STRINGS)),
                usage='%(prog)s <command> [<args>]')
        parser.add_argument('command', help='Command to run')

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
        parser = argparse.ArgumentParser(
                prog=PROG,
                usage='%(prog)s init',
                description=HELP_STRINGS['init'])
        parser.add_argument('stack_root', default='master', help='Ref that acts as the bottom of the stack, defaults to master')
        return parser.parse_args(argv)

    def show(self, argv):
        parser = argparse.ArgumentParser(
                prog=PROG,
                usage='%(prog)s show',
                description=HELP_STRINGS['show'])
        return parser.parse_args(argv)

    def deinit(self, argv):
        parser = argparse.ArgumentParser(
                prog=PROG,
                usage='%(prog)s deinit',
                description=HELP_STRINGS['deinit'])
        return parser.parse_args(argv)

    def push(self, argv):
        parser = argparse.ArgumentParser(
                prog=PROG,
                usage='%(prog)s push',
                description=HELP_STRINGS['push'])
        group = parser.add_mutually_exclusive_group()
        group.add_argument('--branch', help='If provided, push the branch into gack')
        group.add_argument('--new', help='If provided, crease and push a new branch into gack')
        return parser.parse_args(argv)

    def pop(self, argv):
        parser = argparse.ArgumentParser(
                prog=PROG,
                usage='%(prog)s pop',
                description=HELP_STRINGS['pop'])
        parser.add_argument('--all', action='store_true', help='Pop all branches')
        return parser.parse_args(argv)

    def diff(self, argv):
        parser = argparse.ArgumentParser(
                prog=PROG,
                usage='%(prog)s diff',
                description=HELP_STRINGS['diff'])
        return parser.parse_args(argv)

    def log(self, argv):
        parser = argparse.ArgumentParser(
                prog=PROG,
                usage='%(prog)s log',
                description=HELP_STRINGS['log'])
        return parser.parse_args(argv)

    def untrack(self, argv):
        parser = argparse.ArgumentParser(
                prog=PROG,
                usage='%(prog)s untrack',
                description=HELP_STRINGS['untrack'])
        parser.add_argument('branch', help='Stop tracking the branch in gack; it remains tracked by git unless --delete is specified')
        parser.add_argument('--delete', action='store_true', help='Also forcibly delete the branch')
        return parser.parse_args(argv)

    def arcdiff(self, argv):
        parser = argparse.ArgumentParser(
                prog=PROG,
                usage='%(prog)s arcdiff',
                description=HELP_STRINGS['arcdiff'])
        return parser.parse_args(argv)

    def arcland(self, argv):
        parser = argparse.ArgumentParser(
                prog=PROG,
                usage='%(prog)s arcland',
                description=HELP_STRINGS['arcland'])
        return parser.parse_args(argv)

    def log(self, argv):
        parser = argparse.ArgumentParser(
                prog=PROG,
                usage='%(prog)s log',
                description='Print some logs')
        return parser.parse_args(argv)

    def debug(self, argv):
        parser = argparse.ArgumentParser(
                prog=PROG,
                usage='%(prog)s debug',
                description='Do some debugging')
        return parser.parse_args(argv)

def main(argv):
    parser = ArgParser()
    command, args = parser.parse_args(argv)

    repo = GackRepo()

    if command == 'init':
        if not repo.is_initialized:
            repo.initialize_repo(args.stack_root)
        else:
            print('This repo is already initialized!')

    else:
        if not repo.is_initialized:
            print('This repo is not a gack repo, run `gack init` to initialize it')
        elif command == 'show': repo.print_stack()
        elif command == 'deinit':
            response = input('gack will stop tracking your stack, are you sure? (y/N)')
            if response == 'y' or response == 'Y':
                repo.deinitialize()
        elif command == 'push':
            if args.branch is not None:
                repo.push_existing_branch(args.branch)
            elif args.new is not None:
                repo.push_new_branch(args.new)
            else:
                repo.push_one()
        elif command == 'pop':
            repo.pop(all=args.all)
        elif command == 'diff':
            repo.diff()
        elif command == 'log':
            repo.log()
        elif command == 'untrack':
            repo.untrack(branch=args.branch, delete=args.delete)
        elif command == 'arcdiff':
            repo.arc_diff()
        elif command == 'arcland':
            repo.arc_land()
        elif command == 'debug':
            repo._debug()
        else:
            raise Exception('Unknown command!')

if __name__ == '__main__':
    main(sys.argv[1:])
