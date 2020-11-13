#!/usr/bin/env python3

from git import Repo
import os
import re
import subprocess
import sys

class Color:
    END = '\033[0m'
    BOLD = '\033[47m'
    GREY = '\033[30m'
    RED = '\033[31m'

MAX_COMMITS = 15

'''
Gack's view of a git repo.
A Gack is a stack of git branches/refs.
For consistency, I'm borrowing from Mercurial Queue (MQ) terminology to call them a stack of patches.
You can push and pop patches in the stack.
'''
class GackRepo:
    GACK_DIR = os.path.join('.git', 'gack')
    STACK_PATH = os.path.join(GACK_DIR, 'stack')
    DIFF_REVISION_RE = r'Differential Revision:\s+([a-z]+://[^\s]+/(D[0-9]+))'

    def __init__(self):
        if not os.path.exists(os.path.join(os.getcwd(), '.git')):
            raise Exception('Not a git repo!')
        self._repo = Repo.init(os.getcwd())
        self._stack_cache = None

    @property
    def is_initialized(self):
        return os.path.exists(self._path(GackRepo.STACK_PATH))

    def initialize_repo(self, stack_root):
        if self.is_initialized:
            raise Exception('This repo is already initialized!')
        if not os.path.exists(self._path(GackRepo.GACK_DIR)):
            os.mkdir(GackRepo.GACK_DIR)

        if not os.path.exists(self._path(GackRepo.STACK_PATH)):
            with open(GackRepo.STACK_PATH, 'w') as f:
                f.write('{}\n'.format(stack_root))

    def _path(self, path):
        return os.path.join(self._repo.working_tree_dir, path)

    def deinitialize(self):
        if not self.is_initialized:
            raise Exception('This repo was never initialized!')
        os.remove(self._path(GackRepo.STACK_PATH))


    @property
    def _stack(self):
        if not self._stack_cache:
            self._stack_cache = []
            with open(self._path(self.STACK_PATH)) as f:
                while True:
                    line = f.readline()
                    if not line:
                        break;
                    self._stack_cache.append(line.strip())
        return self._stack_cache;
    
    @property
    def current_patch(self):
        return str(self._repo.active_branch)

    def _find_patch_index(self, patch_name):
        for i in range(len(self._stack)):
            if self._stack[i] == patch_name:
                return i
        return -1

    def _find_current_patch_index(self):
        return self._find_patch_index(self.current_patch)

    def untrack(self, branch, delete=False):
        patch_index = self._find_patch_index(branch)
        current_patch_index = self._find_current_patch_index()
        if patch_index < 0:
            print('Cannot untrack: no branch named {}'.format(branch))
        elif current_patch_index > patch_index:
            print('Cannot untrack: branch {} is currently pushed'.format(branch))
        else:
            self._stack.pop(patch_index)
            self._update_stack_file()

            if delete:
                self._repo.delete_head(branch, force=True)

    def diff(self):
        current_patch_index = self._find_current_patch_index()
        if current_patch_index < 0:
            print('Cannot diff: current branch not tracked in gack!')
        elif current_patch_index == 0:
            print('Cannot diff: already at bottom of stack!')
        else:
            self._shell_out(['git', 'diff', self._stack[current_patch_index - 1]], check=False)

    def log(self):
        current_patch_index = self._find_current_patch_index()
        if current_patch_index < 0:
            print('Cannot log: current branch not tracked in gack!')
        elif current_patch_index == 0:
            print('Cannot log: already at bottom of stack!')
        else:
            self._shell_out(
                [
                    'git',
                    'log',
                    '--first-parent',
                    '--no-merges',
                    '{}..'.format(self._stack[current_patch_index - 1])
                ],
                check=False)

    def pop(self, all=False):
        current_patch_index = self._find_current_patch_index()
        if current_patch_index < 0:
            print('Cannot pop: current branch not tracked in gack!')
        elif current_patch_index == 0:
            print('Cannot pop: already at bottom of stack!')
        elif all:
            self._check_out(self._stack[0])
        else:
            self._check_out(self._stack[current_patch_index - 1])

    def push_one(self, rebase):
        current_patch_index = self._find_current_patch_index()
        if current_patch_index < 0:
            print('Cannot push: current branch not tracked in gack')
        elif current_patch_index == len(self._stack) -1:
            print('Cannot push: no more patches in gack!')
        else:
            base_patch = self.current_patch
            patch = self._stack[current_patch_index + 1]
            self._check_out(patch)
            if rebase:
                self._rebase(base_patch)

    def push_existing_branch(self, branch_name, rebase):
        current_patch_index = self._find_current_patch_index()
        next_patch_index = self._find_patch_index(branch_name)
        if current_patch_index < 0:
            print('Cannot push: current branch not tracked in gack')
        elif next_patch_index >= 0:
            print('Cannot push {}: already in gack!'.format(branch_name))
        else:
            base_patch = self.current_patch
            self._stack.insert(current_patch_index + 1, branch_name)
            self._update_stack_file()
            self._check_out(branch_name)
            if rebase:
                self._rebase(base_patch)

    def push_new_branch(self, branch_name):
        current_patch_index = self._find_current_patch_index()
        next_patch_index = self._find_patch_index(branch_name)
        if current_patch_index < 0:
            print('Cannot push: current branch not tracked in gack')
        else:
            self._repo.create_head(branch_name, commit=self.current_patch)
            self._stack.insert(current_patch_index + 1, branch_name)
            self._update_stack_file()
            self._check_out(branch_name)

    def _update_stack_file(self):
        if not os.path.exists(self._path(GackRepo.STACK_PATH)):
            raise Exception('Stack file does not exist!')
        with open(GackRepo.STACK_PATH, 'w') as f:
            for patch in self._stack:
                f.write('{}\n'.format(patch))

    def _find_branch(self, branch_name):
        for branch in self._repo.branches:
            if str(branch) == branch_name:
                return branch

    def _check_out(self, branch):
        self._find_branch(branch).checkout()

    def _rebase(self, branch):
        self._repo.git.rebase('--fork-point', branch)

    def _format_color(self, color, some_string):
        return color + some_string + Color.END

    def print_stack(self, show_phab):
        current_patch_found = False
        for i in range(len(self._stack)):
            patch = self._stack[i]

            output_strings = []

            if patch == self.current_patch:
                patch_string = self._format_color(Color.BOLD, patch)
                current_patch_found = True
            elif current_patch_found:
                patch_string = self._format_color(Color.GREY, patch)
            else:
                patch_string = patch
            output_strings.append(patch_string)

            if show_phab and i > 0:
                diff_status_string = None
                root_commit = self._repo.commit(rev=self._stack[0])

                for commit in self._commits_in_reverse(self._stack[i], self._stack[i - 1]):
                    if diff_status_string is None:
                        # haven't found the diff rev string yet
                        matches = re.search(GackRepo.DIFF_REVISION_RE, commit.message)
                        if matches is not None:
                            diff_status_string = self._format_color(Color.GREY, matches.group(1))
                            # only do rebase check on patches > 1
                            if i <= 1:
                                break
                    elif i > 1:
                        if len(commit.parents) == 0:
                            # Expecting to have parents, branch detached somehow?
                            diff_status_string = self._format_color(Color.RED, 'Needs rebase!')
                            break

                        # already found a diff rev, do a rebase check if we're on patch > 1
                        parent = commit.parents[0]
                        if parent is not None and parent.name_rev == root_commit.name_rev:
                            # current patch is rooted on patch 0, we need to rebase
                            diff_status_string = self._format_color(Color.RED, 'Needs rebase!')
                            break

                if diff_status_string is not None:
                    output_strings.append(diff_status_string)

            print(' '.join(output_strings))

    def _commits_in_reverse(self, current_patch, parent_patch):
        current_commit = self._repo.commit(rev=current_patch)
        parent_commit = self._repo.commit(rev=parent_patch)
        # this can happen if one of the patches needs rebasing
        root_commit = self._repo.commit(rev=self._stack[0])

        commits_yielded = 0
        while current_commit is not None and parent_commit is not None and \
                root_commit.name_rev != current_commit.name_rev and \
                parent_commit.name_rev != current_commit.name_rev:
            yield current_commit

            commits_yielded += 1
            if commits_yielded > MAX_COMMITS or len(current_commit.parents) == 0:
                current_commit = None
            else:
                current_commit = current_commit.parents[0]

    def _get_differential_revision_in_patch(self, patch_index):
        prev_patch = None
        if patch_index > 0:
            prev_patch = self._stack[patch_index - 1]

        for commit in self._commits_in_reverse(self._stack[patch_index], prev_patch):
            matches = re.search(GackRepo.DIFF_REVISION_RE, commit.message)
            if matches is not None:
                return matches.group(2)
        return None

    def _add_depends_on_if_appropriate(self):
        current_patch_index = self._find_current_patch_index()
        if current_patch_index < 1:
            return

        parent_diff = self._get_differential_revision_in_patch(current_patch_index - 1)
        if parent_diff is None:
            return

        for commit in self._commits_in_reverse(
                self._stack[current_patch_index],
                self._stack[current_patch_index - 1]):
            matches = re.search(r'Depends on D[0-9]+', commit.message)
            if matches is not None:
                # already has dependency
                return

        # if we get here, we did not find a dependency already marked
        curr_commit_message = self._repo.commit(rev=self._stack[current_patch_index]).message
        self._repo.git.commit('--amend', '-m', '{}\n\nDepends on {}'.format(curr_commit_message, parent_diff))

    def _shell_out(self, command_args, check=True):
        print('> {}'.format(' '.join(command_args)))
        try:
            subprocess.check_call(command_args)
        except subprocess.CalledProcessError as e:
            print(str(e), file=sys.stderr)
            sys.exit(e.returncode)

    def arc_diff(self, edit_diff):
        current_patch_index = self._find_current_patch_index()
        if current_patch_index < 0:
            print('Cannot diff: current branch not tracked in gack')
        elif current_patch_index == 0:
            print('Cannot diff bottom of stack! gack push first')
        else:
            prev_patch = self._stack[current_patch_index - 1]
            arc_diff_command = ['arc', 'diff']

            if current_patch_index > 1:
                # only calculate dependent diff is parent patch is not root patch
                diff_to_update = self._get_differential_revision_in_patch(current_patch_index)
                if diff_to_update is None:
                    arc_diff_command.extend(['--create'])
                    parent_diff = self._get_differential_revision_in_patch(current_patch_index - 1)
                    if parent_diff is not None:
                        self._add_depends_on_if_appropriate()
                else:
                    arc_diff_command.extend(['--update', diff_to_update])

            if edit_diff:
                arc_diff_command.extend(['--edit'])

            # Start diff from previous patch
            arc_diff_command.extend([prev_patch])

            self._shell_out(arc_diff_command)

    def arc_land(self):
        current_patch_index = self._find_current_patch_index()
        if current_patch_index < 0:
            print('Cannot land: current branch not tracked in gack')
        elif current_patch_index != 1:
            print('Can only land first patch in stack!')
        else:
            self._shell_out(['arc', 'land'])
            self._stack.pop(current_patch_index)
            self._update_stack_file()

