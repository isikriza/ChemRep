from tensorflow.python.keras import backend as K
from tensorflow.python.keras.models import model_from_yaml
from rdkit.Chem import AllChem
from optparse import OptionParser
import rdkit
import rdkit.Chem as Chem
import torch
import pandas as pd
import numpy as np
import sys

sys.path.append('jtnn/')
from jtnn import *
sys.path.append('../')


class Representation:

    def __init__(self):
        yaml_file = open('Models/autoencoder_optedilmemis.yaml', 'r')
        loaded_model_yaml = yaml_file.read()
        yaml_file.close()
        self.loaded_model = model_from_yaml(loaded_model_yaml)
        # load weights into new model
        self.loaded_model.load_weights("Models/autoencoder_optedilmemis.h5")

        lg = rdkit.RDLogger.logger()
        lg.setLevel(rdkit.RDLogger.CRITICAL)

        # Jupyter notebookta hata verdiği için parser kapatıldı.
        # parser = OptionParser()
        # parser.add_option("-t", "--test", dest="test_path")
        # parser.add_option("-v", "--vocab", dest="vocab_path")
        # parser.add_option("-m", "--model", dest="model_path")
        # parser.add_option("-w", "--hidden", dest="hidden_size", default=450)
        # parser.add_option("-l", "--latent", dest="latent_size", default=56)
        # parser.add_option("-d", "--depth", dest="depth", default=3)
        # parser.add_option("-e", "--stereo", dest="stereo", default=1)
        # opts, args = parser.parse_args()

        vocab = [x.strip("\r\n ") for x in open("unique_canonical_train_vocab.txt")]
        vocab = Vocab(vocab)

        hidden_size = 450
        latent_size = 56
        depth = 3
        stereo = True

        model = JTNNVAE(vocab, hidden_size, latent_size, depth, stereo=stereo)
        model.load_state_dict(
            torch.load("Models/model.iter-9-6000"))  # opts.model_path #MPNVAE-h450-L56-d3-beta0.001/model.iter-4

        self.model = model.cuda()

    def get_representation(self, smiles, descriptor):
        representation = [smiles]

        if descriptor == "jtvae":
            for i in self.jtvae_representation([smiles])[0]:
                representation.append(i)
            return np.asarray(representation)

        elif descriptor == "ecfp_autoencoder":
            for i in self.ecfp_representation(([smiles])):
                representation.append(i)
            return np.asarray(representation)

    def ecfp_representation(self, dat):
        for smiles in dat:
            m2 = Chem.MolFromSmiles(smiles)
            if m2 is not None:
                fp1 = AllChem.GetMorganFingerprintAsBitVect(m2, 3, nBits=1024)
                a = np.asarray(fp1)
                # with a Sequential model
                get_3rd_layer_output = K.function([self.loaded_model.layers[0].input],
                                                  [self.loaded_model.layers[1].output])
                layer_output = get_3rd_layer_output(np.asarray([a]))[0]
                return layer_output[0]

            else:
                return None

    def jtvae_representation(self, dat):
        koku = pd.DataFrame(columns=list(range(56)))

        for smiles in dat:
            mol = Chem.MolFromSmiles(smiles)
            smiles3D = Chem.MolToSmiles(mol, isomericSmiles=False)
            dec_smiles = self.model.reconstruct(smiles3D, DataFrame=koku)

            del smiles3D
            del dec_smiles
            torch.cuda.empty_cache()
            return koku.values
