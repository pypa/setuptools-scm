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




Interaction with Enterprise Distributions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Some enterprise distributions like RHEL7 and others
ship rather old setuptools versions due to various release management details.

In those case its typically possible to build by using a sdist against ``setuptools_scm<2.0``.
As those old setuptools versions lack sensible types for versions,
modern setuptools_scm is unable to support them sensibly.

Its strongly recommended to build a wheel artifact using modern python and setuptools,
then installing the artifact instead of trying to run against old setuptools versions.


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
