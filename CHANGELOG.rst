v0.25
======

* fix pep440 support
  this reshuffles the complete code for version guessing

v0.24
======

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
======

* fix the own version attribute (thanks stefan)

v0.20
======

* fix issue 11: always take git describe long format
  to avoid the source of the ambiguity
* fix issue 12: add a __version__ attribute via pkginfo

v0.19
=======

* configurable next version guessing
* fix distance guessing (thanks stefan)
