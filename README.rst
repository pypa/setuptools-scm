setuptools_scm
==============

``setuptools_scm`` extracts Python package versions from ``git`` or
``hg`` metadata instead of declaring them as the version argument
or in a SCM managed file.

Additionally ``setuptools_scm`` provides setuptools with a list of
files that are managed by the SCM (i.e. it automatically adds all of
the SCM-managed files to the sdist). Unwanted files must be excluded
by discarding them via ``MANIFEST.in``.


.. image:: https://github.com/pypa/setuptools_scm/workflows/python%20tests+artifacts+release/badge.svg
    :target: https://github.com/pypa/setuptools_scm/actions

.. image:: https://tidelift.com/badges/package/pypi/setuptools-scm
   :target: https://tidelift.com/subscription/pkg/pypi-setuptools-scm?utm_source=pypi-setuptools-scm&utm_medium=readme


``pyproject.toml`` usage
------------------------

The preferred way to configure ``setuptools_scm`` is to author
settings in a ``tool.setuptools_scm`` section of ``pyproject.toml``.

This feature requires Setuptools 42 or later, released in Nov, 2019.
If your project needs to support build from sdist on older versions
of Setuptools, you will need to also implement the ``setup.py usage``
for those legacy environments.

First, ensure that ``setuptools_scm`` is present during the project's
built step by specifying it as one of the build requirements.

.. code:: toml

    # pyproject.toml
    [build-system]
    requires = ["setuptools>=45", "setuptools_scm[toml]>=6.2"]

That will be sufficient to require ``setuptools_scm`` for projects
that support PEP 518 (`pip <https://pypi.org/project/pip>`_ and
`pep517 <https://pypi.org/project/pep517/>`_). Many tools,
especially those that invoke ``setup.py`` for any reason, may
continue to rely on ``setup_requires``. For maximum compatibility
with those uses, consider also including a ``setup_requires`` directive
(described below in ``setup.py usage`` and ``setup.cfg``).

To enable version inference, you need to set the version
dynamically in the ``project`` section of ``pyproject.toml``:

.. code:: toml

    # pyproject.toml
    [project]
    # version = "0.0.1"  # Remove any existing version parameter.
    dynamic = ["version"]

Then add this section to your ``pyproject.toml``:

.. code:: toml

    # pyproject.toml
    [tool.setuptools_scm]

Including this section is comparable to supplying
``use_scm_version=True`` in ``setup.py``. Additionally,
include arbitrary keyword arguments in that section
to be supplied to ``get_version()``. For example:

.. code:: toml

    # pyproject.toml
    [tool.setuptools_scm]
    version_file = "pkg/_version.py"

Where ``pkg`` is the name of your package.

If you need to confirm which version string is being generated
or debug the configuration, you can install
`setuptools-scm <https://github.com/pypa/setuptools_scm>`_
directly in your working environment and run:

.. code-block:: shell

    $ python -m setuptools_scm

    # To explore other options, try:
    $ python -m setuptools_scm --help








Default versioning scheme
-------------------------

In the standard configuration ``setuptools_scm`` takes a look at three things:

1. latest tag (with a version number)
2. the distance to this tag (e.g. number of revisions since latest tag)
3. workdir state (e.g. uncommitted changes since latest tag)

and uses roughly the following logic to render the version:

no distance and clean:
    ``{tag}``
distance and clean:
    ``{next_version}.dev{distance}+{scm letter}{revision hash}``
no distance and not clean:
    ``{tag}+dYYYYMMDD``
distance and not clean:
    ``{next_version}.dev{distance}+{scm letter}{revision hash}.dYYYYMMDD``

The next version is calculated by adding ``1`` to the last numeric component of
the tag.

For Git projects, the version relies on `git describe <https://git-scm.com/docs/git-describe>`_,
so you will see an additional ``g`` prepended to the ``{revision hash}``.

.. note::

    According to `PEP 440 <https://peps.python.org/pep-0440/#local-version-identifiers>`_,
    if a version includes a local component, the package cannot be published to public
    package indexes like PyPI or TestPyPI. The disallowed version segments may
    be seen in auto-publishing workflows or when a configuration mistake is made.

    However, some package indexes such as devpi or other alternatives allow local
    versions. Local version identifiers must comply with `PEP 440`_.

Semantic Versioning (SemVer)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Due to the default behavior it's necessary to always include a
patch version (the ``3`` in ``1.2.3``), or else the automatic guessing
will increment the wrong part of the SemVer (e.g. tag ``2.0`` results in
``2.1.devX`` instead of ``2.0.1.devX``). So please make sure to tag
accordingly.

.. note::

    Future versions of ``setuptools_scm`` will switch to `SemVer
    <http://semver.org/>`_ by default hiding the the old behavior as an
    configurable option.


Builtin mechanisms for obtaining version numbers
------------------------------------------------

1. the SCM itself (git/hg)
2. ``.hg_archival`` files (mercurial archives)
3. ``.git_archival.txt`` files (git archives, see subsection below)
4. ``PKG-INFO``


Git archives
~~~~~~~~~~~~

Git archives are supported, but a few changes to your repository are required.

Create a ``.git_archival.txt`` file in the root directory of your repository,
and copy-paste this into it::

    node: $Format:%H$
    node-date: $Format:%cI$
    describe-name: $Format:%(describe:tags=true,match=*[0-9]*)$
    ref-names: $Format:%D$

Create the ``.gitattributes`` file in the root directory of your repository
if it doesn't already exist, and copy-paste this into it::

    .git_archival.txt  export-subst

Finally, don't forget to commit those two files::

    git add .git_archival.txt .gitattributes && git commit

Note that if you are creating a ``_version.py`` file, note that it should not
be kept in version control.


File finders hook makes most of MANIFEST.in unnecessary
-------------------------------------------------------

``setuptools_scm`` implements a `file_finders
<https://setuptools.pypa.io/en/latest/userguide/extension.html#adding-support-for-revision-control-systems>`_
entry point which returns all files tracked by your SCM. This eliminates
the need for a manually constructed ``MANIFEST.in`` in most cases where this
would be required when not using ``setuptools_scm``, namely:

* To ensure all relevant files are packaged when running the ``sdist`` command.

* When using `include_package_data <https://setuptools.readthedocs.io/en/latest/setuptools.html#including-data-files>`_
  to include package data as part of the ``build`` or ``bdist_wheel``.

``MANIFEST.in`` may still be used: anything defined there overrides the hook.
This is mostly useful to exclude files tracked in your SCM from packages,
although in principle it can be used to explicitly include non-tracked files
too.


Configuration parameters
------------------------

In order to configure the way ``use_scm_version`` works you can provide
a mapping with options instead of a boolean value.

The currently supported configuration keys are:

:root:
    Relative path to cwd, used for finding the SCM root; defaults to ``.``

:version_scheme:
    Configures how the local version number is constructed; either an
    entrypoint name or a callable.

:local_scheme:
    Configures how the local component of the version is constructed; either an
    entrypoint name or a callable.

:version_file:
    A path to a file that gets replaced with a file containing the current
    version. It is ideal for creating a ``_version.py`` file within the
    package, typically used to avoid using `pkg_resources.get_distribution`
    (which adds some overhead).

    .. warning::

      Only files with :code:`.py` and :code:`.txt` extensions have builtin
      templates, for other file types it is necessary to provide
      :code:`write_to_template`.

:version_file_template_template:
    A newstyle format string that is given the current version as
    the ``version`` keyword argument for formatting.

:write_to:
   (deprecated) legacy option to create a version file relative to the scm root
   its broken for usage from a sdist and fixing it would be a fatal breaking change,
   use ``version_file`` instead
:relative_to:
    A file from which the root can be resolved.
    Typically called by a script or module that is not in the root of the
    repository to point ``setuptools_scm`` at the root of the repository by
    supplying ``__file__``.

:tag_regex:
   A Python regex string to extract the version part from any SCM tag.
    The regex needs to contain either a single match group, or a group
    named ``version``, that captures the actual version information.

    Defaults to the value of ``setuptools_scm.config.DEFAULT_TAG_REGEX``
    (see `_config.py <src/setuptools_scm/_config.py>`_).

:parentdir_prefix_version:
    If the normal methods for detecting the version (SCM version,
    sdist metadata) fail, and the parent directory name starts with
    ``parentdir_prefix_version``, then this prefix is stripped and the rest of
    the parent directory name is matched with ``tag_regex`` to get a version
    string.  If this parameter is unset (the default), then this fallback is
    not used.

    This is intended to cover GitHub's "release tarballs", which extract into
    directories named ``projectname-tag/`` (in which case
    ``parentdir_prefix_version`` can be set e.g. to ``projectname-``).

:fallback_version:
    A version string that will be used if no other method for detecting the
    version worked (e.g., when using a tarball with no metadata). If this is
    unset (the default), setuptools_scm will error if it fails to detect the
    version.

:parse:
    A function that will be used instead of the discovered SCM for parsing the
    version.
    Use with caution, this is a function for advanced use, and you should be
    familiar with the ``setuptools_scm`` internals to use it.

:git_describe_command:
    This command will be used instead the default ``git describe`` command.
    Use with caution, this is a function for advanced use, and you should be
    familiar with the ``setuptools_scm`` internals to use it.

    Defaults to the value set by ``setuptools_scm.git.DEFAULT_DESCRIBE``
    (see `git.py <src/setuptools_scm/git.py>`_).

:normalize:
    A boolean flag indicating if the version string should be normalized.
    Defaults to ``True``. Setting this to ``False`` is equivalent to setting
    ``version_cls`` to ``setuptools_scm.version.NonNormalizedVersion``

:version_cls:
    An optional class used to parse, verify and possibly normalize the version
    string. Its constructor should receive a single string argument, and its
    ``str`` should return the normalized version string to use.
    This option can also receive a class qualified name as a string.

    This defaults to ``packaging.version.Version`` if available. If
    ``packaging`` is not installed, ``pkg_resources.packaging.version.Version``
    is used. Note that it is known to modify git release candidate schemes.

    The ``setuptools_scm.NonNormalizedVersion`` convenience class is
    provided to disable the normalization step done by
    ``packaging.version.Version``. If this is used while ``setuptools_scm``
    is integrated in a setuptools packaging process, the non-normalized
    version number will appear in all files (see ``write_to``) BUT note
    that setuptools will still normalize it to create the final distribution,
    so as to stay compliant with the python packaging standards.

To use ``setuptools_scm`` in other Python code you can use the ``get_version``
function:

.. code:: python

    from setuptools_scm import get_version
    my_version = get_version()

It optionally accepts the keys of the ``use_scm_version`` parameter as
keyword arguments.







Importing in ``setup.py``
~~~~~~~~~~~~~~~~~~~~~~~~~

To support usage in ``setup.py`` passing a callable into ``use_scm_version``
is supported.

Within that callable, ``setuptools_scm`` is available for import.
The callable must return the configuration.

.. code:: python

    # content of setup.py
    import setuptools

    def myversion():
        from setuptools_scm.version import get_local_dirty_tag
        def clean_scheme(version):
            return get_local_dirty_tag(version) if version.dirty else '+clean'

        return {'local_scheme': clean_scheme}

    setup(
        ...,
        use_scm_version=myversion,
        ...
    )


Interaction with Enterprise Distributions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Some enterprise distributions like RHEL7 and others
ship rather old setuptools versions due to various release management details.

In those case its typically possible to build by using a sdist against ``setuptools_scm<2.0``.
As those old setuptools versions lack sensible types for versions,
modern setuptools_scm is unable to support them sensibly.

In case the project you need to build can not be patched to either use old setuptools_scm,
its still possible to install a more recent version of setuptools in order to handle the build
and/or install the package by using wheels or eggs.


Code of Conduct
---------------

Everyone interacting in the ``setuptools_scm`` project's codebases, issue
trackers, chat rooms, and mailing lists is expected to follow the
`PSF Code of Conduct`_.

.. _PSF Code of Conduct: https://github.com/pypa/.github/blob/main/CODE_OF_CONDUCT.md


Security Contact
================

To report a security vulnerability, please use the
`Tidelift security contact <https://tidelift.com/security>`_.
Tidelift will coordinate the fix and disclosure.
