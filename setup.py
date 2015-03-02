from setuptools import setup, find_packages
setup(
    name="eayunstack-tools",
    version="0.0.1",
    packages=find_packages(),
    author='eayun',
    author_email='eayunstack@eayun.com',
    description='Command Line Management Tools For EayunStack.',
    license='GPLv3',
    keywords='EayunStack',

    entry_points = {
        'console_scripts': [
            'eayunstack-tools = eayunstack_tools.main:main',
        ],
        'command': [
            'doctor = eayunstack_tools.doctor:make',
            'fuel = eayunstack_tools.fuel:make',
            'manage = eayunstack_tools.manage:make',
        ],
        'fuel_command': [
            'backup = eayunstack_tools.fuel.backup:make',
            'restore = eayunstack_tools.fuel.restore:make',
        ],
        'doctor_command': [
            'all = eayunstack_tools.doctor.all:make',
            'ntp = eayunstack_tools.doctor.ntp:make',
            'mysql = eayunstack_tools.doctor.mysql:make',
            'rabbit = eayunstack_tools.doctor.rabbit:make',
            'keystone = eayunstack_tools.doctor.keystone:make',
            'glance = eayunstack_tools.doctor.glance:make',
            'neutron = eayunstack_tools.doctor.neutron:make',
            'nova = eayunstack_tools.doctor.nova:make',
            'cinder = eayunstack_tools.doctor.cinder:make',
            'ceph = eayunstack_tools.doctor.ceph:make',
            'ceilometer = eayunstack_tools.doctor.ceilometer:make',
        ],
        'manage_command': [
            'instance = eayunstack_tools.manage.instance:make',
            'volume = eayunstack_tools.manage.volume:make',
            'image = eayunstack_tools.manage.image:make',
            'ceilometer = eayunstack_tools.manage.ceilometer:make',
            'evacuation = eayunstack_tools.manage.evacuation:make',
        ],
    },
)
