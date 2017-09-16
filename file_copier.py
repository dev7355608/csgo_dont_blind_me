from os import name as os_name
from os.path import isdir, join, isfile
from shutil import copy


def copy_config_or_print_message(settings: dict, application_path: str):
    success = False
    destination = get_path_for_os(settings)
    file_name = settings.get('config_file_name')
    file_path = join(application_path, file_name)
    if isdir(destination) and isfile(file_path):
        copy(file_path, destination)
        success = True
    print_message(success, file_name)


def get_path_for_os(settings: dict):
    if os_name == 'nt':
        return settings.get('default_path_windows')
    elif os_name == 'posix':
        return settings.get('default_path_linux')
    return None


def print_message(success: bool, file_name: str):
    if success:
        print('Success copying {} into csgo\cfg directory!'.format(file_name))
    else:
        print('''Failed to copy cfg file. You have to copy {} into
        ...\\Steam\\userdata\\________\\730\\local\\cfg, or
        ...\\Steam\\steamapps\\common\\Counter-Strike Global Offensive\\csgo\\cfg!
        '''.format(file_name))
