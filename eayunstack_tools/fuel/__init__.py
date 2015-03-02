from eayunstack_tools import utils


def make(parser):
    '''EayunStack Fuel Management'''
    return utils.make_subcommand(parser, 'fuel')
