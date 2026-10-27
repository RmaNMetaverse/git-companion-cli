"""Declarative, shell-free command catalog, grouped around user intent."""

from dataclasses import dataclass

from .guidance import GUIDANCE


@dataclass(frozen=True)
class Field:
    name: str
    label: str
    default: str = ""
    optional: bool = False
    literal: bool = False


@dataclass(frozen=True)
class Command:
    id: str
    category: str
    title: str
    description: str
    args: tuple[str, ...]
    fields: tuple[Field, ...] = ()
    risk: str = ""
    repo: bool = True

    @property
    def hint(self) -> str:
        return GUIDANCE[self.id].hint

    @property
    def examples(self):
        return GUIDANCE[self.id].examples

    @property
    def lfs(self) -> bool:
        return self.args[0] == "lfs"

    @property
    def command_line(self) -> str:
        return "git " + " ".join(self.args)

    @property
    def completion(self) -> str:
        """Complete the fixed command, leaving personal values to the review form."""
        fixed = []
        for arg in self.args:
            if arg.startswith("{"):
                break
            fixed.append(arg)
        return "git " + " ".join(fixed)

    def build(self, values: dict[str, str] | None = None) -> list[str]:
        values = values or {}
        resolved = {}
        for field in self.fields:
            value = values.get(field.name, field.default).strip()
            if not value and not field.optional:
                raise ValueError(f"{field.label} is required.")
            if "\x00" in value or "\n" in value or "\r" in value:
                raise ValueError(f"{field.label} must be a single line.")
            if value.startswith("-") and not field.literal:
                raise ValueError(f"{field.label} cannot start with '-'.")
            resolved[field.name] = value
        result = ["git"]
        for arg in self.args:
            if arg.startswith("{") and arg.endswith("}"):
                value = resolved[arg[1:-1]]
                if value:
                    result.append(value)
            else:
                result.append(arg)
        return result


CATEGORIES = {
    "recommended": ("01", "For you", "Context-aware next steps"),
    "inspect": ("02", "Look around", "Status, history & differences"),
    "changes": ("03", "Save your work", "Stage, commit & stash"),
    "branches": ("04", "Try ideas", "Switch, merge & rebase"),
    "sync": ("05", "Share & sync", "Fetch, pull, push & remotes"),
    "lfs": ("06", "Large files", "Track, transfer & verify"),
    "cleanup": ("07", "Reclaim space", "Preview, prune & clean"),
    "recover": ("08", "Recover", "Reflog, restore & undo"),
    "setup": ("09", "Set up", "Repositories & identity"),
}


def f(name, label, default="", optional=False, literal=False):
    return Field(name, label, default, optional, literal)


COMMANDS: list[Command] = []


def c(id, category, title, description, args, fields=(), risk="", repo=True):
    COMMANDS.append(Command(id, category, title, description, tuple(args.split()), tuple(fields), risk, repo))


c(
    "status",
    "inspect",
    "Working tree status",
    "See staged, modified and untracked files.",
    "status --short --branch",
)
c(
    "graph",
    "inspect",
    "Commit constellation",
    "A graph of recent commits across all branches.",
    "log --graph --decorate --oneline --all -40",
)
c("diff", "inspect", "Unstaged differences", "Review changes before staging.", "diff --stat")
c("patch", "inspect", "Inspect the patch", "Read the full unstaged diff.", "diff --no-ext-diff")
c(
    "staged",
    "inspect",
    "Staged differences",
    "Review exactly what the next commit includes.",
    "diff --cached --no-ext-diff",
)
c(
    "show",
    "inspect",
    "Inspect a commit",
    "Show a commit and its patch.",
    "show --no-ext-diff {ref}",
    [f("ref", "Commit or reference", "HEAD")],
)
c(
    "blame",
    "inspect",
    "Who changed this?",
    "Annotate each line of a file with its author.",
    "blame -- {path}",
    [f("path", "File path", literal=True)],
)
c("tags", "inspect", "Browse tags", "List release tags, newest first.", "tag --list --sort=-version:refname")
c(
    "stage",
    "changes",
    "Stage a file or pattern",
    "Use '.' to stage changes under this directory.",
    "add -- {path}",
    [f("path", "Path or pattern", ".", literal=True)],
)
c(
    "stage-all",
    "changes",
    "Stage all changes",
    "Stage additions, edits and deletions throughout the repository.",
    "add --all",
)
c(
    "unstage",
    "changes",
    "Unstage a file",
    "Keep the working copy; remove the file from the next commit. Requires an existing commit.",
    "restore --staged -- {path}",
    [f("path", "Path or pattern", ".", literal=True)],
)
c(
    "commit",
    "changes",
    "Create a commit",
    "Save staged changes with a descriptive message.",
    "commit -m {message}",
    [f("message", "Commit message", literal=True)],
)
c(
    "amend",
    "changes",
    "Amend the last commit",
    "Replace the latest commit with staged changes and a new message.",
    "commit --amend -m {message}",
    [f("message", "Replacement message", literal=True)],
    "Rewrites the latest commit. Avoid amending commits already shared with others.",
)
c(
    "stash",
    "changes",
    "Park current changes",
    "Stash tracked and untracked changes to return to later.",
    "stash push --include-untracked -m {message}",
    [f("message", "Stash label", "Work in progress", literal=True)],
)
c("stash-list", "changes", "Browse stashes", "Find saved work before applying it.", "stash list")
c(
    "stash-apply",
    "changes",
    "Apply a stash",
    "Restore saved work while keeping the stash as a backup.",
    "stash apply {ref}",
    [f("ref", "Stash reference", "stash@{0}")],
)
c(
    "stash-drop",
    "changes",
    "Delete a stash",
    "Remove a saved stash entry.",
    "stash drop {ref}",
    [f("ref", "Stash reference", "stash@{0}")],
    "Permanently removes this stash reference. Apply or back up its changes first.",
)
c(
    "branches",
    "branches",
    "Branch overview",
    "See local and remote branches and their upstreams.",
    "branch --all --verbose --verbose",
)
c(
    "switch",
    "branches",
    "Switch branches",
    "Move to an existing branch.",
    "switch {branch}",
    [f("branch", "Branch")],
)
c(
    "new-branch",
    "branches",
    "Start a new branch",
    "Create a branch and switch to it.",
    "switch -c {branch}",
    [f("branch", "New branch name")],
)
c(
    "rename-branch",
    "branches",
    "Rename this branch",
    "Give the current branch a new name.",
    "branch -m {branch}",
    [f("branch", "New branch name")],
)
c(
    "delete-branch",
    "branches",
    "Delete a merged branch",
    "Delete a local branch only if Git considers it merged.",
    "branch -d {branch}",
    [f("branch", "Branch to delete")],
)
c(
    "merge",
    "branches",
    "Merge a branch",
    "Integrate another branch into the current one; uses a generated merge message.",
    "merge --no-edit {branch}",
    [f("branch", "Branch to merge")],
)
c(
    "merge-abort",
    "branches",
    "Abort a merge",
    "Return to the state before an in-progress merge.",
    "merge --abort",
    risk="Discards conflict-resolution edits made during this merge.",
)
c(
    "rebase",
    "branches",
    "Rebase onto a branch",
    "Replay your commits on another base.",
    "rebase {branch}",
    [f("branch", "New base", "main")],
    "Rewrites commits. Use on private branches and resolve any conflicts before continuing.",
)
c(
    "rebase-continue",
    "branches",
    "Continue a rebase",
    "Continue after fixing and staging conflicts.",
    "rebase --continue",
)
c(
    "rebase-abort",
    "branches",
    "Abort a rebase",
    "Restore the branch to its original state.",
    "rebase --abort",
    risk="Discards conflict-resolution edits from this rebase.",
)
c(
    "cherry-pick",
    "branches",
    "Pick a commit",
    "Apply an existing commit to the current branch.",
    "cherry-pick {ref}",
    [f("ref", "Commit hash")],
)
c("worktrees", "branches", "List worktrees", "Find linked checkouts of this repository.", "worktree list")
c(
    "fetch",
    "sync",
    "Fetch remote updates",
    "Download references from all remotes and remove stale remote references.",
    "fetch --all --prune",
)
c(
    "pull",
    "sync",
    "Pull safely",
    "Fast-forward only; refuses to create an unexpected merge commit.",
    "pull --ff-only",
)
c("push", "sync", "Push this branch", "Publish commits to the configured upstream.", "push")
c(
    "push-upstream",
    "sync",
    "Publish a new branch",
    "Push a branch and configure its upstream.",
    "push --set-upstream {remote} {branch}",
    [f("remote", "Remote", "origin"), f("branch", "Branch")],
)
c(
    "force-push",
    "sync",
    "Push rewritten history",
    "Force-with-lease refuses if the remote changed since your last fetch.",
    "push --force-with-lease",
    risk="Can replace shared history. Coordinate with collaborators before continuing.",
)
c("remotes", "sync", "Remote connections", "Show remote fetch and push addresses.", "remote -v")
c(
    "add-remote",
    "sync",
    "Connect a remote",
    "Add a named remote URL.",
    "remote add {name} {url}",
    [f("name", "Remote name", "origin"), f("url", "Remote URL")],
)
c(
    "tag",
    "sync",
    "Create a release tag",
    "Create an annotated tag at the current commit.",
    "tag -a {tag} -m {message}",
    [f("tag", "Tag name"), f("message", "Release message", literal=True)],
)
c(
    "push-tag",
    "sync",
    "Publish a tag",
    "Push one specific tag to a remote.",
    "push {remote} tag {tag}",
    [f("remote", "Remote", "origin"), f("tag", "Tag name")],
)
c("lfs-status", "lfs", "Large file status", "See LFS files awaiting commit or upload.", "lfs status")
c("lfs-files", "lfs", "Large file inventory", "List LFS-managed files with sizes.", "lfs ls-files --size")
c("lfs-patterns", "lfs", "Tracked file patterns", "List patterns registered for LFS tracking.", "lfs track")
c(
    "lfs-track",
    "lfs",
    "Track a file type",
    "Register a pattern such as *.psd, then stage and commit .gitattributes.",
    "lfs track {pattern}",
    [f("pattern", "File pattern", "*.psd")],
)
c(
    "lfs-untrack",
    "lfs",
    "Stop tracking a pattern",
    "Update .gitattributes; existing LFS history remains unchanged.",
    "lfs untrack {pattern}",
    [f("pattern", "File pattern", "*.psd")],
)
c(
    "lfs-pull",
    "lfs",
    "Download large files",
    "Fetch LFS objects and populate the current checkout.",
    "lfs pull",
)
c(
    "lfs-fetch",
    "lfs",
    "Fetch large files",
    "Download objects for the current reference without changing the checkout.",
    "lfs fetch",
)
c(
    "lfs-fetch-all",
    "lfs",
    "Fetch all LFS history",
    "Download every LFS object referenced by any local reference; may be very large.",
    "lfs fetch --all",
)
c(
    "lfs-push",
    "lfs",
    "Upload large files",
    "Upload LFS objects for a branch to a remote.",
    "lfs push {remote} {branch}",
    [f("remote", "Remote", "origin"), f("branch", "Branch")],
)
c(
    "lfs-checkout",
    "lfs",
    "Populate LFS pointers",
    "Replace pointer files with objects already available locally.",
    "lfs checkout",
)
c(
    "lfs-fsck",
    "lfs",
    "Verify large file integrity",
    "Check LFS object consistency. Git LFS may quarantine corrupt objects in .git/lfs/bad.",
    "lfs fsck",
)
c("lfs-env", "lfs", "LFS environment", "Inspect LFS endpoints, storage and configuration.", "lfs env")
c("lfs-locks", "lfs", "Browse file locks", "List locks advertised by the LFS server.", "lfs locks")
c(
    "lfs-lock",
    "lfs",
    "Lock a large file",
    "Reserve a file on an LFS server that supports locking.",
    "lfs lock {path}",
    [f("path", "File path")],
)
c(
    "lfs-unlock",
    "lfs",
    "Unlock a large file",
    "Release your file lock on the LFS server.",
    "lfs unlock {path}",
    [f("path", "File path")],
)
c(
    "lfs-migrate-info",
    "lfs",
    "Analyze migration candidates",
    "Report large file types across references before planning an LFS migration.",
    "lfs migrate info --everything",
)
c(
    "lfs-migrate",
    "lfs",
    "Migrate history into LFS",
    "Rewrite all local references for matching files. Back up the repository first.",
    "lfs migrate import --everything --include {pattern}",
    [f("pattern", "File pattern", "*.psd")],
    "Rewrites history across all local references. Back up the repository and coordinate with collaborators.",
)
c(
    "prune-preview",
    "cleanup",
    "Preview LFS cleanup",
    "See which local LFS objects would be removed. Deletes nothing.",
    "lfs prune --dry-run --verbose",
)
c(
    "prune",
    "cleanup",
    "Prune verified LFS objects",
    "Free local storage after verifying remote copies of reachable objects. Avoid shared lfs.storage directories.",
    "lfs prune --verify-remote",
    risk="Deletes eligible local LFS objects. Do not run if repositories share a custom LFS storage directory.",
)
c(
    "prune-force-preview",
    "cleanup",
    "Preview aggressive LFS cleanup",
    "Preview force-prune eligibility without deleting objects.",
    "lfs prune --force --dry-run --verbose",
)
c(
    "prune-force",
    "cleanup",
    "Force-prune LFS objects",
    "Aggressively remove local objects, including objects for the current checkout; preserve unpushed objects.",
    "lfs prune --force",
    risk="Deletes local LFS objects including those needed by checked-out references. You may need to download them again. Never use with shared lfs.storage.",
)
c(
    "clean-preview",
    "cleanup",
    "Preview untracked cleanup",
    "List untracked files and directories that clean would delete.",
    "clean -nd",
)
c(
    "clean",
    "cleanup",
    "Delete untracked files",
    "Delete untracked files and directories; ignored files are preserved.",
    "clean -fd",
    risk="Permanently deletes untracked files and directories. Git cannot recover them. Run the preview first.",
)
c(
    "gc",
    "cleanup",
    "Optimize Git storage",
    "Run normal Git garbage collection with default retention policies.",
    "gc",
)
c(
    "size",
    "cleanup",
    "Git storage report",
    "Inspect loose objects and packed object sizes.",
    "count-objects -vH",
)
c(
    "reflog",
    "recover",
    "Find a lost commit",
    "Browse recent HEAD movements to recover work.",
    "reflog -40 --date=relative",
)
c(
    "restore",
    "recover",
    "Discard file edits",
    "Replace unstaged file content from the index.",
    "restore -- {path}",
    [f("path", "Path or pattern", literal=True)],
    "Discards unstaged edits to this path. Git may not be able to recover them.",
)
c(
    "undo-commit",
    "recover",
    "Undo commit, keep staged work",
    "Move HEAD back one commit; keep its changes staged.",
    "reset --soft HEAD~1",
    risk="Moves this branch back one commit. Avoid on published commits; changes remain staged.",
)
c(
    "reset-hard",
    "recover",
    "Reset to a reference",
    "Reset tracked files and the branch to a chosen commit.",
    "reset --hard {ref}",
    [f("ref", "Target reference", "HEAD")],
    "Discards staged and unstaged tracked edits, may delete obstructing untracked paths, and moves the branch pointer.",
)
c(
    "revert",
    "recover",
    "Revert a commit",
    "Create an inverse commit without rewriting existing history.",
    "revert --no-edit {ref}",
    [f("ref", "Commit to revert")],
)
c(
    "init",
    "setup",
    "Initialize a repository",
    "Create a Git repository in the current folder.",
    "init",
    repo=False,
)
c(
    "clone",
    "setup",
    "Clone a repository",
    "Download a repository into a new directory.",
    "clone -- {url} {directory}",
    [f("url", "Repository URL"), f("directory", "Destination directory")],
    repo=False,
)
c(
    "identity",
    "setup",
    "Inspect configuration",
    "Show effective configuration and where each value comes from.",
    "config --list --show-origin",
    repo=False,
)
c(
    "user-name",
    "setup",
    "Set your Git name",
    "Configure your global commit author name.",
    "config --global user.name {name}",
    [f("name", "Your name", literal=True)],
    repo=False,
)
c(
    "user-email",
    "setup",
    "Set your Git email",
    "Configure your global commit author email.",
    "config --global user.email {email}",
    [f("email", "Your email", literal=True)],
    repo=False,
)
c(
    "lfs-install",
    "setup",
    "Enable Git LFS",
    "Install LFS filters for your user and hooks for this repository, if present.",
    "lfs install",
    repo=False,
)

BY_ID = {command.id: command for command in COMMANDS}


def search(query: str, category: str | None = None, recommended: tuple[str, ...] = ()) -> list[Command]:
    normalized = " ".join(query.casefold().split())
    words = normalized.split()
    result = []
    for command in COMMANDS:
        if category == "recommended" and command.id not in recommended:
            continue
        if category and category != "recommended" and command.category != category:
            continue
        examples = " ".join(
            example.label + " " + " ".join(value for _, value in example.values)
            for example in command.examples
        )
        haystack = (
            f"{command.id} {command.title} {command.hint} {command.description} "
            f"{command.command_line} {command.category} {CATEGORIES[command.category][1]} {examples}"
        ).casefold()
        if all(word in haystack for word in words):
            result.append(command)
    if category == "recommended":
        result.sort(key=lambda command: recommended.index(command.id))
    elif normalized:

        def relevance(command: Command):
            variants = (
                command.completion.casefold(),
                command.completion[4:].casefold(),
                command.title.casefold(),
                command.id.casefold(),
            )
            score = min(
                (
                    index * 2 + (0 if text == normalized else 1)
                    for index, text in enumerate(variants)
                    if text.startswith(normalized)
                ),
                default=8,
            )
            return score, bool(command.risk)

        result.sort(key=relevance)
    return result


def complete(value: str) -> str | None:
    """Suggest an existing action by command syntax or friendly name, without executing it."""
    query = value.casefold()
    if not query.strip():
        return None
    for command in search(value):
        for candidate in (command.completion, command.completion[4:], command.title):
            if candidate.casefold().startswith(query):
                return candidate if len(candidate) > len(value) else None
    return None
