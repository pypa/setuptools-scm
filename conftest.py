
def pytest_sessionstart():
    import setuptools_scm
    setuptools_scm.trace = setuptools_scm.trace_debug
