import os
import sys

from setuptools_scm.git import GitWorkdir


class PreCommitHook:
    def __init__(self, repo_dir, build_command):
        self.build_command = build_command
        self.work_dir = GitWorkdir.from_potential_worktree(repo_dir)

    def is_git_rebasing(self):
        """Checks if git is currently in rebase mode and returns the output of build_command.

        This detection code could be improved, Here is a summary of how well this
        handles various git operations.
        Rebase: A series of post-commit hooks where `is_git_rebasing` returns true,
            and finally the post-rewrite hook is called. This is why we have a separate
            `update-egg-info-rewrite` hook that passes `--post-rewrite` to force the
            running of build_command.
        Squash: For each commit being squashed, `is_git_rebasing` returns true for
            the post-commit hook, but the post-rewrite hook is called several times,
            calling build_command each of those times.
        Amend: This ends up calling build_command twice.
        """
        git_dir = self.work_dir.get_git_dir()
        rebase_merge = os.path.join(git_dir, "rebase-merge")
        rebase_apply = os.path.join(git_dir, "rebase-apply")
        return os.path.exists(rebase_merge) or os.path.exists(rebase_apply)

    def update_egg_info(self, force_on_rebase=False):
        """Run the `python setup.py egg_info` if this is a editable install."""

        # Allow users to temporarily disable the hook. `is_git_rebasing` doesn't work
        # in all cases and there may be cases where you want to disable this hook to
        # speed up git operations. Running egg_info adds some slowness to the git
        # commands, especially for large packages with a lot of files.
        if os.getenv("SETUPTOOLS_SCM_SKIP_UPDATE_EGG_INFO", "0") != "0":
            output = (
                'update-egg-info: Skipping, "SETUPTOOLS_SCM_SKIP_UPDATE_EGG_INFO" '
                "env var set."
            )
            return output, 0

        # If this is not an editable install there is no need to run it
        contents = os.listdir(self.work_dir.path)

        # If there is not a setup.cfg or setup.py file then this can't be an editable
        # install, no need to try to run build_command.
        if "setup.cfg" not in contents and "setup.py" not in contents:
            output = "update-egg-info: Skipping, no setup script found."
            return output, 0

        # If a egg_info directory doesn't exist its not currently an editable install
        # don't turn it into one.
        if not any(filter(lambda i: os.path.splitext(i)[-1] == ".egg-info", contents)):
            output = "update-egg-info: Skipping, no .egg-info directory found."
            return output, 0

        # Check if git is currently rebasing, if so and force_on_rebase is False, this
        # is likely a post-commit call, and the post-rewrite hook will be called later,
        # skip running build_command for now.
        if not force_on_rebase and self.is_git_rebasing():
            output = "update-egg-info: Skipping, rebase in progress."
            return output, 0

        # Run the build command
        output = [f"update-egg-info: Running command: {self.build_command}"]
        cmd_out, error, returncode = self.work_dir.do_ex(self.build_command)

        if cmd_out:
            output += cmd_out
        if returncode and error:
            output.append("update-egg-info: Error running build_command:")
            output.append(error)

        output = "\n".join(output)
        return output, returncode


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description=(
            "Pre-commit hook interface for automatically updating egg-info of "
            "editable installs."
        )
    )
    parser.add_argument(
        "--post-rewrite",
        action="store_true",
        help=(
            "Force running `command` after a rebase. update-egg-info skips calling "
            "`command` if it detects that git is performing a rebase as generating the"
            "egg_info takes extra time, especially for larger packages."
        ),
    )
    parser.add_argument(
        "command",
        default=["python", "setup.py", "egg_info"],
        nargs="*",
        help=(
            "The command the hook will run to update the editable "
            'install. Defaults to: "python setup.py egg_info"'
        ),
    )
    args = parser.parse_args()

    hook = PreCommitHook(os.getcwd(), build_command=args.command)
    output, returncode = hook.update_egg_info(force_on_rebase=args.post_rewrite)

    print(output)

    # Return the error code so pre-commit can report the failure.
    sys.exit(returncode)


if __name__ == "__main__":
    main()
