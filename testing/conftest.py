import os
os.environ['SETUPTOOLS_SCM_DEBUG'] = '1'


def pytest_report_header():
    import pkg_resources
    version = pkg_resources.get_distribution('setuptools_scm').version
    return ['setuptools_scm version ' + version]
