#!/usr/bin/env python3

from git import Repo
import os
import re
import subprocess

'''
Gack's view of a git repo.
A Gack is a stack of git branches/refs.
For consistency, I'm borrowing from Mercurial Queue (MQ) terminology to call them a stack of patches.
You can push and pop patches in the stack.
'''
class GackRepo:
    GACK_DIR = os.path.join('.git', 'gack')
    STACK_PATH = os.path.join(GACK_DIR, 'stack')

    def __init__(self):
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
    def stack(self):
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
        for i in range(len(self.stack)):
            if self.stack[i] == patch_name:
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
            self.stack.pop(patch_index)
            self._update_stack_file()

            if delete:
                self._repo.delete_head(branch, force=True)

    def pop(self, all=False):
        current_patch_index = self._find_current_patch_index()
        if current_patch_index < 0:
            print('Cannot pop: current branch not tracked in gack!')
        elif current_patch_index == 0:
            print('Cannot pop: already at bottom of stack!')
        elif all:
            self._check_out(self.stack[0])
        else:
            self._check_out(self.stack[current_patch_index - 1])

    def push_one(self):
        current_patch_index = self._find_current_patch_index()
        if current_patch_index < 0:
            print('Cannot push: current branch not tracked in gack')
        elif current_patch_index == len(self.stack) -1:
            print('Cannot push: no more patches in gack!')
        else:
            base_patch = self.current_patch
            patch = self.stack[current_patch_index + 1]
            self._check_out(patch)
            self._rebase(base_patch)

    def push_existing_branch(self, branch_name):
        current_patch_index = self._find_current_patch_index()
        next_patch_index = self._find_patch_index(branch_name)
        if current_patch_index < 0:
            print('Cannot push: current branch not tracked in gack')
        elif next_patch_index >= 0:
            print('Cannot push {}: already in gack!'.format(branch_name))
        else:
            base_patch = self.current_patch
            self.stack.insert(current_patch_index + 1, branch_name)
            self._update_stack_file()
            self._check_out(branch_name)
            self._rebase(base_patch)

    def push_new_branch(self, branch_name):
        current_patch_index = self._find_current_patch_index()
        next_patch_index = self._find_patch_index(branch_name)
        if current_patch_index < 0:
            print('Cannot push: current branch not tracked in gack')
        else:
            self._repo.create_head(branch_name, commit=self.current_patch)
            self.stack.insert(current_patch_index + 1, branch_name)
            self._update_stack_file()
            self._check_out(branch_name)

    def _update_stack_file(self):
        if not os.path.exists(self._path(GackRepo.STACK_PATH)):
            raise Exception('Stack file does not exist!')
        with open(GackRepo.STACK_PATH, 'w') as f:
            for patch in self.stack:
                f.write('{}\n'.format(patch))

    def _find_branch(self, branch_name):
        for branch in self._repo.branches:
            if str(branch) == branch_name:
                return branch

    def _check_out(self, branch):
        self._find_branch(branch).checkout()

    def _rebase(self, branch):
        self._repo.git.rebase(branch)

    def _print_special(self, color, some_string):
        END = '\033[0m'
        print(color + some_string + END)

    def print_stack(self):
        BOLD = '\033[47m'
        GREY = '\033[30m'

        current_patch_found = False
        for patch in self.stack:
            if patch == self.current_patch:
                self._print_special(BOLD, patch)
                current_patch_found = True
            elif current_patch_found:
                self._print_special(GREY, patch)
            else:
                print(patch)

    def _get_differntial_revision_in_patch(self, patch_index):
        prev_patch_commit = None
        if patch_index > 0:
            prev_patch_commit = self._repo.commit(rev=self.stack[patch_index - 1])

        curr_commit = self._repo.commit(rev=self.stack[patch_index])
        while curr_commit is not None:
            if prev_patch_commit is not None and curr_commit.name_rev == prev_patch_commit.name_rev:
                # got to the last patch on the stack
                break

            matches = re.search(r'Differential Revision:\s+[a-z]+://[^\s]+/(D[0-9]+)', curr_commit.message)
            if matches is not None:
                return matches.group(1)

            if len(curr_commit.parents) == 0:
                # No more parents
                break
            curr_commit = curr_commit.parents[0]
        return None

    def _add_depends_on_if_appropriate(self):
        current_patch_index = self._find_current_patch_index()
        if current_patch_index < 1:
            return

        parent_diff = self._get_differntial_revision_in_patch(current_patch_index - 1)
        if parent_diff is None:
            return

        curr_commit = self._repo.commit(rev=self.stack[current_patch_index])
        prev_commit = self._repo.commit(rev=self.stack[current_patch_index - 1])

        while curr_commit is not None:
            if curr_commit.name_rev == prev_commit.name_rev:
                # got to the last patch on the stack
                break

            matches = re.search(r'Depends on D[0-9]+', curr_commit.message)
            if matches is not None:
                # already has dependency
                return

            if len(curr_commit.parents) == 0:
                # No more parents, this shouldn't happen
                raise Exception('Unexpected state: Parent revision in gack is not a parent of current revision!')
            curr_commit = curr_commit.parents[0]
        
        # if we get here, we did not find a dependency already marked
        curr_commit_message = self._repo.commit(rev=self.stack[current_patch_index]).message
        self._repo.git.commit('--amend', '-m', '{}\n\nDepends on {}'.format(curr_commit_message, parent_diff))

    def _shell_out(self, command_args):
        print('> {}'.format(' '.join(command_args))
        subprocess.run(command_args, check=True)

    def arc_diff(self):
        current_patch_index = self._find_current_patch_index()
        if current_patch_index < 0:
            print('Cannot diff: current branch not tracked in gack')
        elif current_patch_index == 0:
            print('Cannot diff bottom of stack! gack push first')
        else:
            prev_patch = self.stack[current_patch_index - 1]
            arc_diff_command = ['arc', 'diff']

            diff_to_update = self._get_differntial_revision_in_patch(current_patch_index)
            if diff_to_update is None:
                arc_diff_command.extend(['--create'])
                parent_diff = self._get_differntial_revision_in_patch(current_patch_index - 1)
                if parent_diff is not None:
                    self._add_depends_on_if_appropriate()
            else:
                arc_diff_command.extend(['--update', diff_to_update])
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
            self.stack.pop(current_patch_index)
            self._update_stack_file()
