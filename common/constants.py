# Strings
LOSS = 'loss'
ACCURACY = 'acc'
ITERATION = 'iteration'
WANDB_NAME = 'disentanglement'
INPUT_IMAGE = 'input_image'
RECON_IMAGE = 'recon_image'
RECON = 'recon'
FIXED = 'fixed'
SQUARE = 'square'
ELLIPSE = 'ellipse'
HEART = 'heart'
TRAVERSE = 'traverse'
RANDOM = 'random'
TEMP = 'tmp'
GIF = 'gif'
JPG = 'jpg'
FACTORVAE = 'FactorVAE'
DIPVAEI = 'DIPVAEI'
DIPVAEII = 'DIPVAEII'
BetaTCVAE = 'BetaTCVAE'
INFOVAE = 'InfoVAE'
GRAYVAE = "grayvae"
GRAYVAE_STANDARD = 'grayvae_standard'
GRAYVAE_JOIN = 'grayvae_join'
CBM_SEQ = 'cbm_seq'
CBM_JOIN ='cbm_join'
SENN = 'SENN'

TOTAL_VAE = 'total_vae'
TOTAL_VAE_EPOCH = 'total_vae_epoch'
LEARNING_RATE = 'learning_rate'

# Algorithms
ALGS = ('AE', 'VAE', 'BetaVAE', 'CVAE', 'IFCVAE', "GRAYVAE", 'GrayVAE_Standard', 'GrayVAE_Join', 'CBM_Seq', 'CBM_Join')
LOSS_TERMS = (FACTORVAE, DIPVAEI, DIPVAEII, BetaTCVAE, INFOVAE, GRAYVAE, GRAYVAE_STANDARD, GRAYVAE_JOIN, CBM_SEQ, CBM_JOIN) #uncertain here

# Datasets
DATASETS = ('celebA', 
            'dsprites_full', 'dsprites_noshape', 'color_dsprites', 'noisy_dsprites', 'scream_dsprites', 'dsprites_leakage',
            'smallnorb', 'cars3d', 'shapes3d', 
            'mpi3d', 'mpi3d_toy', 'mpi3d_realistic', 'mpi3d_real')
DEFAULT_DATASET = DATASETS[-2]  # mpi3d_realistic
TEST_DATASETS = DATASETS[0:2]  # celebA, dsprites_full

# Architectures
DISCRIMINATORS = ('SimpleDiscriminator', 'SimpleDiscriminatorConv64')
TILERS = ('MultiTo2DChannel',)
DECODERS = ('SimpleConv64', 'ShallowLinear', 'DeepLinear', 'DeConv64')
ENCODERS = ('SimpleConv64', 'SimpleGaussianConv64', 'PadlessConv64', 'PadlessGaussianConv64',
            'ShallowGaussianLinear', 'DeepGaussianLinear', 'EncConv64')

# Evaluation Metrics
EVALUATION_METRICS = ('dci', 'factor_vae_metric', 'sap_score', 'mig', 'irs', 'beta_vae_sklearn')

# Schedulers
LR_SCHEDULERS = ('ReduceLROnPlateau', 'StepLR', 'MultiStepLR', 'ExponentialLR',
                 'CosineAnnealingLR', 'CyclicLR', 'LambdaLR')
SCHEDULERS = ('LinearScheduler', )
