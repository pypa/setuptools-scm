



def _archival_to_version(data):
    "stolen logic from mercurials setup.py"
    if 'tag' in data:
        return data['tag']
    elif 'latesttag' in data:
        return '%(latesttag)s.dev%(latesttagdistance)s-%(node).12s' % data
    else:
        return data.get('node', '')[:12]

def data_from_archival(path):
    import email
    data = email.message_from_file(open(str(path)))
    return dict(data.items())


