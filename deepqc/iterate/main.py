import os
import sys
import numpy as np
try:
    import deepqc
except ImportError as e:
    sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../../")
from deepqc.utils import load_yaml
from deepqc.iterate.iterate import make_iterate


def main(*args, **kwargs):
    r"""
    Make a `Workflow` to do the iterative training procedure and run it.

    The parameters are the same as `make_iterate` but the jobs wil be run.
    If ``$workdir/RECORD`` exists, the procedure will try to restart.
    The procedure will be conducted in `workdir` for `n_iter` iterations.
    Each iteration of the procedure is done in sub-folder ``iter.XX``, 
    which further containes two sub-folders, ``00.scf`` and ``01.train``.

    Parameters
    ----------
    systems_train: str or list of str, optional
        System paths used as training set in the procedure. These paths 
        can refer to systems or a file that contains multiple system paths.
        Systems must be .xyz files or folders contains .npy files.
        If not given, use ``$share_folder/systems_train.raw`` as default.
    systems_test: str or list of str, optional
        System paths used as testing (or validation) set in the procedure. 
        The format is same as `systems_train`. If not given, use the last
        system in the training set as testing system.
    n_iter: int, optional
        The number of iterations to do. Default is 0.
    workdir: str, optional
        The working directory. Default is current directory (`.`).
    share_folder: str, optional
        The folder to store shared files in the iteration, including
        ``scf_input.yaml``, ``train_input.yaml``, and possibly files for
        initialization. Default is ``share``.
    scf_input: bool or str or dict, optional
        Arguments used to specify the SCF calculation. If given `None` or
        `False`, bypass the checking and use program default (unreliable). 
        Otherwise, the arguments would be saved as a YAML file at 
        ``$share_folder/scf_input.yaml`` and used for SCF calculation. 
        Default is `True`, which will check and use the existing file.
        If given a string of file path, copy the corresponding file into 
        target location. If given a dict, dump it into the target file.
    scf_machine: str or dict, optional
        Arguments used to specify the job settings of SCF calculation,
        including submitting method, resources, group size, etc..
        If given a string of file path, load that file as a dict using 
        YAML format. If not given, using program default setup.
    train_input: bool or str or dict, optional 
        Arguments used to specify the training of neural network. 
        It follows the same rule as `scf_input`, only that the target 
        location is ``$share_folder/train_input.yaml``.
    train_machine: str or dict, optional 
        Arguments used to specify the job settings of NN training. 
        It Follows the same rule as `scf_machine`, but without group.
    init_model: bool or str, optional 
        Decide whether to use an existing model as the starting point.
        If set to `False` (default), use `init_scf` and `init_train` 
        to run an extra initialization iteration in folder ``iter.init``. 
        If set to `True`, look for a model at ``$share_folder/init/model.pth``.
        If given a string of path, copy that file into target location.
    init_scf: bool or str or dict, optional 
        Similar to `scf_input` but used for init calculation. The target
        location is ``$share_folder/init_scf.yaml``. Defaults to True.
    init_train: bool or str or dict, optional 
        Similar to `train_input` but used for init calculation. The target
        location is ``$share_folder/init_train.yaml``. Defaults to True.
    cleanup: bool, optional 
        Whether to remove job files during calculation, 
        such as ``slurm-*.out`` and ``err``. Defaults to False.
    strict: bool, optional 
        Whether to allow additional arguments to be passed to task constructor,
        through `scf_machine` and `train_machine`. Defaults to True.

    Returns
    -------
    None
    
    Raises
    ------
    FileNotFoundError
        Raise an Error when the system or argument files are required but 
        not found in the share folder.
    """
    # pass all arguments to make_iterate and run it
    iterate = make_iterate(*args, **kwargs)
    if os.path.exists(iterate.record_file):
        iterate.restart()
    else:
        iterate.run()


if __name__ == "__main__":
    from deepqc.main import iter_cli as cli
    cli()