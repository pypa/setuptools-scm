


def data_from_archival(path):
    import email
    data = email.message_from_file(open(str(path)))
    return dict(data.items())
