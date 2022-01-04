import os
import sys

from setuptools_scm.git import GitWorkdir


class PreCommitHook:
    def __init__(self, repo_dir, venv_name=".setuptools_scm", build_command=None):
        self.build_command = build_command
        self.work_dir = GitWorkdir.from_potential_worktree(repo_dir)
        self.venv_name = venv_name
        self.header = "update-egg-info:"

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

    def run_virtualenv(self):
        """Create a virtualenv if required and run an editable pip install of this
        pip package.
        """
        output = []
        venv = os.path.join(self.work_dir.path, self.venv_name)

        # Create the virtualenv only if it doesn't already exist
        if not os.path.exists(venv):
            output.append(f"{self.header} Creating Virtualenv: {venv}")
            cmd_out, error, returncode = self.work_dir.do_ex(["virtualenv", venv])
            if cmd_out:
                output.append(cmd_out)

        # Build the pip command. Calling the venv's pip exe will automatically
        # activate the environment.
        bin_part = "Scripts" if os.name == "nt" else "bin"
        pip_path = os.path.join(venv, bin_part, "pip")
        # Use `--no-deps` to skip the overhead of installing any dependencies
        # we won't actually be using this install
        pip_cmd = [pip_path, "install", "-e", self.work_dir.path, "--no-deps"]

        # Run the editable install
        output.append('{} Running: "{}"'.format(self.header, " ".join(pip_cmd)))
        cmd_out, error, returncode = self.work_dir.do_ex(pip_cmd)
        if cmd_out:
            output.append(cmd_out)

        return "\n".join(output), error, returncode

    def update_egg_info(self, force_on_rebase=False):
        """Run the `python setup.py egg_info` if this is a editable install."""

        # Allow users to temporarily disable the hook. `is_git_rebasing` doesn't work
        # in all cases and there may be cases where you want to disable this hook to
        # speed up git operations. Running egg_info adds some slowness to the git
        # commands, especially for large packages with a lot of files.
        if os.getenv("SETUPTOOLS_SCM_SKIP_UPDATE_EGG_INFO", "0") != "0":
            output = (
                f'{self.header} Skipping, "SETUPTOOLS_SCM_SKIP_UPDATE_EGG_INFO" '
                "env var set."
            )
            return output, 0

        # Check if git is currently rebasing, if so and force_on_rebase is False, this
        # is likely a post-commit call, and the post-rewrite hook will be called later,
        # skip running build_command for now.
        if not force_on_rebase and self.is_git_rebasing():
            output = f"{self.header} Skipping, rebase in progress."
            return output, 0

        output = []
        if self.build_command:
            output.append(f"{self.header} Running command: {self.build_command}")
            cmd_out, error, returncode = self.work_dir.do_ex(self.build_command)
        else:
            cmd_out, error, returncode = self.run_virtualenv()

        if cmd_out:
            output.append(cmd_out)
        if returncode and error:
            output.append(f"{self.header} Error running build_command:")
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
        "--venv-name",
        default=".setuptools_scm",
        help=(
            "By default creates this virtualenv folder inside the repo and does an"
            "editable install using `pip install -e .`."
        ),
    )
    parser.add_argument(
        "command",
        nargs="*",
        help=(
            "If specified disables creating a virtualenv and simply runs this command."
        ),
    )
    args = parser.parse_args()

    hook = PreCommitHook(
        os.getcwd(), venv_name=args.venv_name, build_command=args.command
    )
    output, returncode = hook.update_egg_info(force_on_rebase=args.post_rewrite)

    print(output)

    # Return the error code so pre-commit can report the failure.
    sys.exit(returncode)


if __name__ == "__main__":
    main()
