from eayunstack_tools import utils


def make(parser):
    """Upgrade Management"""
    return utils.make_subcommand(parser, 'upgrade')
