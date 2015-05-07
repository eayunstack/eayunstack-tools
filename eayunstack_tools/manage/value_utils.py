# get_volume of output

def get_value(info, key):
    for entry in info.split('\n'):
        if len(entry.split('|')) > 1:
            if entry.split('|')[1].strip() == key:
                return entry.split('|')[2].strip()
