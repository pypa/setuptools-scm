setuptools_scm
===============

About
-----

:code:`setuptools_scm` is a simple utility for the ``setup_requires``
feature of setuptools for use in `Mercurial <http://mercurial.selenic.com/>`_
and `Git <http://git-scm.com/>`_ based projects.

It uses metadata from the SCM to generate the **version** of a project
and is able to list the files belonging to that project
(which makes the :code:`MANIFEST.in` file unnecessary in many cases).

It falls back to ``PKG-INFO``/``.hg_archival.txt`` when necessary.

Default behavior
----------------

In the standard configuration setuptools_scm takes a look at 3 things:

1. latest tag (with a version number)
2. the distance to this tag (e.g. number of revisions since latest tag)
3. workdir state (e.g. uncommitted changes since latest tag)

and uses roughly the following logic to render the version:

no distance and clean:
    :code:`{tag}`
distance and clean:
    :code:`{next_version}.dev{distance}+n{revision hash}`
no distance and not clean:
    :code:`{tag}+dYYYMMMDD`
distance and not clean:
    :code:`{next_version}.dev{distance}+n{revision hash}.dYYYMMMDD`

The next version is calculated by adding ``1`` to the last numeric component
of the tag.

Semantic Versioning (SemVer)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Due to the default behavior it's necessary to always include a
patch version (the ``3`` in ``1.2.3``), or else the automatic guessing
will increment the wrong part of the semver (e.g. tag ``2.0`` results in
``2.1.devX`` instead of ``2.0.1.devX``). So please make sure to tag
accordingly.

.. note::

    Future versions of setuptools_scm will switch to
    `SemVer <http://semver.org/>`_ by default hiding the the old behavior
    as an configurable option.

Setup.py usage
--------------

To use setuptools_scm simple modify your project's setup.py file like this:

1. Add the :code:`use_scm_version` parameter and set it to ``True``

2. Add :code:`'setuptools_scm'` to the :code:`setup_requires` parameter

   E.g.:
   
   .. code:: python
   
       from setuptools import setup
       setup(
           ...,
           use_scm_version=True,
           setup_requires=['setuptools_scm'],
           ...,
       )
   
In order to configure the way ``use_scm_version`` works you can provide
a mapping with options instead of simple boolean value.

The Currently supported configuration keys are:

:version_scheme:
    configures how the local version number is constructed.
    either an entrypoint name or a callable

:local_scheme:
    configures how the local component of the version is constructed
    either an entrypoint name or a callable

To use setuptools_scm in other Python code you can use the
``get_version`` function:

.. code:: python

    from setuptools_scm import get_version
    my_version = get_version()

It optionally accepts the keys of the ``use_scm_version`` parameter as
keyword arguments.

Extending setuptools_scm
------------------------

setuptools_scm ships with a few setuptools entrypoints based hooks to extend
its default capabilities.

Adding a new SCM
~~~~~~~~~~~~~~~~

setuptools_scm provides 2 entrypoints for adding new SCMs

``setuptools_scm.parse_scm``
    A function used to parse the metadata of the current workdir
    using the name of the control directory/file of your SCM as the
    entrypoint's name. E.g. for the built-in entrypoint for git the
    entrypoint is named :code:`.git` and references
    :code:`'setuptools_scm.git:parse'`.

    The return value MUST be a :code:`setuptools.version.ScmVersion` instance
    created by the function :code:`setuptools_scm.version:meta`.

``setuptools_scm.files_command``
    Either a string containing a shell command that prints all SCM managed
    files in its current working directory or a callable, that given a
    pathname will return that list.

    Also use then name of your SCM control directory as name of the entrypoint.

Version number construction
~~~~~~~~~~~~~~~~~~~~~~~~~~~

``setuptools_scm.version_scheme``
    Configures how the version number is constructed given a
    :code:`setuptools.version.ScmVersion` instance and should return a string
    representing the version.

    Available implementations:

    :guess-next-dev: automatically guesses the next development version (default)
    :post-release: generates post release versions (adds :code:`postN`)

``setuptools_scm.local_scheme``
    Configures how the local part of a version is rendered given a
    :code:`setuptools.version.ScmVersion` instance and should return a string
    representing the local version.

    Available implementations:

    :node-and-date: adds the node on dev versions and the date on dirty
                    workdir (default)
    :dirty-tag: adds :code:`+dirty` if the current workdir has changes
