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
* introduce a internal config object to allow the configruation fo tag parsing and prefixes
  (thanks to @punkadiddle for introducing it and passing it trough)

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
* reintroduce manifest as the travis deploy cant use the file finder
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
* #214 - fix missuse in surogate-escape api
* add the node-and-timestamp local version sheme
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

* fix issue #164: iterate all found entry points to avoid erros when pip remakes egg-info
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
  and ensure its always correctly usign itself
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
  (happens when you haven't commited anything)

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
  * strictly pass all versions trough parsed version metadata

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

* fix isssue #63 by adding the --match parameter to the git describe call
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

* propperly raise errors on write_to missuse (thanks Te-jé Rodgers)

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

* propper handling for sdist
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
