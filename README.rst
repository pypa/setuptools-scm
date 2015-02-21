setuptools_scm
===============

About
~~~~~~

:code:`setuptools_scm` is a simple setup_requires utility for use
in mercurial and git based projects.

It uses metadata from the scm to generate the **version** of a project
and to list the files belonging to that project
(makes MANIFEST.in unnecessary in many cases).

It falls back to PKG-INFO/.hg_archival.txt when necessary/

Standard Version Generation
~~~~~~~~~~~~~~~~~~~~~~~~~~~

In the standard configurations setuptools_scm takes a look at 3 things

1. latest tag
2. the distance to this tag
3. workdir state

and uses roughly the following logic to render the version

not distance and clean
    :code:`{tag}`
distance and clean
    :code:`{next_version}.dev{distance}+n{revision hash}`
not distance and not clean
    :code:`{tag}+dYYYMMMDD`
distance and not clean
    :code:`{next_version}.dev{distance}+n{revision hash}.dYYYMMMDD`


The next version is calculated by adding 1 to the last numeric component
of the tag.

Using Semver
~~~~~~~~~~~~

Due to the default behaviour its necessary to always include a
patch version, else the automatic guessing will increment the wrong part
of the semver. (i.e. tag 2.0 results in 2.1.devX instead of 2.0.1.devX)


Future versions of setuptools_scm will switch to semver by default,
hiding the the old behaviour as configurable option


Setup.py
~~~~~~~~

.. code:: python

    from setuptools import setup
    setup(
        ...,
        use_scm_version=True,
        setup_requires=['setuptools_scm'],
        ...,
    )

In order to configure the way use_scm_version works
you an provide a mapping with options instead of simple truth value.


currently supported configuration keys are:

:version_scheme:
    configures how the local version number is constructed
    either a entrypoint name or a callable
:local_scheme:
    configures how the local component of the version is constructed
    either a entrypoint name or a callable

To use setuptools_scm in other python code
you can use the get_version function.

.. code:: python

    from setuptools_scm import get_version
    my_version = get_version()

It suports the keys of the setup.py use_scm_version
flag as keyword arguments.


extending setuptools_scm
------------------------

adding new scm
~~~~~~~~~~~~~~

setuptools_scm provides 2 entrypoints for adding new scms

**setuptools_scm.parse_scm**
    a function used to parse the metadata of the current workdir
    use the name of the control directoy/file of your scm as name

    the return value MUST be a ScmVersion instance created by the
    function :code:`setuptools_scm.version:meta`

**setuptools_scm.files_command**
    either a string containing a shell command
    that prints all scm managed files in its current working directory
    or a callable, that given a pathname will return

    also use then name of your scm control directory as name of the entrypoint


version number constructions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**setuptools_scm.version_scheme**
    configures how the version number is constructed

    availiable implementations:

    :guess-next-dev: automatically guess the next development version
    :post-release: generate post release versions

**setuptools_scm.local_scheme**
    configures how the local part of a version is rendered

    availiable implementations:

    :node-and-date: adds the node on dev versions and the date on dirty workdir
    :dirty-tag: adds :code:`+dirty` if the current workdir has changes
