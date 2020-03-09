#!/usr/bin/env python3

from git import Repo
import os
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

    def push(self, branch=None, new_branch=None):
        if branch is not None:
            if new_branch is not None:
                raise Exception('Cannot create a branch and push a branch in one go')
            self._push_branch(branch)
        elif new_branch is not None:
            self._push_new_branch(new_branch)
        else:
            self._push_one()

    def _push_one(self):
        current_patch_index = self._find_current_patch_index()
        if current_patch_index < 0:
            print('Cannot push: current branch not tracked in gack')
        elif current_patch_index == len(self.stack) -1:
            print('Cannot push: no more patches in gack!')
        else:
            base_patch = self.current_patch
            patch = self.stack[current_patch_index + 1]
            self._CheckOut(patch)
            self._Rebase(base_patch)

    def _push_branch(self, branch_name):
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

    def _push_new_branch(self, branch_name):
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

    def arc_diff(self, diff_to_update=None):
        current_patch_index = self._find_current_patch_index()
        if current_patch_index < 0:
            print('Cannot diff: current branch not tracked in gack')
        elif current_patch_index == 0:
            print('Cannot diff bottom of stack! gack push first')
        else:
            prev_patch = self.stack[current_patch_index - 1]
            arc_diff_command = ['arc', 'diff']
            if diff_to_update is not None:
                arc_diff_command.extend(['--update', diff_to_update])
            arc_diff_command.extend([prev_patch])
            subprocess.run(arc_diff_command, check=True)

    def arc_land(self):
        current_patch_index = self._find_current_patch_index()
        if current_patch_index < 0:
            print('Cannot land: current branch not tracked in gack')
        elif current_patch_index != 1:
            print('Can only land first patch in stack!')
        else:
            subprocess.run(['arc', 'land'], check=True)
            self.stack.pop(current_patch_index)
            self._update_stack_file()
