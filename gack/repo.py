#!/usr/bin/env python3

from git import Repo
import os

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

    def InitializeRepo(self, stack_root):
        if self.is_initialized:
            raise Exception('This repo is already initialized!')
        if not os.path.exists(self._path(GackRepo.GACK_DIR)):
            os.mkdir(GackRepo.GACK_DIR)

        if not os.path.exists(self._path(GackRepo.STACK_PATH)):
            with open(GackRepo.STACK_PATH, 'w') as f:
                f.write('{}\n'.format(stack_root))

    def _path(self, path):
        return os.path.join(self._repo.working_tree_dir, path)

    def Deinitialize(self):
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

    def _FindPatchIndex(self, patch_name):
        for i in range(len(self.stack)):
            if self.stack[i] == patch_name:
                return i
        return -1

    def _FindCurrentPatchIndex(self):
        return self._FindPatchIndex(self.current_patch)

    def Pop(self, all=False):
        current_patch_index = self._FindCurrentPatchIndex()
        if current_patch_index < 0:
            print('Cannot pop: current branch not tracked in gack!')
        elif current_patch_index == 0:
            print('Cannot pop: already at bottom of stack!')
        elif all:
            self._CheckOut(self.stack[0])
        else:
            self._CheckOut(self.stack[current_patch_index - 1])

    def Push(self, branch=None, newBranch=None):
        if branch is not None:
            if newBranch is not None:
                raise Exception('Cannot create a branch and push a branch in one go')
            self._PushBranch(branch)
        elif newBranch is not None:
            self._PushNewBranch(newBranch)
        else:
            self._PushOne()

    def _PushOne(self):
        current_patch_index = self._FindCurrentPatchIndex()
        if current_patch_index < 0:
            print('Cannot push: current branch not tracked in gack')
        elif current_patch_index == len(self.stack) -1:
            print('Cannot push: no more patches in gack!')
        else:
            patch = self.stack[current_patch_index + 1]
            self._CheckOut(patch)
            self._Rebase(self.current_patch)

    def _PushBranch(self, branch_name):
        current_patch_index = self._FindCurrentPatchIndex()
        next_patch_index = self._FindPatchIndex(branch_name)
        if current_patch_index < 0:
            print('Cannot push: current branch not tracked in gack')
        elif next_patch_index >= 0:
            print('Cannot push {}: already in gack!'.format(branch_name))
        else:
            self.stack.insert(current_patch_index + 1, branch_name)
            self._UpdateStackFile()
            self._CheckOut(branch_name)
            self._Rebase(self.current_patch)

    def _PushNewBranch(self, branch_name):
        current_patch_index = self._FindCurrentPatchIndex()
        next_patch_index = self._FindPatchIndex(branch_name)
        if current_patch_index < 0:
            print('Cannot push: current branch not tracked in gack')
        else:
            self._repo.create_head(branch_name, commit=self.current_patch)
            self.stack.insert(current_patch_index + 1, branch_name)
            self._UpdateStackFile()
            self._CheckOut(branch_name)

    def _UpdateStackFile(self):
        if not os.path.exists(self._path(GackRepo.STACK_PATH)):
            raise Exception('Stack file does not exist!')
        with open(GackRepo.STACK_PATH, 'w') as f:
            for patch in self.stack:
                f.write('{}\n'.format(patch))

    def _FindBranch(self, branch_name):
        for branch in self._repo.branches:
            if str(branch) == branch_name:
                return branch

    def _CheckOut(self, branch):
        self._FindBranch(branch).checkout()

    def _Rebase(self, branch):
        self._repo.git.rebase(branch)

    def _PrintSpecial(self, color, some_string):
        END = '\033[0m'
        print(color + some_string + END)

    def PrintStack(self):
        BOLD = '\033[47m'
        GREY = '\033[30m'

        current_patch_found = False
        for patch in self.stack:
            if patch == self.current_patch:
                self._PrintSpecial(BOLD, patch)
                current_patch_found = True
            elif current_patch_found:
                self._PrintSpecial(GREY, patch)
            else:
                print(patch)

    def ArcDiff(self, diffToUpdate=None):
        current_patch_index = self._FindCurrentPatchIndex()
        if current_patch_index < 0:
            print('Cannot diff: current branch not tracked in gack')
        elif current_patch_index == 0:
            print('Cannot diff bottom of stack! gack push first')
        else:
            prevPatch = self.stack[current_patch_index - 1]
            arcDiffCommand = ['arc', 'diff']
            if diffToUpdate is not None:
                arcDiffCommand.extend(['--update', diffToUpdate])
            arcDiffCommand.extend([prevPatch])
            subprocess.run(arcDiffCommand, check=True)

    def ArcLand(self):
        current_patch_index = self._FindCurrentPatchIndex()
        if current_patch_index < 0:
            print('Cannot land: current branch not tracked in gack')
        elif current_patch_index != 1:
            print('Can only land first patch in stack!')
        else:
            subprocess.run(['arc', 'land'], check=True)
            self.stack.pop(current_patch_index)
            self._UpdateStackFile()
