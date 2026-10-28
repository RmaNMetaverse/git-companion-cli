# Git Companion

A friendly, colorful home for your Git projects and large artwork files. Save versions, share work, try ideas and recover earlier changes without memorizing terminal commands.

https://github.com/user-attachments/assets/962562af-7fc8-4bfe-adf2-0718bfd64cb9

## Set up once

Choose the file for your computer, right here in this folder:

| Your computer | Setup file | What to do |
| --- | --- | --- |
| Windows | [setup-windows.cmd](setup-windows.cmd) | Double-click it |
| macOS | [setup-macos.command](setup-macos.command) | Open it in Terminal, or run `sh setup-macos.command` |
| Linux | [setup-linux.sh](setup-linux.sh) | Run `sh setup-linux.sh` |

Setup handles Python and the app's dependencies automatically. An internet connection is needed. You do not need to create or activate a Python environment.

**When setup finishes, close and reopen your terminal.** Open your project folder in that terminal, then type:

```text
git-companion
```

Git Companion uses the folder you are currently in. The setup file can be deleted afterwards. On Windows, you may need to fully quit and relaunch your terminal app for the new command to become available.

The app also checks for Git and Git LFS and attempts to install missing tools using your computer's package manager. Your operating system may request administrator permission. If a package manager is unavailable, the app explains what is missing.

## Find your next step

Choose a workflow on the left, or search for what you want to do. Each action has a short, plain-language hint. **Details & examples** stays closed until you expand it; press **F2** for the selected action's examples, including in a small terminal window.

The dedicated **Search all commands** box finds every included Git and Git LFS action, across all workflows. Search by a task (`save`, `Photoshop`), a command (`git lfs prune`), or flags (`--dry-run`). Suggestions update while you type. Press **Tab** or **Right** to accept an inline completion, **Down** to browse the results, and **Enter** to review your selection. **Ctrl+F** jumps to search; **Escape** clears it and returns to your workflow. Completing or selecting a command never runs it automatically.

Examples show possibilities; they never run automatically. Fill in your own file names when reviewing an action. You can always see the actual command before running it. Actions that can discard work also show a warning and require confirmation.

When you run an action, **Command results** opens automatically with live output, errors and a clear final status. Commands that return no text still show whether they succeeded. Scroll to read longer output. **Escape** returns to your commands; **F3** or the **Results** button reopens the latest result. **Ctrl+X** or **Stop command** stops a running operation. The embedded live terminal also stays visible in compact windows.

| Workflow | Use it to… |
| --- | --- |
| For you | Find suggested next steps for your current project |
| Look around | See what changed and browse earlier saves |
| Save your work | Choose files and save a version with a note |
| Try ideas | Explore another direction in a separate branch |
| Share & sync | Download shared updates and upload your saves |
| Large files | Manage artwork, scenes, textures and media with LFS |
| Reclaim space | Preview cleanup before removing local downloads |
| Recover | Find earlier save points and undo changes |
| Set up | Start a project, download one or set your author name |

Mouse navigation works too. Use **Tab** to move between controls, arrow keys to browse, **Enter** to select, and **Escape** to go back. **Ctrl+F** searches, **Ctrl+O** opens another folder, and **Ctrl+Q** quits.

## Project files

The three setup files above are all you need to install the app. `src` holds the application code. `dev` holds tests, build tools, setup templates and development notes.

For technical setup, architecture and build instructions, see the [developer guide](dev/README.md).
