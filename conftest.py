
def pytest_sessionstart():
    import hgdistver
    hgdistver.trace = hgdistver.trace_debug
