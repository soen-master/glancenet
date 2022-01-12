import sys
import torch
import logging
import os

from common.utils import setup_logging, initialize_seeds, set_environment_variables
from aicrowd.aicrowd_utils import is_on_aicrowd_server
from common.arguments import get_args
import models

torch.backends.cudnn.enabled = True
torch.backends.cudnn.benchmark = True


def main(_args):
    #
    # REMOVED AIRCROWD CHALLENGE HERE
    #

    # load the model associated with args.alg
    print("_Args.alg", _args.alg)
    model_cl = getattr(models, _args.alg)
    model = model_cl(_args) #return models.alg

    # load checkpoint
    if _args.ckpt_load:
        model.load_checkpoint(_args.ckpt_load, load_iternum=_args.ckpt_load_iternum, load_optim=_args.ckpt_load_optim)

    # run test or train
    if not _args.test:
        model.train()#track_changes=True)
    else:
        model.test()

    ### REMOVED AIRCROWD ###

if __name__ == "__main__":
    _args = get_args(sys.argv[1:])
    setup_logging(_args.verbose)
    initialize_seeds(_args.seed)

    # set the environment variables for dataset directory and name, and check if the root dataset directory exists.
    set_environment_variables(_args.dset_dir, _args.dset_name)
    assert os.path.exists(os.environ.get('DISENTANGLEMENT_LIB_DATA', '')), \
        'Root dataset directory does not exist at: \"{}\"'.format(_args.dset_dir)

    main(_args)
