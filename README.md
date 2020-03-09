# gack - Git Stack Manager

gack helps a git user use git like Mercurial Queues: gack provide the ability to push/pop and create patches and automatically rebases them.

Currently supported commands are:

- init
- deinit
- push
- pop
- show

Arc utilities:

- diff
- land

# Quick Getting-Started Guide

## Installation

To install, run

```
python3 setup.py install
```

To run:

```
python3 -m gack
```

## Usage

First initialize the repo, with gack rooted on master:

```
gack init master
```

To create a new branch and push it in gack:

```
gack push --new new-branch-name
```

To track and push an existing branch in gack:

```
gack push --branch existing-branch-name
```

To show current gack status:

```
gack show
```

To go up the patch stack:

```
gack pop
```

gack shells out to arc to use Arcanist to work with Phabricator. It always deals with the patch in relation to the previous patch on the gack.

To upload a diff through arc:

```
gack diff
```

To land a diff through arc:

```
gack land
```

# Terminologies

Gack = Git stACK.

Patch = A branch tracked in gack; a gack is a stack of patches.

# How it works, and caveats

gack tracks the stack in `.git/gack/stack`, and compares current git branch to others in the stack to understand the relationship.

Generally, gack tracks branches linearly to simplify rebase operations. Starting from master, let's create a new patch, `alpha`:

In git's view, the repo looks like:

```
M1 - M2  <- master
     ^
     alpha (HEAD)
```

When you commit a change to `alpha`, git tracks it as you would expect

```
M1 - M2  <- master
      \
       A1  <- alpha (HEAD)
```

At this point, `gack pop` is simply `git checkout master`:

```
M1 - M2  <- master (HEAD)
      \
       A1  <- alpha
```

Then, `gack push` is `git checkout alpha`:

```
M1 - M2  <- master
      \
       A1  <- alpha (HEAD)
```

If we `gack push --new beta`:

```
M1 - M2   master
      \
       A1  <- alpha
        \
         B1  <- beta (HEAD)
```

Now gack is tracking 2 patches on top of master.

gack here enables you to do some work on the branches as dependencies. For example, if we need to go back to `alpha` to fix a bug, we can `gack pop` and commmit the change (`A2`):

```
M1 - M2   master
      \
       A1 - A2  <- alpha (HEAD)
        \
         B1  <- beta
```

When you `gack push`, because `beta` depends on `alpha`, gack rebases beta onto alpha for you:

```
M1 - M2   master
      \
       A1 - A2  <- alpha
             \
              B1  <- beta (HEAD)
```

The biggest caveat in working with a gack-style workflow is that it is difficult to move patches up and down the stack, and deleting existing revs can cause unintuitive side-effects, because of the way git tracks branches.

In the above example, if we want to reorder the patches to `master`, `beta` then `alpha`, it involves a few non-trivial operations and is currently not supported by gack.

Also in the above example, if we were to drop A2 from `alpha` through an interactive rebase, we will actually end up with something like this:

```
M1 - M2   master
      \
       A1  <- alpha
         \
          A2 - B1  <- beta
```

So generally when using gack at this point of development, it is most intuitive to keep a forward workflow and never edit the branches directly to keep things simple.
