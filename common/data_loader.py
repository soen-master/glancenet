import os
from .utils import Accuracy_Loss, F1_Loss

from sklearn.linear_model import LogisticRegression
import matplotlib.pyplot as plt
import numpy as np
import logging

import torch
from PIL import Image
from torch.utils.data import Dataset, DataLoader
from torchvision.datasets import ImageFolder
from torchvision import transforms
import matplotlib.pyplot as plt

from common import constants as c


def target_cast(inputs, r_plane, irrelevant_components=[0], _plot=False):
    targets = []
    admitted = np.ones(len(r_plane[0]))
    admitted[irrelevant_components] = 0
    print(admitted)
    for i in range(len(inputs)):
        guess =  (np.dot(inputs[i] - r_plane[1]*admitted, (r_plane[0]*admitted) ))
        if guess < 0: target = 1
        else: target = 0
        #if np.random.uniform() > 0.99:
         #   if target > 0:
          #      target = 0
           # else: target = 1

        targets.append((target))

    if _plot:
        f = plt.figure(figsize=(18, 10))
        mask = (np.array(targets, dtype=np.int) > 0)
        plt.plot(inputs[:,4][mask], inputs[:,5][mask], 'r.', label='classified 1' )
        plt.plot(inputs[:,4][~mask], inputs[:,5][~mask], 'b.', label='classified 0' )
        x = np.linspace(np.min(inputs[:,4]), np.max(inputs[:,4]))
        y = -r_plane[0][4]/r_plane[0][5]*x
        plt.plot(x,y, color='black', label='separation plane')
        plt.legend()
        plt.xlim(x[0], x[-1])
        plt.ylim(np.min(inputs[:,5]), np.max(inputs[:,5]) )
        plt.show()
    return np.array(targets, dtype=np.int)


def random_plane(labels, space, irrelevant_components=0,_plot=False):
    l = len(labels)

    random_versor = np.random.uniform(size=l)
    random_versor /= np.linalg.norm(random_versor)

    mean_vect = np.mean(space, axis=0)

    assert np.all( space[:,0] ==0 ), space[:50,0]
    assert np.all( mean_vect[2:] < 0.1 ), mean_vect

    print("Random versor=", random_versor)

    if _plot:
        f = plt.figure(figsize=(18, 10))
        for i in range(l):
            f.add_subplot(2, 3, i+1)
            z = space[:,i]
            plt.hist(z, int(len(z)/100), label='component-%i'%(i-1))
            plt.legend()
        plt.show()

    return [random_versor, mean_vect]


class LabelHandler(object):
    def __init__(self, labels, label_weights, class_values):
        self.labels = labels
        self._label_weights = None
        self._num_classes_torch = torch.tensor((0,))
        self._num_classes_list = [0]
        self._class_values = None
        if labels is not None:
            self._label_weights = [torch.tensor(w) for w in label_weights]
            self._num_classes_torch = torch.tensor([len(cv) for cv in class_values])
            self._num_classes_list = [len(cv) for cv in class_values]
            self._class_values = class_values

    def label_weights(self, i):
        return self._label_weights[i]

    def num_classes(self, as_tensor=True):
        if as_tensor:
            return self._num_classes_torch
        else:
            return self._num_classes_list

    def class_values(self):
        return self._class_values

    def get_label(self, idx):
        if self.labels is not None:
            return torch.tensor(self.labels[idx], dtype=torch.long)
        return None

    def get_values(self, idx):
        if self.labels is not None:
            return torch.tensor(self.labels[idx], dtype=torch.float)
        return None

    def has_labels(self):
        return self.labels is not None


class CustomImageFolder(ImageFolder):
    def __init__(self, root, transform, labels, label_weights, name, class_values, num_channels, seed):
        super(CustomImageFolder, self).__init__(root, transform)
        self.indices = range(len(self))
        self._num_channels = num_channels
        self._name = name
        self.seed = seed

        self.label_handler = LabelHandler(labels, label_weights, class_values)

        ## ADDED GRAYBOX VARIANT
        self.isGRAY = False

    @property
    def name(self):
        return self._name

    def label_weights(self, i):
        return self.label_handler.label_weights(i)

    def num_classes(self, as_tensor=True):
        return self.label_handler.num_classes(as_tensor)

    def class_values(self):
        return self.label_handler.class_values()

    def has_labels(self):
        return self.label_handler.has_labels()

    def num_channels(self):
        return self._num_channels

    def __getitem__(self, index1):
        path1 = self.imgs[index1][0]
        img1 = self.loader(path1)
        if self.transform is not None:
            img1 = self.transform(img1)

        label1 = 0
        if self.label_handler.has_labels():
            label1 = self.label_handler.get_label(index1)
        if self.isGRAY: label1 = self.label_weights(index1)
        return img1, label1


class CustomNpzDataset(Dataset): ### MODIFIED HERE THE DATABASE TYPE FOR _GET_ITEM
    def __init__(self, data_images, transform, labels, label_weights, name, class_values, num_channels, seed, y_target=None):
        self.seed = seed
        self.data_npz = data_images
        self._name = name
        self._num_channels = num_channels

        self.label_handler = LabelHandler(labels, label_weights, class_values)

        self.transform = transform
        self.indices = range(len(self))

        ## ADDED GRAYBOX VARIANT
        self.isGRAY = False
        self.y_data = y_target

    @property
    def name(self):
        return self._name

    def label_weights(self, i):
        return self.label_handler.label_weights(i)

    def num_classes(self, as_tensor=True):
        return self.label_handler.num_classes(as_tensor)

    def class_values(self):
        return self.label_handler.class_values()

    def has_labels(self):
        return self.label_handler.has_labels()

    def num_channels(self):
        return self._num_channels

    def __getitem__(self, index1):
        #print("Passed index", index1)
        img1 = Image.fromarray(self.data_npz[index1] * 255)
        if self.transform is not None:
            img1 = self.transform(img1)

        label1 = 0
        if self.label_handler.has_labels():
            label1 = self.label_handler.get_label(index1)
            #print("The obtained label is", label1)
            ### INSERTED THE TRUTH VALUE FOR DSPIRTES
            if self.isGRAY:
                y = self.y_data[index1]
                z_values = self.label_handler.get_values(index1)
                return img1, z_values, y
        return img1, label1, 0

    def __len__(self):
        return self.data_npz.shape[0]


class DisentanglementLibDataset(Dataset):
    """
    Data-loading from Disentanglement Library

    Note:
        Unlike a traditional Pytorch dataset, indexing with _any_ index fetches a random batch.
        What this means is dataset[0] != dataset[0]. Also, you'll need to specify the size
        of the dataset, which defines the length of one training epoch.

        This is done to ensure compatibility with disentanglement_lib.
    """

    def __init__(self, name, seed=0, make_yset=False):
        """
        Parameters
        ----------
        name : str
            Name of the dataset use. You may use `get_dataset_name`.
        seed : int
            Random seed.
        iterator_len : int
            Length of the dataset. This defines the length of one training epoch.
        """
        from disentanglement_lib.data.ground_truth.named_data import get_named_ground_truth_data
        self.name = name
        self.seed = seed
        self.random_state = np.random.RandomState(seed)
        self.dataset = get_named_ground_truth_data(self.name)
        self.iterator_len = self.dataset.images.shape[0]

    @staticmethod
    def has_labels():
        return False


    def num_channels(self):
        return self.dataset.observation_shape[2]

    def __len__(self):
        return self.iterator_len

    def __getitem__(self, item):
        assert item < self.iterator_len
        output = self.dataset.sample_observations(1, random_state=self.random_state)[0]
        # Convert output to CHW from HWC
        return torch.from_numpy(np.moveaxis(output, 2, 0), ).type(torch.FloatTensor), 0


def _get_dataloader_with_labels(name, dset_dir, batch_size, seed, num_workers, image_size, include_labels, pin_memory,
                                shuffle, droplast, d_version="full"):
    transform = transforms.Compose([
        transforms.Resize((image_size, image_size)),
        transforms.ToTensor(), ])
    labels = None
    label_weights = None
    label_idx = None
    label_names = None
    class_values = None

    # check if labels are provided as indices or names
    if include_labels is not None:
        try:
            int(include_labels[0])
            label_idx = [int(s) for s in include_labels]
        except ValueError:
            label_names = include_labels
    logging.info('include_labels: {}'.format(include_labels))

    make_yset = False

    if name.lower() == 'celeba':
        print("Entered this routine")
        root = os.path.join(dset_dir, 'CelebA')
        labels_file = os.path.join(root, 'list_attr_celeba.csv')

        # celebA images are properly numbered, so the order should remain intact in loading
        labels = None
        if label_names is not None:
            labels = []
            labels_all = np.genfromtxt(labels_file, delimiter=',', names=True)
            for label_name in label_names:
                labels.append(labels_all[label_name])
            labels = np.array(labels).transpose()
        elif label_idx is not None:
            labels_all = np.genfromtxt(labels_file, delimiter=',', skip_header=True)
            labels = labels_all[:, label_idx]

        if labels is not None:
            # celebA labels are all binary with values -1 and +1
            labels[labels == -1] = 0
            from pathlib import Path
            num_l = labels.shape[0]
            num_i = len(list(Path(root).glob('**/*.jpg')))
            assert num_i == num_l, 'num_images ({}) != num_labels ({})'.format(num_i, num_l)

            # calculate weight adversely proportional to each class's population
            num_labels = labels.shape[1]
            label_weights = []
            for i in range(num_labels):
                ones = labels[:, i].sum()
                prob_one = ones / labels.shape[0]
                label_weights.append([prob_one, 1 - prob_one])
            label_weights = np.array(label_weights)

            # all labels in celebA are binary
            class_values = [[0, 1]] * num_labels

        data_kwargs = {'root': root,
                       'labels': labels,
                       'label_weights': label_weights,
                       'class_values': class_values,
                       'num_channels': 3}
        dset = CustomImageFolder
    elif name.lower() == 'dsprites_full':
        #print(name)
        if d_version == "full":
            root = os.path.join(dset_dir, 'dsprites/dsprites_ndarray_co1sh3sc6or40x32y32_64x64.npz')
        elif d_version=="smaller":
            root = os.path.join(dset_dir, 'dsprites/dsprites_ndarray_co1sh3sc6or40x32y32_64x64_smaller.npz')
        else:
            raise ValueError

        npz = np.load(root)
        """
        print("Passed npz:", np.shape(npz), "and",type(npz))
        print(npz.files)
        print("Information on how they're stored")
        print(" ")
        print(np.shape(npz["latents_values"]))
        print("latents_values contains \n", npz["latents_values"][:10] )
        print(" ")
        print("Here the min/max is for every column:")
        ranges = []
#        for i in range(len(npz["latents_values"][0])  ):
 #           new_list = []
  #          for any_number in npz["latents_values"][:,i]:
   #             if  not any_number in new_list:
    #                new_list.append(any_number)
     #       ranges.append(new_list)

        #del new_list
        #print("The ranges are")
        #print(ranges)

        #print("label_idx", label_idx)
        #for i in range(len(ranges)):
         #   print(i)
          #  print("For class ", i, "min", np.min(ranges[i]),"max",np.max(ranges[i]))
 #        print([np.min(npz["latents_values"][:, i] for i in range(len(npz["latents_values"][0] )))])
#        print([np.max(npz["latents_values"][:, i] for i in range(len(npz["latents_values"][0] )))])

        """
        if label_idx is not None:
            #print("Passed label_idx:",label_idx)
            labels = (npz['latents_values'][:, label_idx])

            ### SHIFTING ALL VALUES OVER THEIR MEANS
            Mean = np.mean(labels, axis=0 )
            for j in label_idx:
                if j != 1:  labels[:, j] -= Mean[j]

            if 1 in label_idx:
                index_shape = label_idx.index(1)
                labels[:, 1] -= 1

            ### CREATE THE H-STACK with the usual np onehot
                #print("Info on labels")
                #print(np.shape(labels))
                #print(type(labels))
                #print(len(labels))

                b = np.zeros((len(labels),3))
                b[np.arange(len(labels)), np.asarray(labels[:,1], dtype=np.int) ] = 1

#                print(np.shape(labels[:,0].reshape(-1,1)   ), b )
                new_labels = np.hstack( (labels[:,0].reshape(-1,1) , b))
                labels_one_hot = np.hstack((new_labels, labels[:,2:] ) )



            # dsprite has uniformly distributed labels
            num_labels = labels.shape[1]
            label_weights = []
            class_values = []
            for i in range(num_labels):
                unique_values, count = np.unique(labels[:, i], axis=0, return_counts=True)
                weight = 1 - count / labels.shape[0]
                if len(weight) == 1:
                    weight = np.array(1)
                else:
                    weight /= sum(weight)
                label_weights.append(np.array(weight))

                # always set label values to integers starting from zero
                unique_values_mock = np.arange(len(unique_values))
                class_values.append(unique_values_mock)
#            print("the npz is of size", np.size(npz['latents_values']))
            label_weights = np.array(label_weights)#, dtype=np.float32)
        #print("Labels is size: ", np.shape(labels))

        #max_capacity = 10000
 #       print("labels are of size", np.size(labels))
  #      print("the npz is of size", np.size(npz['latents_values']))
        data_kwargs = {'data_images': npz['imgs']}
        data_kwargs.update({'labels': labels_one_hot,
                       'label_weights': label_weights,
                       'class_values': class_values,
                       'num_channels': 1})
        dset = CustomNpzDataset
        #print("The r plane:",[random_plane(label_idx, ranges)])
        if labels is not None:
            ### NOW CREATE A PARTICULAR TYPE THAT PREDICTS ONLY WITH TWO COMPONENTS
            target_set = np.asarray(
                        target_cast(labels, r_plane=random_plane(label_idx, labels,  _plot=False), irrelevant_components=[0], _plot=False), dtype=np.int
                        )
            print("target", np.shape(target_set))
            data_kwargs.update({'y_target': target_set})

            print("Population of 0:", len(target_set[target_set == 0]) / len(target_set) * 100, "%.")

            print("Start verification")
#            print("labels shape:", (np.shape(labels)))
            in_data = labels

            print("Labels in data_loader")

            y_target1 = target_set

            lr = LogisticRegression( solver='lbfgs')
            lr.fit(in_data[:,1:], y_target1)
            y_pred = lr.predict_proba(in_data[:,1:])
            """ 
            f = plt.figure(figsize=(20,10))
            f.add_subplot(1,2,1)
            mask = (y_target1>0.5)
            plt.plot(in_data[mask][:,4], in_data[mask][:,5], 'b.', label='1' )
            plt.plot(in_data[~mask][:,4], in_data[~mask][:,5], 'r.', label='0' )
            plt.legend()

            f.add_subplot(1,2,2)
            mask = (y_pred[:,1]>0.5)
            plt.plot(in_data[mask][:,4], in_data[mask][:,5], 'b.', label='1' )
            plt.plot(in_data[~mask][:,4], in_data[~mask][:,5], 'r.', label='0' )
            plt.legend()

            plt.show()
            """

            baseline = torch.nn.CrossEntropyLoss(reduction="mean", )(torch.tensor(y_pred), torch.tensor(y_target1))

            print("Fitting a LogReg model, loss:",  baseline)

            accuracy = Accuracy_Loss()(torch.tensor(y_pred, dtype=torch.float), torch.tensor(y_target1, dtype=torch.float))
            print("ACCURACY for logreg: ", accuracy)

        make_yset = True
    else:
        raise NotImplementedError

    data_kwargs.update({'seed': seed,
                        'name': name,
                        'transform': transform})
    dataset = dset(**data_kwargs)

    # Setting the Graybox here
    dataset.isGRAY = True

    data_loader = DataLoader(dataset,
                             batch_size=batch_size,
                             shuffle=shuffle,
                             num_workers=num_workers,
                             pin_memory=pin_memory,
                             drop_last=droplast)

    if include_labels is not None:
        logging.info('num_classes: {}'.format(dataset.num_classes(False)))
        logging.info('class_values: {}'.format(class_values))
    """ 
    if make_yset and labels is not None:
        target_loader = DataLoader(target_set,
                                   batch_size=batch_size,
                                   shuffle=shuffle,
                                   num_workers=num_workers,
                                   pin_memory=pin_memory,
                                   drop_last=droplast
                                    )
        print("Made target_loader")

#        quit()
        return data_loader, target_loader
    

    else:
    """
    return data_loader, [None]



def get_dataset_name(name):
    """Returns the name of the dataset from its input argument (name) or the
    environment variable `AICROWD_DATASET_NAME`, in that order."""
    return name or os.getenv('AICROWD_DATASET_NAME', c.DEFAULT_DATASET)


def get_datasets_dir(dset_dir):
    if dset_dir:
        os.environ['DISENTANGLEMENT_LIB_DATA'] = dset_dir
    return dset_dir or os.getenv('DISENTANGLEMENT_LIB_DATA')


def _get_dataloader(name, batch_size, seed, num_workers, pin_memory, shuffle, droplast):
    """
    Makes a dataset using the disentanglement_lib.data.ground_truth functions, and returns a PyTorch dataloader.
    Image sizes are fixed to 64x64 in the disentanglement_lib.
    :param name: Name of the dataset use. Should match those of disentanglement_lib
    :return: DataLoader
    """
    dataset = DisentanglementLibDataset(name, seed=seed)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=shuffle, drop_last=droplast, pin_memory=pin_memory,
                        num_workers=num_workers,)
    return loader


def get_dataloader(dset_name, dset_dir, batch_size, seed, num_workers, image_size, include_labels, pin_memory,
                   shuffle, droplast, d_version="full"):
    locally_supported_datasets = c.DATASETS[0:2]
    dset_name = get_dataset_name(dset_name)
    dsets_dir = get_datasets_dir(dset_dir)

    logging.info(f'Datasets root: {dset_dir}')
    logging.info(f'Dataset: {dset_name}')

    if dset_name in locally_supported_datasets:
        return _get_dataloader_with_labels(dset_name, dsets_dir, batch_size, seed, num_workers, image_size,
                                           include_labels, pin_memory, shuffle, droplast, d_version=d_version)
    else:
        # use the dataloader of Google's disentanglement_lib
        return _get_dataloader(dset_name, batch_size, seed, num_workers, pin_memory, shuffle, droplast)

