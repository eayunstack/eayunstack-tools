from eayunstack_tools import utils


def make(parser):
    '''EayunStack Management'''
    return utils.make_subcommand(parser, 'manage')
