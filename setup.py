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

    entry_points={
        'console_scripts': [
            'eayunstack = eayunstack_tools.main:main',
        ],
        'command': [
            'doctor = eayunstack_tools.doctor:make',
            'fuel = eayunstack_tools.fuel:make',
            'manage = eayunstack_tools.manage:make',
            'init = eayunstack_tools.init:make',
            'list = eayunstack_tools.list:make',
            'upgrade = eayunstack_tools.upgrade:make',
            'cleanup = eayunstack_tools.cleanup:make',
        ],
        'fuel_command': [
            'backup = eayunstack_tools.fuel.backup:make',
            'restore = eayunstack_tools.fuel.restore:make',
            'deployment_monitor_plugins = '
            'eayunstack_tools.fuel.deployment_monitor_plugins:make',
        ],
        'doctor_command': [
            'env = eayunstack_tools.doctor.env:make',
            'cls = eayunstack_tools.doctor.cls:make',
            'stack = eayunstack_tools.doctor.stack:make',
            'all = eayunstack_tools.doctor.all:make',
            'net = eayunstack_tools.doctor.net:make',
        ],
        'manage_command': [
            'volume = eayunstack_tools.manage.volume:make',
            'ami = eayunstack_tools.manage.ami:make',
            'instance = eayunstack_tools.manage.instance:make',
            'orphan = eayunstack_tools.manage.orphan:make',
        ],
        'upgrade_command': [
            'setup = eayunstack_tools.upgrade.setup:make',
            'go = eayunstack_tools.upgrade.go:make',
        ],
        'cleanup_command': [
            'orphan = eayunstack_tools.cleanup.orphan:make',
        ],
    },
)
