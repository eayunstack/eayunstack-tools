from eayunstack_tools import utils


def make(parser):
    '''EayunStack Doctor'''
    return utils.make_subcommand(parser, 'doctor')
