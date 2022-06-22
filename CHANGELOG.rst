v7.0.2
======

* fix #723 and #722: remove bootstrap dependencies
* bugfix: ensure we read the distribution name from setup.cfg
  if needed even for pyproject
*

v7.0.1
=======

* fix #718: Avoid `ModuleNotFoundError` by requiring importlib_metadata in python < 3.8

v7.0.0
=======

* drop python 3.6 support
* include git archival support
* fix #707: support git version detection even when git protects against mistmatched owners
            (common with misconfigured containers, thanks @chrisburr )

v6.4.3
======

* fix #548: correctly handle parsing the commit timestamp of HEAD when ``log.showSignature`` is set

v6.4.2
======

* fix #671 : NoReturn is not avaliable in painfully dead python 3.6


v6.4.1
=======


* fix regression #669: restore get_version signature
* fix #668: harden the selftest for distribution extras

6.4.0
======

* compatibility adjustments for setuptools >58
* only put minimal setuptools version into toml extra to warn people with old strict pins
* coorectly handle hg-git self-use
* better mercurial detection
* modernize packaging setup
* python 3.10 support
* better handling of setuptools install command deprecation
* consider ``pyproject.tomls`` when running as command
* use list in git describe command to avoid shell expansions while supporting both windows and posix
* add ``--strip-dev`` flag to ``python -m setuptools_scm`` to print the next guessed version cleanly
* ensure no-guess-dev will fail on bad tags instead of generating invalid versions
* ensure we use utc everywhere to avoid confusion

6.3.2
=====

* fix #629: correctly convert Version data in tags_to_version parser to avoid errors

6.3.1
=====

* fix #625: restore tomli in install_requires after the regression changes in took it out
  and some users never added it even tho they have pyproject.toml files

6.3.0
=======

.. warning::

   This release explicitly warns on unsupported setuptools.
   This unfortunately has to happen as the legacy ``setup_requires`` mechanism
   incorrectly configures the setuptools working-set when a more recent setuptools
   version than available is required.

   As all releases of setuptools are affected as the historic mechanism
   for ensuring a working setuptools setup was shipping a ``ez_setup`` file
   next to ``setup.py``, which would install the required version of setuptools.

   This mechanism has long since been deprecated and removed
   as most people haven't been using it


* fix #612: depend on packaging to ensure version parsing parts
* fix #611: correct the typo that hid away the toml extra and add it in ``setup.py`` as well
* fix #615: restore support for the git_archive plugin which doesn't pass over the config
* restore the ability to run on old setuptools while to avoid breaking pipelines

v6.2.0
=======

* fix #608: resolve tomli dependency issue by making it a hard dependency
  as all intended/supported install options use pip/wheel this is only a feature release
* ensure python 3.10 works

v6.1.1
=======

* fix #605: completely disallow bdist_egg - modern enough setuptools>=45 uses pip
* fix #606: re-integrate and harden toml parsing
* fix #597: harden and expand support for figuring the current distribution name from
  `pyproject.toml` (`project.name` or `tool.setuptools_scm.dist_name`) section or `setup.cfg` (`metadata.name`)

v6.1.0
======

* fix #587: don't fail file finders when distribution is not given
* fix #524: new parameters ``normalize`` and ``version_cls`` to customize the version normalization class.
* fix #585: switch from toml to tomli for toml 1.0 support
* fix #591: allow to opt in for searching parent directories in the api
* fix #589: handle yaml encoding using the expected defaults
* fix #575: recommend storing the version_module inside of ``mypkg/_version.py``
* fix #571: accept branches starting with ``v`` as release branches
* fix #557: Use ``packaging.version`` for ``version_tuple``
* fix #544: enhance errors on unsupported python/setuptools versions

v6.0.1
======

*  fix #537: drop node_date on old git to avoid errors on missing %cI

v6.0.0
======

* fix #517: drop dead python support >3.6 required
* drop dead setuptools support > 45 required (can install wheels)
* drop egg building (use wheels)
* add git node_date metadata to get the commit time-stamp of HEAD
* allow version schemes to be priority ordered lists of version schemes
* support for calendar versioning (calver) by date

v5.0.2
======

* fix #415: use git for matching prefixes to support the windows situation

v5.0.1
======

* fix #509: support ``SETUPTOOLS_SCM_PRETEND_VERSION_FOR_${DISTRIBUTION_NAME}`` for ``pyproject.toml``

v5.0.0
======


Breaking changes:

* fix #339: strict errors on missing scms when  parsing a scm dir to avoid false version lookups
* fix #337: if relative_to is a directory instead of a file,
  consider it as direct target instead  of the containing folder and print a warning

Bugfixes:

* fix #352: add support for generally ignoring specific vcs roots
* fix #471: better error for version bump failing on complex but accepted tag
* fix #479: raise indicative error when tags carry non-parsable information
* Add `no-guess-dev` which does no next version guessing, just adds `.post1.devN` in
  case there are new commits after the tag
* add python3.9
* enhance documentation
* consider SOURCE_DATE_EPOCH for versioning
* add a version_tuple to write_to templates
* fix #321: add support for the ``SETUPTOOLS_SCM_PRETEND_VERSION_FOR_${DISTRIBUTION_NAME}`` env var to target the pretend key
* fix #142: clearly list supported scm
* fix #213: better error message for non-zero dev numbers in tags
* fix #356: add git branch to version on describe failure

v4.1.2
=======

* disallow git tags without dots by default again - #449

v4.1.1
=======

* drop jaraco.windows from pyproject.toml, allows for wheel builds on python2


v4.1.0
=======

* include python 3.9 via the deadsnakes action
* return release_branch_semver scheme (it got dropped in a bad rebase)
* undo the devendoring of the samefile backport for python2.7 on windows
* re-enable the building of universal wheels
* fix handling of missing git/hg on python2.7 (python 3 exceptions where used)
* correct the tox flake8 invocation
* trigger builds on tags again

v4.0.0
======

* Add ``parentdir_prefix_version`` to support installs from GitHub release
  tarballs.
* use  Coordinated Universal Time (UTC)
* switch to github actions for ci
* fix documentation for ``tag_regex`` and add support for single digit versions
* document handling of enterprise distros with unsupported setuptools versions #312
* switch to declarative metadata
* drop the internal copy of samefile and use a dependency on jaraco.windows on legacy systems
* select git tags based on the presence of numbers instead of dots
* enable getting a version form a parent folder prefix
* add release-branch-semver version scheme
* make global configuration available to version metadata
* drop official support for python 3.4

v3.5.0
======

* add ``no-local-version`` local scheme and improve documentation for schemes

v3.4.4
======

* fix #403: also sort out resource warnings when dealing with git file finding

v3.4.3
======

* fix #399: ensure the git file finder terminates subprocess after reading archive

v3.4.2
======

* fix #395: correctly transfer tag regex in the Configuration constructor
* rollback --first-parent for git describe as it turns out to be a regression for some users

v3.4.1
======

* pull in #377 to fix #374: correctly set up the default version scheme for pyproject usage.
  this bugfix got missed when ruushing the  release.

v3.4.0
======

* fix #181 - add support for projects built under setuptools declarative config
  by way of the setuptools.finalize_distribution_options hook in Setuptools 42.

* fix #305 - ensure the git file finder closes filedescriptors even when errors happen

* fix #381 - clean out env vars from the git hook system to ensure correct function from within

* modernize docs wrt importlib.metadata

*edited*

* use --first-parent for git describe

v3.3.3
======

* add eggs  for python3.7 and 3.8 to the deploy

v3.3.2
======


* fix #335 - fix python3.8 support and add builds for up to python3.8

v3.3.1
======

* fix #333 (regression from #198) - use a specific fallback root when calling fallbacks. Remove old
  hack that resets the root when fallback entrypoints are present.

v3.3.0
======

* fix #198 by adding the ``fallback_version`` option, which sets the version to be used when everything else fails.

v3.2.0
======

* fix #303 and #283 by adding the option ``git_describe_command`` to allow the user to control the
way that `git describe` is called.

v3.1.0
=======

* fix #297 - correct the invocation in version_from_scm and deprecate it as its exposed by accident
* fix #298 - handle git file listing on empty repositories
* fix #268 - deprecate ScmVersion.extra


v3.0.6
======
* fix #295 - correctly handle selfinstall from tarballs

v3.0.5
======

* fix #292 - match leading ``V`` character as well

  https://www.python.org/dev/peps/pep-0440/#preceding-v-character

v3.0.4
=======

* rerelease of 3.0.3 after fixing the release process

v3.0.3  (pulled from pypi due to a packaging issue)
======

* fix #286 - duo an oversight a helper functio nwas returning a generator instead of a list


v3.0.2
======

* fix a regression from tag parsing - support for multi-dashed prefixes - #284


v3.0.1
=======

* fix a regression in setuptools_scm.git.parse - reorder arguments so the positional invocation from before works as expected #281

v3.0.0
=======

* introduce pre-commit and use black
* print the origin module to help testing
* switch to src layout (breaking change)
* no longer alias tag and parsed_version in order to support understanding a version parse failure
* require parse results to be ScmVersion or None (breaking change)
* fix #266 by requiring the prefix word to be a word again
  (breaking change as the bug allowed arbitrary prefixes while the original feature only allowed words")
* introduce an internal config object to allow the configuration for tag parsing and prefixes
  (thanks to @punkadiddle for introducing it and passing it through)

v2.1.0
======

* enhance docs for sphinx usage
* add symlink support to file finder for git #247
  (thanks Stéphane Bidoul)
* enhance tests handling win32
  (thanks Stéphane Bidoul)

v2.0.0
========

* fix #237 - correct imports in code examples
* improve mercurial commit detection (thanks Aaron)
* breaking change: remove support for setuptools before parsed versions
* reintroduce manifest as the travis deploy can't use the file finder
* reconfigure flake8 for future compatibility with black
* introduce support for branch name in version metadata and support a opt-in simplified semver version scheme

v1.17.0
========

* fix regression in git support - use a function to ensure it works in egg isntalled mode
* actually fail if file finding fails in order to see broken setups instead of generating broken dists

  (thanks Mehdi ABAAKOUK for both)


v1.16.2
========

* fix regression in handling git export ignores
  (thanks Mehdi ABAAKOUK)

v1.16.1
=======

* fix regression in support for old setuptools versions
  (thanks Marco Clemencic)


v1.16.0
=======

* drop support for eol python versions
* #214 - fix misuse in surogate-escape api
* add the node-and-timestamp local version scheme
* respect git export ignores
* avoid shlex.split on windows
* fix #218 - better handling of mercurial edge-cases with tag commits
  being considered as the tagged commit
* fix #223 - remove the dependency on the interal SetupttoolsVersion
  as it was removed after long-standing deprecation

v1.15.7
======

* Fix #174 with #207: Re-use samefile backport as developed in
  jaraco.windows, and only use the backport where samefile is
  not available.

v1.15.6
=======

* fix #171 by unpinning the py version to allow a fixed one to get installed

v1.15.5
=======

* fix #167 by correctly respecting preformatted version metadata
  from PKG-INFO/EGG-INFO

v1.15.4
=======

* fix issue #164: iterate all found entry points to avoid errors when pip remakes egg-info
* enhance self-use to enable pip install from github again

v1.15.3
=======

* bring back correctly getting our version in the own sdist, finalizes #114
* fix issue #150: strip local components of tags

v1.15.2
=======

* fix issue #128: return None when a scm specific parse fails in a worktree to ease parse reuse


v1.15.1
=======

* fix issue #126: the local part of any tags is discarded
  when guessing new versions
* minor performance optimization by doing fewer git calls
  in the usual cases


v1.15.0
=======

* more sophisticated ignoring of mercurial tag commits
  when considering distance in commits
  (thanks Petre Mierlutiu)
* fix issue #114: stop trying to be smart for the sdist
  and ensure its always correctly using itself
* update trove classifiers
* fix issue #84: document using the installed package metadata for sphinx
* fix issue #81: fail more gracious when git/hg are missing
* address issue #93: provide an experimental api to customize behaviour on shallow git repos
  a custom parse function may pick pre parse actions to do when using git


v1.14.1
=======

* fix #109: when detecting a dirty git workdir
            don't consider untracked file
            (this was a regression due to #86 in v1.13.1)
* consider the distance 0 when the git node is unknown
  (happens when you haven't committed anything)

v1.14.0
=======

* publish bdist_egg for python 2.6, 2.7 and 3.3-3.5
* fix issue #107 - dont use node if it is None

v1.13.1
=======

* fix issue #86 - detect dirty git workdir without tags

v1.13.0
=======

* fix regression caused by the fix of #101
  * assert types for version dumping
  * strictly pass all versions through parsed version metadata

v1.12.0
=======

* fix issue #97 - add support for mercurial plugins
* fix issue #101 - write version cache even for pretend version
  (thanks anarcat for reporting and fixing)

v1.11.1
========

* fix issue #88 - better docs for sphinx usage (thanks Jason)
* fix issue #89 - use normpath to deal with windows
  (thanks Te-jé Rodgers for reporting and fixing)

v1.11.0
=======

* always run tag_to_version so in order to handle prefixes on old setuptools
  (thanks to Brian May)
* drop support for python 3.2
* extend the error message on missing scm metadata
  (thanks Markus Unterwaditzer)
* fix bug when using callable version_scheme
  (thanks Esben Haabendal)

v1.10.1
=======

* fix issue #73 - in hg pre commit merge, consider parent1 instead of failing

v1.10.0
=======

* add support for overriding the version number via the
  environment variable SETUPTOOLS_SCM_PRETEND_VERSION

* fix issue #63 by adding the --match parameter to the git describe call
  and prepare the possibility of passing more options to scm backends

* fix issue #70 and #71 by introducing the parse keyword
  to specify custom scm parsing, its an expert feature,
  use with caution

  this change also introduces the setuptools_scm.parse_scm_fallback
  entrypoint which can be used to register custom archive fallbacks


v1.9.0
======

* Add :code:`relative_to` parameter to :code:`get_version` function;
  fixes #44 per #45.

v1.8.0
======

* fix issue with setuptools wrong version warnings being printed to standard
  out. User is informed now by distutils-warnings.
* restructure root finding, we now reliably ignore outer scm
  and prefer PKG-INFO over scm, fixes #43 and #45

v1.7.0
======

* correct the url to github
  thanks David Szotten
* enhance scm not found errors with a note on git tarballs
  thanks Markus
* add support for :code:`write_to_template`

v1.6.0
======

* bail out early if the scm is missing

  this brings issues with git tarballs and
  older devpi-client releases to light,
  before we would let the setup stay at version 0.0,
  now there is a ValueError

* properly raise errors on write_to misuse (thanks Te-jé Rodgers)

v1.5.5
======

* Fix bug on Python 2 on Windows when environment has unicode fields.

v1.5.4
======

* Fix bug on Python 2 when version is loaded from existing metadata.

v1.5.3
======

* #28: Fix decoding error when PKG-INFO contains non-ASCII.

v1.5.2
======

* add zip_safe flag

v1.5.1
======

* fix file access bug i missed in 1.5

v1.5.0
======

* moved setuptools integration related code to own file
* support storing version strings into a module/text file
  using the :code:`write_to` coniguration parameter

v1.4.0
======

* proper handling for sdist
* fix file-finder failure from windows
* resuffle docs

v1.3.0
======

* support setuptools easy_install egg creation details
  by hardwireing the version in the sdist

v1.2.0
======

* enhance self-use

v1.1.0
======

* enable self-use

v1.0.0
======

* documentation enhancements

v0.26
=====

* rename to setuptools_scm
* split into package, add lots of entry points for extension
* pluggable version schemes

v0.25
=====

* fix pep440 support
  this reshuffles the complete code for version guessing

v0.24
=====

* dont drop dirty flag on node finding
* fix distance for dirty flagged versions
* use dashes for time again,
  its normalisation with setuptools
* remove the own version attribute,
  it was too fragile to test for
* include file finding
* handle edge cases around dirty tagged versions

v0.23
=====

* windows compatibility fix (thanks stefan)
  drop samefile since its missing in
  some python2 versions on windows
* add tests to the source tarballs


v0.22
=====

* windows compatibility fix (thanks stefan)
  use samefile since it does path normalisation

v0.21
=====

* fix the own version attribute (thanks stefan)

v0.20
=====

* fix issue 11: always take git describe long format
  to avoid the source of the ambiguity
* fix issue 12: add a __version__ attribute via pkginfo

v0.19
=====

* configurable next version guessing
* fix distance guessing (thanks stefan)
