"""Short, artist-friendly hints with two opt-in examples for every action."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Example:
    label: str
    values: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class Guide:
    hint: str
    examples: tuple[Example, Example]


def e(label: str, **values: str) -> Example:
    return Example(label, tuple(values.items()))


GUIDANCE: dict[str, Guide] = {}


def g(id: str, hint: str, first: Example, second: Example):
    GUIDANCE[id] = Guide(hint, (first, second))


g(
    "status",
    "See what changed and what is ready to save.",
    e("Check which artwork files you edited."),
    e("Check that everything is saved before leaving."),
)
g(
    "graph",
    "See your project's recent save history as a simple graph.",
    e("Find the latest saved version of your project."),
    e("See where two versions of an idea split."),
)
g(
    "diff",
    "See a quick summary of edits you have not prepared to save.",
    e("Check how many files changed since your last save."),
    e("Review the size of an edit before saving it."),
)
g(
    "patch",
    "Read the exact text changes you have made.",
    e("Review changes to a project notes file."),
    e("Check edits to a text-based scene file."),
)
g(
    "staged",
    "Review the changes included in your next saved version.",
    e("Check your prepared edits before making a commit."),
    e("Make sure unrelated edits are left out."),
)
g(
    "show",
    "Look inside an earlier saved version.",
    e("Inspect your latest save.", ref="HEAD"),
    e("Inspect the save before that.", ref="HEAD~1"),
)
g(
    "blame",
    "See who last edited each line of a text file.",
    e("Check who updated your project notes.", path="notes.txt"),
    e("Find who changed an export script.", path="scripts/export.py"),
)
g(
    "tags",
    "Find named milestones, such as approved versions.",
    e("Find the tag for a client-approved delivery."),
    e("Browse previous release milestones."),
)
g(
    "stage",
    "Choose a file or folder for your next saved version.",
    e("Prepare one illustration.", path="artwork/cover.psd"),
    e("Prepare all edits in your artwork folder.", path="artwork/"),
)
g(
    "stage-all",
    "Prepare all new, edited and deleted files to save together.",
    e("Include a whole set of revised illustrations."),
    e("Include a scene update and its new textures."),
)
g(
    "unstage",
    "Leave a file out of your next save; keep its edits.",
    e("Leave an unfinished illustration out.", path="artwork/draft.psd"),
    e("Leave all prepared files out for now.", path="."),
)
g(
    "commit",
    "Save your prepared changes with a short note.",
    e("Save a finished illustration.", message="Finish cover illustration"),
    e("Save a round of client feedback.", message="Apply client color feedback"),
)
g(
    "amend",
    "Replace your latest save with corrected changes or a new note.",
    e("Correct the note on your latest private save.", message="Finish cover and title lettering"),
    e("Include a forgotten file you have now prepared.", message="Add final artwork and texture"),
)
g(
    "stash",
    "Set unfinished work aside so you can return to it later.",
    e("Pause a color experiment.", message="Color study in progress"),
    e("Pause a scene before switching tasks.", message="Lighting experiment"),
)
g(
    "stash-list",
    "Find work you previously set aside.",
    e("Find your paused lighting experiment."),
    e("Check which unfinished ideas you still have saved."),
)
g(
    "stash-apply",
    "Bring back set-aside work while keeping its backup.",
    e("Bring back your most recently paused work.", ref="stash@{0}"),
    e("Bring back the work paused before that.", ref="stash@{1}"),
)
g(
    "stash-drop",
    "Delete a backup of work you previously set aside.",
    e("Delete the latest stash after saving its work elsewhere.", ref="stash@{0}"),
    e("Delete an older stash you have already recovered.", ref="stash@{1}"),
)
g(
    "branches",
    "See the different versions of your project in progress.",
    e("Find your alternate-cover branch."),
    e("Check which branch follows the shared project."),
)
g(
    "switch",
    "Move to another existing version of your project.",
    e("Return to your main project.", branch="main"),
    e("Return to an alternate cover idea.", branch="alternate-cover"),
)
g(
    "new-branch",
    "Start a separate space to try an idea.",
    e("Try another cover without changing the main version.", branch="alternate-cover"),
    e("Try a new lighting direction.", branch="warm-lighting"),
)
g(
    "rename-branch",
    "Give the current project branch a clearer name.",
    e("Name an experiment after its purpose.", branch="client-color-study"),
    e("Rename a draft branch for delivery.", branch="cover-final-review"),
)
g(
    "delete-branch",
    "Remove a local branch after its work has been combined.",
    e("Remove a finished cover experiment.", branch="alternate-cover"),
    e("Remove a finished lighting branch.", branch="warm-lighting"),
)
g(
    "merge",
    "Combine another branch's saved work into this one.",
    e("Bring an alternate cover into your current branch.", branch="alternate-cover"),
    e("Bring the main project's updates into your branch.", branch="main"),
)
g(
    "merge-abort",
    "Cancel an unfinished attempt to combine branches.",
    e("Back out when two scene versions conflict."),
    e("Cancel before choosing how to combine overlapping edits."),
)
g(
    "rebase",
    "Replay your branch's saves on a newer starting point.",
    e("Update a private experiment to start from main.", branch="main"),
    e("Update a private draft to start from a review branch.", branch="client-review"),
)
g(
    "rebase-continue",
    "Continue replaying saves after you have fixed a conflict.",
    e("Continue after resolving and preparing conflicting notes."),
    e("Continue after choosing which scene file to keep and staging it."),
)
g(
    "rebase-abort",
    "Cancel a rebase and return to your original branch state.",
    e("Back out when updating a private experiment gets complicated."),
    e("Return to the point before you started replaying saves."),
)
g(
    "cherry-pick",
    "Copy one saved change onto your current branch.",
    e("Copy the latest save from another branch.", ref="alternate-cover"),
    e("Copy one known save by its ID.", ref="abc1234"),
)
g(
    "worktrees",
    "Find other folders linked to this same project history.",
    e("Find a second checkout used for rendering."),
    e("Check where your other working copies live."),
)
g(
    "fetch",
    "Check for shared updates without changing your files.",
    e("Check what teammates saved while you were away."),
    e("Refresh the shared branch list before choosing what to download."),
)
g(
    "pull",
    "Bring in shared updates when Git can apply them directly.",
    e("Download teammates' latest saves before starting work."),
    e("Update a clean project folder before rendering."),
)
g(
    "push",
    "Upload your saved changes to your connected shared project.",
    e("Share a finished illustration after committing it."),
    e("Back up your latest saved work to the shared server."),
)
g(
    "push-upstream",
    "Share a new branch and connect it for future uploads.",
    e("Share an alternate cover for review.", remote="origin", branch="alternate-cover"),
    e("Share your lighting experiment.", remote="origin", branch="warm-lighting"),
)
g(
    "force-push",
    "Replace shared history after intentionally rewriting your saves.",
    e("Upload an amended private branch that you own."),
    e("Upload a rebased branch after coordinating with collaborators."),
)
g(
    "remotes",
    "See the server addresses this project downloads from and uploads to.",
    e("Check which shared project you are connected to."),
    e("Check where your next upload would go."),
)
g(
    "add-remote",
    "Connect this local project to a shared server.",
    e("Connect a new shared art project.", name="origin", url="https://github.com/your-team/art-project.git"),
    e("Connect a second project backup.", name="backup", url="https://github.com/your-team/art-backup.git"),
)
g(
    "tag",
    "Give this saved version a memorable milestone name.",
    e("Mark a client-approved delivery.", tag="approved-v1", message="Client approved cover"),
    e("Mark a final render milestone.", tag="render-v2", message="Final lighting render"),
)
g(
    "push-tag",
    "Share one named milestone with your team.",
    e("Share the approved delivery milestone.", remote="origin", tag="approved-v1"),
    e("Share a final render milestone.", remote="origin", tag="render-v2"),
)
g(
    "lfs-status",
    "Check which large files still need saving or uploading.",
    e("Check a revised Photoshop file before sharing."),
    e("Check which scene assets are waiting to upload."),
)
g(
    "lfs-files",
    "See your LFS-managed files and their sizes.",
    e("Find the large artwork files managed by LFS."),
    e("Check the sizes of your tracked video and scene files."),
)
g(
    "lfs-patterns",
    "See which file types this project sends through LFS.",
    e("Check whether Photoshop files are tracked."),
    e("Check whether Blender files are tracked before adding a scene."),
)
g(
    "lfs-track",
    "Tell LFS to manage a type of large file.",
    e("Track Photoshop documents.", pattern="*.psd"),
    e("Track Blender scenes.", pattern="*.blend"),
)
g(
    "lfs-untrack",
    "Stop using an LFS tracking rule for future file additions.",
    e("Remove the Photoshop tracking rule.", pattern="*.psd"),
    e("Remove the video tracking rule.", pattern="*.mp4"),
)
g(
    "lfs-pull",
    "Download the real large files for the version you have open.",
    e("Get the actual artwork after cloning a project."),
    e("Replace small LFS pointer files with usable scenes and textures."),
)
g(
    "lfs-fetch",
    "Download large files into local storage without replacing your files.",
    e("Prepare large assets before checking them out."),
    e("Cache the current version's large files before going offline."),
)
g(
    "lfs-fetch-all",
    "Download large files from all locally known project history.",
    e("Prepare a complete local LFS backup; this may take much space."),
    e("Collect older LFS assets before moving a project to a new server."),
)
g(
    "lfs-push",
    "Upload a branch's saved large files to a shared server.",
    e("Upload main's saved artwork files.", remote="origin", branch="main"),
    e("Upload a cover-review branch's large files.", remote="origin", branch="alternate-cover"),
)
g(
    "lfs-checkout",
    "Restore real large files that are already downloaded.",
    e("Replace pointer files using your local LFS cache."),
    e("Populate available scene assets without another download."),
)
g(
    "lfs-fsck",
    "Check that your downloaded large files are complete and intact.",
    e("Investigate an asset that appears corrupt."),
    e("Check local LFS data after an interrupted transfer."),
)
g(
    "lfs-env",
    "See where LFS stores files and which server it uses.",
    e("Check the LFS server address when a download fails."),
    e("Find the local storage location before investigating disk usage."),
)
g(
    "lfs-locks",
    "See which large files are reserved by you or your teammates.",
    e("Check whether someone is already editing a scene."),
    e("Find your own locks before handing work to a teammate."),
)
g(
    "lfs-lock",
    "Reserve a file so teammates know you are editing it.",
    e("Reserve a Photoshop document.", path="artwork/cover.psd"),
    e("Reserve a Blender scene.", path="scenes/studio.blend"),
)
g(
    "lfs-unlock",
    "Release a file reservation when you finish editing.",
    e("Release a cover after sharing your changes.", path="artwork/cover.psd"),
    e("Release a scene for the next artist.", path="scenes/studio.blend"),
)
g(
    "lfs-migrate-info",
    "Find large file types that could be moved into LFS.",
    e("Check whether old Photoshop files are making the project heavy."),
    e("Review older video files before planning a migration."),
)
g(
    "lfs-migrate",
    "Rewrite old saved versions to move selected file types into LFS.",
    e("Move historical Photoshop files after backing up the project.", pattern="*.psd"),
    e("Move historical Blender scenes after coordinating with your team.", pattern="*.blend"),
)
g(
    "prune-preview",
    "See which unused large-file downloads can be removed; delete nothing.",
    e("Check how much LFS storage a normal cleanup could free."),
    e("Review old downloaded assets before deciding to clean up."),
)
g(
    "prune",
    "Remove eligible local LFS downloads, checking remote copies first.",
    e("Free disk space after reviewing the normal cleanup preview."),
    e("Remove eligible old downloads after uploading your work."),
)
g(
    "prune-force-preview",
    "Preview an aggressive LFS cleanup without deleting anything.",
    e("Check what force-prune would remove before deciding."),
    e("Compare aggressive cleanup with the normal preview."),
)
g(
    "prune-force",
    "Remove more LFS downloads, including ones your current version needs.",
    e("Reclaim downloads you accept having to download again later."),
    e("Aggressively clear eligible LFS data after reviewing its preview."),
)
g(
    "clean-preview",
    "See which files Git does not track and would delete in a cleanup.",
    e("Check whether an unsaved sketch would be deleted."),
    e("Review untracked export folders before cleaning."),
)
g(
    "clean",
    "Delete files and folders Git is not tracking.",
    e("Delete unwanted untracked exports after checking the preview."),
    e("Remove abandoned draft files you have backed up elsewhere."),
)
g(
    "gc",
    "Let Git tidy and compress its stored project history.",
    e("Run normal maintenance after a long editing period."),
    e("Compress Git history after many small saves; this does not prune LFS."),
)
g(
    "size",
    "Check how much space regular Git history is using.",
    e("Inspect Git storage before doing maintenance."),
    e("Compare Git storage before and after normal garbage collection."),
)
g(
    "reflog",
    "Find recent save points, including ones you may have lost track of.",
    e("Find a save after moving a branch by mistake."),
    e("Look up where you were before an undo operation."),
)
g(
    "restore",
    "Throw away a file's unsaved edits and restore its prepared version.",
    e("Discard an unwanted edit to a cover.", path="artwork/cover.psd"),
    e("Discard edits in your notes file.", path="notes.txt"),
)
g(
    "undo-commit",
    "Undo your latest save while keeping its changes prepared to save again.",
    e("Redo your last private save as two smaller saves."),
    e("Undo a private commit so you can revise its contents."),
)
g(
    "reset-hard",
    "Move to a saved version and discard tracked changes in your way.",
    e("Discard tracked edits and return to your latest save.", ref="HEAD"),
    e("Return to an approved milestone after backing up newer work.", ref="approved-v1"),
)
g(
    "revert",
    "Make a new save that undoes an earlier saved change.",
    e("Undo your most recent commit without erasing its history.", ref="HEAD"),
    e("Undo a known commit using its ID.", ref="abc1234"),
)
g(
    "init",
    "Start keeping version history in this folder.",
    e("Turn a new illustration folder into a Git project."),
    e("Start tracking versions of an existing local art project."),
)
g(
    "clone",
    "Download a shared project into a new folder.",
    e(
        "Get your team's art project.",
        url="https://github.com/your-team/art-project.git",
        directory="art-project",
    ),
    e("Get a texture library.", url="https://github.com/your-team/textures.git", directory="texture-library"),
)
g(
    "identity",
    "See the Git settings currently used on this computer.",
    e("Check which name and email Git uses for saves."),
    e("Find where an unexpected project setting comes from."),
)
g(
    "user-name",
    "Set the name shown beside the changes you save.",
    e("Use your full name.", name="Alex Rivera"),
    e("Use your studio name.", name="River Studio"),
)
g(
    "user-email",
    "Set the email attached to changes you save.",
    e("Use your work email.", email="alex@example.com"),
    e("Use your studio email.", email="artist@example.com"),
)
g(
    "lfs-install",
    "Prepare Git LFS to handle large artwork and media files.",
    e("Enable LFS before tracking Photoshop files."),
    e("Set up LFS hooks in a project you just opened."),
)
