setuptools_scm
===============

``setuptools_scm`` handles managing your Python package versions
in SCM metadata instead of declaring them as the version argument
or in a SCM managed file.

It also handles file finders for the supported SCMs.

.. image:: https://travis-ci.org/pypa/setuptools_scm.svg?branch=master
    :target: https://travis-ci.org/pypa/setuptools_scm

``setup.py`` usage
------------------

To use ``setuptools_scm`` just modify your project's ``setup.py`` file
like this:

* Add ``setuptools_scm`` to the ``setup_requires`` parameter.
* Add the ``use_scm_version`` parameter and set it to ``True``.

For example:

.. code:: python

    from setuptools import setup
    setup(
        ...,
        use_scm_version=True,
        setup_requires=['setuptools_scm'],
        ...,
    )

Arguments to ``get_version()`` (see below) may be passed as a dictionary to
``use_scm_version``. For example:

.. code:: python

    from setuptools import setup
    setup(
        ...,
        use_scm_version = {"root": "..", "relative_to": __file__},
        setup_requires=['setuptools_scm'],
        ...,
    )

Once configured, you can access the version number in your package via
``pkg_resources`` (`PEP-0396 <https://www.python.org/dev/peps/pep-0396>`_). For
example:

.. code:: python

   from pkg_resources import get_distribution, DistributionNotFound
   try:
       __version__ = get_distribution(__name__).version
   except DistributionNotFound:
       # package is not installed
       pass

You can also confirm the version number locally via ``setup.py``:

.. code-block:: shell

    $ python setup.py --version

.. note::

   If you see unusual version numbers for packages but ``python setup.py
   --version`` reports the expected version number, ensure ``[egg_info]`` is
   not defined in ``setup.cfg``.


``setup.cfg``
-------------

If using `setuptools 30.3.0
<https://setuptools.readthedocs.io/en/latest/setuptools.html#configuring-setup-using-setup-cfg-files>`_
or greater, you can store ``setup_requires`` configuration in ``setup.cfg``.
However, ``use_scm_version`` must still be placed in ``setup.py``. For example:

.. code:: python

    # setup.py
    from setuptools import setup
    setup(
        use_scm_version=True,
    )

.. code:: ini

    # setup.cfg
    [metadata]
    ...

    [options]
    setup_requires =
      setuptools_scm
    ...

.. important::

    Ensure neither the ``[metadata]`` ``version`` option nor the ``[egg_info]``
    section are defined, as these will interfere with ``setuptools_scm``.

You may also need to define a ``pyproject.toml`` file (`PEP-0518
<https://www.python.org/dev/peps/pep-0518>`_) to ensure you have the required
version of ``setuptools``:

.. code:: ini

    # pyproject.toml
    [build-system]
    requires = ["setuptools>=30.3.0", "wheel", "setuptools_scm"]

For more information, refer to the `setuptools issue #1002
<https://github.com/pypa/setuptools/issues/1002>`_.


Programmatic usage
------------------

In order to use ``setuptools_scm`` from code that is one directory deeper
than the project's root, you can use:

.. code:: python

    from setuptools_scm import get_version
    version = get_version(root='..', relative_to=__file__)

See `setup.py Usage`_ above for how to use this within ``setup.py``.


Usage from Sphinx
-----------------

It is discouraged to use ``setuptools_scm`` from Sphinx itself,
instead use ``pkg_resources`` after editable/real installation:

.. code:: python

    # contents of docs/conf.py
    from pkg_resources import get_distribution
    release = get_distribution('myproject').version
    # for example take major/minor
    version = '.'.join(release.split('.')[:2])

The underlying reason is, that services like *Read the Docs* sometimes change
the working directory for good reasons and using the installed metadata
prevents using needless volatile data there.

Notable Plugins
----------------

`setuptools_scm_git_archive <https://pypi.python.org/pypi/setuptools_scm_git_archive>`_
    Provides partial support for obtaining versions from git archives that
    belong to tagged versions. The only reason for not including it in
    ``setuptools_scm`` itself is Git/GitHub not supporting sufficient metadata
    for untagged/followup commits, which is preventing a consistent UX.


Default versioning scheme
--------------------------

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
    ``{tag}+dYYYMMMDD``
distance and not clean:
    ``{next_version}.dev{distance}+{scm letter}{revision hash}.dYYYMMMDD``

The next version is calculated by adding ``1`` to the last numeric component of
the tag.

For Git projects, the version relies on `git describe <https://git-scm.com/docs/git-describe>`_,
so you will see an additional ``g`` prepended to the ``{revision hash}``.

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
--------------------------------------------------

1. the SCM itself (git/hg)
2. ``.hg_archival`` files (mercurial archives)
3. ``PKG-INFO``

.. note::

    Git archives are not supported due to Git shortcomings


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

:write_to:
    A path to a file that gets replaced with a file containing the current
    version. It is ideal for creating a ``version.py`` file within the
    package, typically used to avoid using `pkg_resources.get_distribution`
    (which adds some overhead).

    .. warning::

      Only files with :code:`.py` and :code:`.txt` extensions have builtin
      templates, for other file types it is necessary to provide
      :code:`write_to_template`.

:write_to_template:
    A newstyle format string that is given the current version as
    the ``version`` keyword argument for formatting.

:relative_to:
    A file from which the root can be resolved.
    Typically called by a script or module that is not in the root of the
    repository to point ``setuptools_scm`` at the root of the repository by
    supplying ``__file__``.

:tag_regex:
    A Python regex string to extract the version part from any SCM tag.
    The regex needs to contain three named groups prefix, version and suffix,
    where ``version`` captures the actual version information.

    Defaults to the value of ``setuptools_scm.config.DEFAULT_TAG_REGEX``
    (see `config.py <src/setuptools_scm/config.py>`_).

:fallback_version:
    A version string that will be used if no other method for detecting the
    version worked (e.g., when using a tarball with no metadata).  If this is
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

To use ``setuptools_scm`` in other Python code you can use the ``get_version``
function:

.. code:: python

    from setuptools_scm import get_version
    my_version = get_version()

It optionally accepts the keys of the ``use_scm_version`` parameter as
keyword arguments.

Example configuration in ``setup.py`` format:

.. code:: python

    from setuptools import setup

    setup(
        use_scm_version={
            'write_to': 'version.txt',
            'tag_regex': r'^(?P<prefix>v)?(?P<version>[^\+]+)(?P<suffix>.*)?$',
        }
    )

Environment variables
---------------------

:SETUPTOOLS_SCM_PRETEND_VERSION:
    when defined and not empty,
    its used as the primary source for the version number
    in which case it will be a unparsed string

:SETUPTOOLS_SCM_DEBUG:
    when defined and not empty,
    a lot of debug information will be printed as part of ``setuptools_scm``
    operating

Extending setuptools_scm
------------------------

``setuptools_scm`` ships with a few ``setuptools`` entrypoints based hooks to
extend its default capabilities.

Adding a new SCM
~~~~~~~~~~~~~~~~

``setuptools_scm`` provides two entrypoints for adding new SCMs:

``setuptools_scm.parse_scm``
    A function used to parse the metadata of the current workdir
    using the name of the control directory/file of your SCM as the
    entrypoint's name. E.g. for the built-in entrypoint for git the
    entrypoint is named ``.git`` and references ``setuptools_scm.git:parse``

  The return value MUST be a ``setuptools.version.ScmVersion`` instance
  created by the function ``setuptools_scm.version:meta``.

``setuptools_scm.files_command``
  Either a string containing a shell command that prints all SCM managed
  files in its current working directory or a callable, that given a
  pathname will return that list.

  Also use then name of your SCM control directory as name of the entrypoint.

Version number construction
~~~~~~~~~~~~~~~~~~~~~~~~~~~

``setuptools_scm.version_scheme``
    Configures how the version number is constructed given a
    ``setuptools.version.ScmVersion`` instance and should return a string
    representing the version.

    Available implementations:

    :guess-next-dev: automatically guesses the next development version (default)
    :post-release: generates post release versions (adds :code:`postN`)

``setuptools_scm.local_scheme``
    Configures how the local part of a version is rendered given a
    ``setuptools.version.ScmVersion`` instance and should return a string
    representing the local version.

    Available implementations:

    :node-and-date: adds the node on dev versions and the date on dirty
                    workdir (default)
    :node-and-timestamp: like ``node-and-date`` but with a timestamp of
                         the form ``{:%Y%m%d%H%M%S}`` instead
    :dirty-tag: adds ``+dirty`` if the current workdir has changes


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


Note on testing non-installed versions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

While the general advice is to test against a installed version,
some environments require a test prior to install,

.. code::

  $ python setup.py egg_info
  $ PYTHONPATH=$PWD:$PWD/src pytest



Code of Conduct
---------------

Everyone interacting in the ``setuptools_scm`` project's codebases, issue
trackers, chat rooms, and mailing lists is expected to follow the
`PyPA Code of Conduct`_.

.. _PyPA Code of Conduct: https://www.pypa.io/en/latest/code-of-conduct/
