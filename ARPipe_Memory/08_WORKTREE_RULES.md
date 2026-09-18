# ARPipe — Worktree Rules

> ONE SESSION = ONE WORKTREE = ONE TASK.

Before work record: task, model, starting SHA, worktree, expected output, constraints.

During work:
- never touch another active worktree
- forensic trees remain read-only
- stop on unexpected file changes

After work record:
- tests
- changed files
- commit SHA
- artifact/report paths
- hashes when important
- what was proven
- what was not proven
- verdict
- next dependency
