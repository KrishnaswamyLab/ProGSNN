from argparse import ArgumentParser
import datetime
import os
import numpy as np

import torch
import torch.utils.data
from torch import nn
from torch.nn import functional as F
import pickle
import pytorch_lightning as pl
from pytorch_lightning.loggers import WandbLogger
from pytorch_lightning.callbacks.early_stopping import EarlyStopping
from pytorch_lightning.loggers import TensorBoardLogger
from pathlib import Path
from atom3d.util.metrics import auroc
from gsae_model import GSAE
from progsnn import ProGSNN
from torch_geometric.loader import DataLoader
from torchvision import transforms
from atom3d.datasets import LMDBDataset
from de_shaw_Dataset import DEShaw, Scattering


if __name__ == '__main__':
    # torch.cuda.is_available()
    # import pdb; pdb.set_trace()
    parser = ArgumentParser()

    parser.add_argument('--dataset', default='deshaw', type=str)

    parser.add_argument('--input_dim', default=None, type=int)
    parser.add_argument('--latent_dim', default=100, type=int)
    parser.add_argument('--hidden_dim', default=200, type=int)
    parser.add_argument('--embedding_dim', default=80, type=int)
    parser.add_argument('--lr', default=0.001, type=float)

    parser.add_argument('--alpha', default=0.5, type=float)
    parser.add_argument('--beta', default=0.0005, type=float)
    parser.add_argument('--n_epochs', default=10, type=int)
    parser.add_argument('--len_epoch', default=None)
    parser.add_argument('--probs', default=0.2)
    parser.add_argument('--nhead', default=1)
    parser.add_argument('--layers', default=1)
    parser.add_argument('--task', default='bin_class')
    parser.add_argument('--batch_size', default=1, type=int)
    parser.add_argument('--n_gpus', default=1, type=int)
    parser.add_argument('--save_dir', default='train_logs/', type=str)

    # add args from trainer
    # parser = pl.Trainer.add_argparse_args(parser)
    # parse params 
    args = parser.parse_args()


    # full_dataset = DEShaw('graphs/total_graphs.pkl')
    with open('data_msp.pk', 'rb') as file:
        full_dataset =  pickle.load(file)
    
    # full_dataset = LMDBDataset('data/msp/raw/MSP/data/')
    # import pdb; pdb.set_trace()
    # full_dataset = [x for x in full_dataset if x.num_nodes < 1000]
    # print(len(full_dataset))
    #Convert the list of 0s and 1s target strings to integers and a torch tensor
    for data in full_dataset:
        y = torch.tensor([int(label) for label in data.y]).float()
        data.y = y
    
    # import pdb; pdb.set_trace()
    train_size = int(0.8 * len(full_dataset))
    val_size = len(full_dataset) - train_size
    train_set, val_set = torch.utils.data.random_split(full_dataset, [train_size, val_size])
    # print(len(full_dataset))
    # import pdb; pdb.set_trace()
    # train loader
    train_loader = DataLoader(train_set, batch_size=1)
    # valid loader 
    valid_loader = DataLoader(val_set, batch_size=1)
    # full_loader = DataLoader(full_dataset,
    #                          batch_size=args.batch_size,
    #                          shuffle=False,
    #                          num_workers=15)

    # logger
    # import pdb; pdb.set_trace()
    now = datetime.datetime.now()
    date_suffix = now.strftime("%Y-%m-%d-%M")
    save_dir =  args.save_dir + 'progsnn_logs_run_{}_{}/'.format(args.dataset,date_suffix)

    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    
    wandb_logger = WandbLogger(name='run_progsnn',
                                project='progsnn', 
                                log_model=True,
                                save_dir=save_dir)
    
    wandb_logger.log_hyperparams(args)
    wandb_logger.experiment.log({"logging timestamp":date_suffix})

    # print(train_loader)
    # print([item for item in full_dataset])
    # early stopping 
    # early_stop_callback = EarlyStopping(
    #         monitor='train_loss',
    #         min_delta=0.00,
    #         patience=5,
    #         verbose=True,
    #         mode='min'
    #         )
    # print(len(val_set))
    # args.input_dim = len(train_set)
    # print()
    args.input_dim = train_set[0].x.shape[-1]
    # args.input_dim = 20
    # print(train_set[0].x.shape[-1])

    # print(full_dataset[0][0].shape)
    # args.prot_graph_size = 1928
    args.prot_graph_size = max(
            [item.edge_index.shape[1] for item in full_dataset])
    args.len_epoch = len(train_loader)
    # init module
    model = ProGSNN(args)
    # # model.half()
    # print("Training model..")
    # # most basic trainer, uses good defaults
    # trainer = pl.Trainer(
    #                     max_epochs=args.n_epochs,
    #                     devices = "auto",
    #                     accelerator="gpu",
    #                     callbacks=[early_stop_callback],
    #                     logger = wandb_logger
    #                     )
    # trainer.fit(model=model,
    #             train_dataloaders=train_loader,
    #             #val_dataloaders=valid_loader,
    #             )

    # model = model.cpu()
    # model.dev_type = 'cpu'
    # print('saving model')
    # torch.save(model.state_dict(), "model_MSP.npy")
    trained_weights = torch.load('model_MSP.npy')
    model.load_state_dict(trained_weights)
    model = model.eval()


    # get test set prediction
    test_targets = np.array([data.y for data in val_set])
    test_predictions = []

    with torch.no_grad():
        for x in valid_loader:
            print("Looping through test set..")
            y_hat = model(x)[0]
            test_predictions.append(y_hat)


    test_predictions = torch.cat(test_predictions, dim=0)
    #Apply sigmoid or softmax to the predictions
    print("Test predictions: ")
    print(test_predictions)
    test_predictions = torch.softmax(test_predictions)
    print('test predictions shape')
    print(test_predictions.shape)
    print("Saving test predictions..")
    with open('test_preds.pkl', 'wb') as file:
        pickle.dump(test_predictions, file)
    # test_auroc = auroc(test_targets, test_predictions)
    # wandb_logger.log_metrics({'test_auroc': test_auroc})    






    # model = model.cpu()
    # model.dev_type = 'cpu'
    # print('saving model')
    # torch.save(model.state_dict(), save_dir + "model.npy")
    

    # residual_attention = []
    # embeddings = []
    # print(len(full_dataset))
    # with torch.no_grad():
    #     loss = model.get_loss_list()
    #     for batch in full_loader:
    #         y_pred, z_rep, coeffs, coeffs_recon, attention_maps, att_maps_res = model(batch)
    #         # att_maps = []
    #         # print(len(att_maps_res))
    #         print(att_maps_res[0].shape)
    #         # print(att_maps_res[0].shape)
    #         # for i in range(len(att_maps_res)):
    #         #     #loops over 3 layers of attention and hence we get 3 attention maps: 1 for each layer

    #         #     att_maps.append(att_maps_res[i].mean(dim = (0,1))) 
    #         # print(att_maps_res[0].shape)
    #         # print(len(att_maps))
    #         # print(att_maps[5].shape)
    #         # print(attention_maps[0].shape)
    #         residual_attention.append(att_maps_res[0])
    #         # print(residual_attention[0][0].shape)
    #         # x = np.vstack(residual_attention)
    #         # print(x.shape)
    #         # print(len(residual_attention))
    #         embeddings.append(z_rep)

    # print('saving reconstruction loss')
    # loss = np.array(loss)
    # np.save(save_dir + "reg_loss_list.npy", loss)
    
    # print('saving attention map')
    # # residual_attention = np.stack(residual_attention)
    # # np.save(save_dir + "attention_maps.npy", residual_attention)
    # with open('attention.pkl', 'wb') as file:
    #     pickle.dump(residual_attention, file)

    
    # print('saving embeddings')
    # embeddings = np.array(embeddings)
    # np.save(save_dir + "embeddings.npy", embeddings)  

    



    # EVALUATION ON TEST SET 
    # energy pred mse

    #print("getting test set predictions")
    #with torch.no_grad():
    #    x_recon_test = model(test_tup[0])[0]
    #    y_pred_test = model.predict_from_data(test_tup[0])


    # print("adj type: {}".format(test_tup[1].flatten().numpy()))
    # print("adj_hat type: {}".format(adj_hat_test.flatten().detach().numpy()))

    #recon_test_val = nn.MSELoss()(x_recon_test.flatten(), test_tup[0].flatten())
    #pred_test_val = nn.MSELoss()(y_pred_test.flatten(), test_tup[-1].flatten())

    #print("logging test set metrics")
    # wandb_logger.log_metrics({'test_recon_MSE':recon_test_val,
    #                             'test_pred_MSE': pred_test_val})


    #print("gathering eval subsets")
    #eval_tup_list = [eval_metrics.compute_subsample([test_embed, test_tup[-1]], 10000)[0] for i in range(8)]
    # trainer.test()
    #print("getting smoothness vals")
    #embed_eval_array= np.expand_dims(np.array([x[0].numpy() for x in eval_tup_list]),0)
    #energy_eval_array= np.array([x[1].numpy() for x in eval_tup_list])

    #print('embed_eval_array shape: {}'.format(embed_eval_array.shape))
    #print('energy_eval_array shape: {}'.format(energy_eval_array.shape))
    
    # energy_smoothness = eval_metrics.eval_over_replicates(embed_eval_array,
    #                                                         energy_eval_array,
    #                                             eval_metrics.get_smoothnes_kNN,
    #                                             [5, 10])[0]

    # energy_smoothness = eval_metrics.format_metric(energy_smoothness)


    # wandb_logger.log_metrics({'e_smooth_k5_mean':energy_smoothness[0][0],
    #                             'e_smooth_k10_mean': energy_smoothness[0][1],
    #                             'e_smooth_k5_std': energy_smoothness[1][0],
    #                             'e_smooth_k10_std': energy_smoothness[1][1]})