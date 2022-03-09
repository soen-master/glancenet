import os.path
import torch
from torch import nn
import torch.optim as optim
from models.vae import VAE
from models.vae import VAEModel
from architectures import encoders, decoders
from common.ops import reparametrize
from common.utils import Accuracy_Loss
from common import constants as c
import torch.nn.functional as F
from common.utils import is_time_for

import numpy as np
import pandas as pd


class GrayVAE_Standard(VAE):
    """
    Graybox version of VAE, with standard implementation. The discussion on
    """

    def __init__(self, args):

        super().__init__(args)

        print('Initialized GrayVAE_Standard model')

        # checks
        assert self.num_classes is not None, 'please identify the number of classes for each label separated by comma'

        # encoder and decoder
        encoder_name = args.encoder[0]
        decoder_name = args.decoder[0]

        encoder = getattr(encoders, encoder_name)
        decoder = getattr(decoders, decoder_name)

        # number of channels
        image_channels = self.num_channels
        input_channels = image_channels
        decoder_input_channels = self.z_dim

        # model and optimizer
        self.model = VAEModel(encoder(self.z_dim, input_channels, self.image_size),
                               decoder(decoder_input_channels, self.num_channels, self.image_size),
                               ).to(self.device)
        self.optim_G = optim.Adam(self.model.parameters(), lr=self.lr_G, betas=(self.beta1, self.beta2))
        self.optim_G_mse = optim.Adam(self.model.encoder.parameters(), lr=self.lr_G, betas=(self.beta1, self.beta2))

        # update nets
        self.net_dict['G'] = self.model
        self.optim_dict['optim_G'] = self.optim_G

        self.setup_schedulers(args.lr_scheduler, args.lr_scheduler_args,
                              args.w_recon_scheduler, args.w_recon_scheduler_args)

        ## add binary classification layer
#        self.classification = nn.Linear(self.z_dim, 1, bias=False).to(self.device)
        self.classification = nn.Linear(self.z_dim, 2, bias=False).to(self.device) ### CHANGED OUT DIMENSION
        self.classification_epoch = args.classification_epoch

        self.class_G = optim.SGD(self.classification.parameters(), lr=0.01, momentum=0.9)

        self.label_weight = args.label_weight
        self.masking_fact = args.masking_fact
        self.show_loss = args.show_loss

        self.dataframe_dis = pd.DataFrame() #columns=self.evaluation_metric)
        self.dataframe_eval = pd.DataFrame()

        self.latent_loss = args.latent_loss

    def predict(self, **kwargs):
        """
        Predict the correct class for the input data.
        """
        input_x = kwargs['latent'].to(self.device)
        pred_raw = self.classification(input_x)
        pred = nn.Softmax(dim=1)(pred_raw)
        return  pred_raw, pred.to(self.device, dtype=torch.float32) #nn.Sigmoid()(self.classification(input_x).resize(len(input_x)))

    def vae_classification(self, losses, x_true1, label1, y_true1, examples, classification=False):

        mu, logvar = self.model.encode(x=x_true1,)

        z = reparametrize(mu, logvar)
        mu_processed = torch.tanh(mu/2)
        x_recon = self.model.decode(z=z,)

        # CHECKING THE CONSISTENCY
#        z_prediction = torch.zeros(size=(len(mu), self.z_dim))
 #       z_prediction[:, :label1.size(1)] = label1.detach()
  #      z_prediction[:, label1.size(1):] = mu[:, label1.size(1):].detach()

        prediction, forecast = self.predict(latent=mu_processed)
        rn_mask = (examples==1)
        n_passed = len(examples[rn_mask])

        if not classification:
            loss_fn_args = dict(x_recon=x_recon, x_true=x_true1, mu=mu, logvar=logvar, z=z)
            loss_dict = self.loss_fn(losses, reduce_rec=False, **loss_fn_args)
            losses.update(loss_dict)
#            losses.update({'total_vae': loss_dict['total_vae'].detach(), 'recon': loss_dict['recon'].detach(),
 #                          'kld': loss_dict['kld'].detach()})
            del loss_dict

            if n_passed > 0: # added the presence of only small labelled generative factors

                ## loss of categorical variables

                ## loss of continuous variables
                if self.latent_loss == 'MSE':
                    #TODO: PLACE ONEHOT ENCODING
                    loss_bin = nn.MSELoss(reduction='mean')( mu_processed[rn_mask][:, :label1.size(1)], 2*label1[rn_mask]-1  )

                    losses.update(true_values=self.label_weight * loss_bin)
                    losses[c.TOTAL_VAE] += self.label_weight * loss_bin

                elif self.latent_loss == 'BCE':

                    loss_bin = nn.BCELoss(reduction='mean')((1+mu_processed[rn_mask][:, :label1.size(1)])/2,
                                                             label1[rn_mask] )

                    losses.update(true_values=self.label_weight * loss_bin)
                    losses[c.TOTAL_VAE] += self.label_weight * loss_bin

                elif self.latent_loss == 'exact_BCE':
                    mu_processed = nn.Sigmoid()( mu/torch.sqrt(1+ torch.exp(logvar)) )
                    loss_bin = nn.BCELoss(reduction='mean')( mu_processed[rn_mask], label1[rn_mask] )

                    losses.update(true_values=self.label_weight * loss_bin)
                    losses[c.TOTAL_VAE] += self.label_weight * loss_bin

                else:
                    raise NotImplementedError('Not implemented loss.')

            else:
                losses.update(true_values=torch.tensor(-1))

        #            losses[c.TOTAL_VAE] += nn.MSELoss(reduction='mean')(mu[:, :label1.size(1)], label1).detach()

        if classification:
            #TODO: INSERT MORE OPTIONS ON HOW TRAINING METRICS AFFECT
            ## DISJOINT VERSION

            loss_fn_args = dict(x_recon=x_recon, x_true=x_true1, mu=mu, logvar=logvar, z=z)
            loss_dict = self.loss_fn(losses, reduce_rec=True, **loss_fn_args)
            loss_dict.update(true_values=torch.tensor(-1)) # nn.BCELoss(reduction='mean')((1+mu_processed[:,:label1.size(1)])/2, label1))
            loss_dict[c.TOTAL_VAE] += -1 #nn.BCELoss(reduction='mean')((1+z[:, :label1.size(1)])/2, label1)
            losses.update({'total_vae': loss_dict['total_vae'].detach(), 'recon': loss_dict['recon'].detach(),
                           'kld': loss_dict['kld'].detach(), 'true_values': loss_dict['true_values']})

            del loss_dict

            #TODO insert MSE Classification
            #TODO: insert the regression on the latents factor matching

            losses.update(prediction=nn.CrossEntropyLoss(reduction='mean')(prediction, y_true1) )

            ## INSERT DEVICE IN THE CREATION OF EACH TENSOR
            ### AVOID COPYING FROM CPU TO GPU AS MUCH AS POSSIBLE

        return losses, {'x_recon': x_recon, 'mu': mu, 'z': z, 'logvar': logvar, "prediction": prediction,
                        'forecast': forecast, 'n_passed': n_passed}

    def loss_fn(self, input_losses, classification=False, **kwargs):
        x_recon = kwargs['x_recon']
        x_true = kwargs['x_true']
        mu = kwargs['mu']
        logvar = kwargs['logvar']
        labels = kwargs['labels']
        y = kwargs['y']
        pred = kwargs['pred']
        examples = kwargs['examples']

        #        prediction z= kwargs["prediction"]

        bs = self.batch_size
        output_losses = dict()
        output_losses[c.TOTAL_VAE] = input_losses.get(c.TOTAL_VAE, 0)
        output_losses[c.RECON] = F.binary_cross_entropy(input=x_recon, target=x_true,
                                                            reduction='sum') / bs * self.w_recon
        output_losses[c.TOTAL_VAE] += output_losses[c.RECON]

        output_losses['kld'] = self._kld_loss_fn(mu, logvar)
        output_losses[c.TOTAL_VAE] += output_losses['kld']

        rn_mask = (examples == 1)
        n_passed = len(examples[rn_mask])

        if not classification and n_passed > 0:
            if self.latent_loss == 'MSE':
                mu_processed = torch.tanh(mu/2)
                loss_bin = nn.MSELoss(reduction='mean')(mu_processed[rn_mask][:, :labels.size(1)],
                                                        2 * labels[rn_mask] - 1)

                output_losses['true_values']=self.label_weight * loss_bin
                output_losses[c.TOTAL_VAE] += output_losses['true_values']

            elif self.latent_loss == 'BCE':
                mu_processed = torch.tanh(mu/2)
                loss_bin = nn.BCELoss(reduction='mean')((1 + mu_processed[rn_mask][:, :labels.size(1)]) / 2,
                                                        labels[rn_mask])

                output_losses['true_values'] =self.label_weight * loss_bin
                output_losses[c.TOTAL_VAE] += output_losses['true_values']

            elif self.latent_loss == 'exact_BCE':
                mu_processed = nn.Sigmoid()(mu / torch.sqrt(1 + torch.exp(logvar)))
                loss_bin = nn.BCELoss(reduction='mean')(mu_processed[rn_mask], labels[rn_mask])

                output_losses['true_values'] = self.label_weight * loss_bin
                output_losses[c.TOTAL_VAE] += output_losses['true_values']

            else:
                raise NotImplementedError('Not implemented loss.')

        elif classification:
            output_losses['true_values']=torch.tensor(-1)  # nn.BCELoss(reduction='mean')((1+mu_processed[:,:label1.size(1)])/2, label1))

            output_losses['prediction']=nn.CrossEntropyLoss(reduction='mean')(pred, y)
            output_losses[c.TOTAL_VAE] += output_losses['prediction']

        else:
            output_losses['true_values']=torch.tensor(-1)


        if c.FACTORVAE in self.loss_terms:
            from models.factorvae import factorvae_loss_fn
            output_losses['vae_tc_factor'], output_losses['discriminator_tc'] = factorvae_loss_fn(
                self.w_tc, self.model, self.PermD, self.optim_PermD, self.ones, self.zeros, **kwargs)
            output_losses[c.TOTAL_VAE] += output_losses['vae_tc_factor']

        if c.DIPVAEI in self.loss_terms:
            from models.dipvae import dipvaei_loss_fn
            output_losses['vae_dipi'] = dipvaei_loss_fn(self.w_dipvae, self.lambda_od, self.lambda_d, **kwargs)
            output_losses[c.TOTAL_VAE] += output_losses['vae_dipi']

        if c.DIPVAEII in self.loss_terms:
            from models.dipvae import dipvaeii_loss_fn
            output_losses['vae_dipii'] = dipvaeii_loss_fn(self.w_dipvae, self.lambda_od, self.lambda_d, **kwargs)
            output_losses[c.TOTAL_VAE] += output_losses['vae_dipii']

        if c.BetaTCVAE in self.loss_terms:
            from models.betatcvae import betatcvae_loss_fn
            output_losses['vae_betatc'] = betatcvae_loss_fn(self.w_tc, **kwargs)
            output_losses[c.TOTAL_VAE] += output_losses['vae_betatc']

        if c.INFOVAE in self.loss_terms:
            from models.infovae import infovae_loss_fn
            output_losses['vae_mmd'] = infovae_loss_fn(self.w_infovae, self.z_dim, self.device, **kwargs)
            output_losses[c.TOTAL_VAE] += output_losses['vae_mmd']

        # if "classification" in self.loss_terms:
        #   pass
        #   pass

        return output_losses

    def train(self, **kwargs):

        if 'output'  in kwargs.keys():
            out_path = kwargs['output']
            track_changes=True
            self.out_path = out_path #TODO: Not happy with this thing

        else: track_changes=False;

        if track_changes:
            print("## Initializing Train indexes")
            print("::path chosen ->",out_path+"/train_runs")


        epoch = 0
        while not self.training_complete():
            epoch += 1
            self.net_mode(train=True)
            vae_loss_sum = 0
            # add the classification layer #
            if epoch>self.classification_epoch:
                print("## STARTING CLASSIFICATION ##")
                start_classification = True
            else: start_classification = False

            for internal_iter, (x_true1, label1, y_true1, examples) in enumerate(self.data_loader):

                if internal_iter > 1 and is_time_for(self.iter, self.evaluate_iter):
                    # test the behaviour on other losses
                    trec, tkld, tlat, tbce, tacc = self.test(end_of_epoch=False)
                    factors = pd.DataFrame(
                        {'iter': self.iter, 'rec': trec, 'kld': tkld, 'latent': tlat, 'BCE': tbce, 'Acc': tacc}, index=[0])

                    self.dataframe_eval = self.dataframe_eval.append(factors, ignore_index=True)
                    self.net_mode(train=True)

                    if track_changes and not self.dataframe_eval.empty:
                        self.dataframe_eval.to_csv(os.path.join(out_path, 'eval_results/test_metrics.csv'), index=False)
                        print('Saved test_metrics')

                    # include disentanglement metrics
                    dis_metrics = pd.DataFrame(self.evaluate_results, index=[0])
                    self.dataframe_dis = self.dataframe_dis.append(dis_metrics)

                    if track_changes and not self.dataframe_dis.empty:
                        self.dataframe_dis.to_csv(os.path.join(out_path, 'eval_results/dis_metrics.csv'), index=False)
                        print('Saved dis_metrics')

                losses = {'total_vae':0}

                x_true1 = x_true1.to(self.device)
                label1 = label1[:, 1:].to(self.device)
                y_true1 = y_true1.to(self.device, dtype=torch.long)

                ###configuration for dsprites

                losses, params = self.vae_classification(losses, x_true1, label1, y_true1, examples,
                                                         classification=start_classification)

                self.optim_G.zero_grad()
                self.optim_G_mse.zero_grad()
                self.class_G.zero_grad()

                if (internal_iter%self.show_loss)==0: print("Losses:", losses)

                if not start_classification:
                    losses[c.TOTAL_VAE].backward(retain_graph=False)
                    #losses['true_values'].backward(retain_graph=False)
                    self.optim_G.step()

                if start_classification:   # and (params['n_passed']>0):
                    losses['prediction'].backward(retain_graph=False)
                    self.class_G.step()

                vae_loss_sum += losses[c.TOTAL_VAE]
                losses[c.TOTAL_VAE_EPOCH] = vae_loss_sum /( internal_iter+1) ## ADDED +1 HERE IDK WHY NOT BEFORE!!!!!

                ## Insert losses -- only in training set

            self.log_save(input_image=x_true1, recon_image=params['x_recon'], loss=losses)
            # end of epoch

        self.pbar.close()


    def test(self, end_of_epoch=True):
        self.net_mode(train=False)
        rec, kld, latent, BCE, Acc = 0, 0, 0, 0, 0
        for internal_iter, (x_true, label, y_true, _) in enumerate(self.test_loader):
            x_true = x_true.to(self.device)
            label = label[:,1:].to(self.device, dtype=torch.long)
            y_true =  y_true.to(self.device, dtype=torch.long)

            mu, logvar = self.model.encode(x=x_true, )
            z = reparametrize(mu, logvar)

            mu_processed = torch.tanh(mu / 2)
            prediction, forecast = self.predict(latent=mu_processed)
            x_recon = self.model.decode(z=z,)

            if end_of_epoch:
                self.visualize_recon(x_true, x_recon, test=True)
                self.visualize_traverse(limit=(self.traverse_min, self.traverse_max),
                                        spacing=self.traverse_spacing,
                                        data=(x_true, label), test=True)

            rec+=(F.binary_cross_entropy(input=x_recon, target=x_true,reduction='sum').detach().item()/self.batch_size )
            kld+=(self._kld_loss_fn(mu, logvar).detach().item())


            if self.latent_loss == 'MSE':
                loss_bin = nn.MSELoss(reduction='mean')(mu_processed[:, :label.size(1)], 2 * label.to(dtype=torch.float32) - 1)
            elif self.latent_loss == 'BCE':
                loss_bin = nn.BCELoss(reduction='mean')((1+mu_processed[:, :label.size(1)])/2, label.to(dtype=torch.float32) )
            else:
                NotImplementedError('Wrong argument for latent loss.')

            latent+=(loss_bin.detach().item())
            del loss_bin

            BCE+=(nn.CrossEntropyLoss(reduction='mean')(prediction,
                                                        y_true).detach().item())


            Acc+=(Accuracy_Loss()(forecast,
                                   y_true).detach().item() )

            #self.iter += 1
            #self.pbar.update(1)

        print('Done testing')
        nrm = internal_iter + 1
        return rec/nrm, kld/nrm, latent/nrm, BCE/nrm, Acc/nrm