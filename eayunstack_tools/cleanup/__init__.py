from eayunstack_tools import utils


def make(parser):
    '''EayunStack Cleanup Resources'''
    return utils.make_subcommand(parser, 'cleanup')
