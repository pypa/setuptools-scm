#!/usr/bin/env bash
set -euxo pipefail

rm -rf y z home venv tmp

[ ! -d black ] && git clone https://github.com/psf/black
export SETUPTOOLS_SCM_DEBUG=1
export PRE_COMMIT_HOME="$PWD/home"
export TMPDIR="$PWD/tmp"

git init y
git init z
git -C z commit --allow-empty -m 'commit!'
git -C y submodule add "$PWD/z"
cat > "$PWD/y/.git/modules/z/hooks/pre-commit" <<EOF
#!/usr/bin/env bash
virtualenv "$PWD/venv"
"$PWD/venv/bin/pip" install -e "$1"
"$PWD/venv/bin/pip" install --no-clean "$PWD/black"
EOF
chmod +x "$PWD/y/.git/modules/z/hooks/pre-commit"
cd y/z
git commit -m "test"
