Simplify release tag creation to use a single ``createRelease`` API call instead of separate ``createTag``/``createRef``/``createRelease`` calls, avoiding dangling tag objects on partial failures.
