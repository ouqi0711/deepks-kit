import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from time import time


DEVICE = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")


def calc_force(ene, eig, gvx):
    [gev] = torch.autograd.grad(ene, eig, 
                                grad_outputs=torch.ones_like(ene),
                                retain_graph=True, create_graph=True, only_inputs=True)
    # minus sign as froce = - grad_x E
    force = - torch.einsum("...bxap,...ap->...bx", gvx, gev)
    return force


def make_evaluator(force_factor=0, loss_fn=nn.MSELoss(), device=DEVICE):
    # make evaluator a closure to save parameters
    def evaluator(model, sample):
        # allocate data first
        e_label, eig, *force_sample = [d.to(device, non_blocking=True) for d in sample]
        if force_factor > 0:
            eig.requires_grad_(True)
        # begin the calculation
        e_pred = model(eig)
        loss = loss_fn(e_pred, e_label)
        # optional force calculation
        if force_factor > 0:
            f_label, gvx = force_sample
            f_pred = calc_force(e_pred, eig, gvx)
            loss = loss + force_factor * loss_fn(f_pred, f_label)
        return loss
    # return the closure
    return evaluator


def preprocess(model, g_reader, 
                preshift=True, prescale=False, prescale_sqrt=False, prescale_clip=0,
                prefit=True, prefit_ridge=1, prefit_trainable=False):
    shift = model.input_shift.cpu().detach().numpy()
    scale = model.input_scale.cpu().detach().numpy()
    if preshift or prescale:
        davg, dstd = g_reader.compute_data_stat()
        if preshift: 
            shift = davg
        if prescale: 
            scale = dstd
            if prescale_sqrt: 
                scale = np.sqrt(scale)
            if prescale_clip: 
                scale = scale.clip(prescale_clip)
        model.set_normalization(shift, scale)
    if prefit:
        weight, bias = g_reader.compute_prefitting(shift=shift, scale=scale, ridge_alpha=prefit_ridge)
        model.set_prefitting(weight, bias, trainable=prefit_trainable)


def train(model, g_reader, n_epoch=1000, 
          test_reader=None, force_factor=0,
          start_lr=0.001, decay_steps=100, decay_rate=0.96, stop_lr=None,
          weight_decay=0.0, display_epoch=100, ckpt_file="model.pth", device=DEVICE):
    
    model = model.to(device)
    print("# working on device:", device)
    if test_reader is None:
        test_reader = g_reader
    optimizer = optim.Adam(model.parameters(), lr=start_lr, weight_decay=weight_decay)
    if stop_lr is not None:
        decay_rate = (stop_lr / start_lr) ** (1 / (n_epoch // decay_steps))
        print(f"# resetting decay_rate: {decay_rate:.4f} "
              + f"to satisfy stop_lr: {stop_lr:.2e}")
    scheduler = optim.lr_scheduler.StepLR(optimizer, decay_steps, decay_rate)
    evaluator = make_evaluator(force_factor, nn.MSELoss(), device)

    print("# epoch      trn_err   tst_err        lr  trn_time  tst_time ")
    tic = time()
    trn_loss = np.mean([evaluator(model, batch).item() 
                    for batch in g_reader.sample_all_batch()])
    tst_loss = np.mean([evaluator(model, batch).item() 
                    for batch in test_reader.sample_all_batch()])
    tst_time = time() - tic
    print(f"  {0:<8d}  {np.sqrt(trn_loss):>.2e}  {np.sqrt(tst_loss):>.2e}"
          f"  {start_lr:>.2e}  {0:>8.2f}  {tst_time:>8.2f}")

    for epoch in range(1, n_epoch+1):
        tic = time()
        loss_list = []
        for sample in g_reader:
            optimizer.zero_grad()
            loss = evaluator(model, sample)
            loss.backward()
            optimizer.step()
            loss_list.append(loss.item())
        scheduler.step()

        if epoch % display_epoch == 0:
            trn_loss = np.mean(loss_list)
            trn_time = time() - tic
            tic = time()
            tst_loss = np.mean([evaluator(model, batch).item() 
                            for batch in test_reader.sample_all_batch()])
            tst_time = time() - tic
            print(f"  {epoch:<8d}  {np.sqrt(trn_loss):>.2e}  {np.sqrt(tst_loss):>.2e}"
                  f"  {scheduler.get_last_lr()[0]:>.2e}  {trn_time:>8.2f}  {tst_time:8.2f}")
            if ckpt_file:
                model.save(ckpt_file)
    
    