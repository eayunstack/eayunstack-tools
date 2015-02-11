from setuptools import setup,find_packages
setup(
    name = "eayunstack-tools",
    version = "0.0.1",
    packages = find_packages('eayunstack_tools'),
    package_dir = {'':'eayunstack_tools'},
    author='eayun',
    author_email='eayunstack@eayun.com',
    description='Command Line Management Tools For EayunStack.',
    license='GPLv3',
    keywords='EayunStack',

    entry_points = {
        'command': [
            'doctor = doctor.doctor:make',
            'fuel = fuel.fuel:make',
            'manage = manage.manage:make',
        ],
        'fuel_command': [
            'backup = fuel.backup:make_backup',
            'restore = fuel.restore:make_restore',
        ],
        'doctor_command': [
            'ntp = doctor.ntp:make_ntp',
            'mysql = doctor.mysql:make_mysql',
            'nova = doctor.nova:make_nova',
        ],
        'manage_command': [
            'instance = manage.instance:make_instance',
            'volume = manage.volume:make_volume',
        ],
    },
)
