from __future__ import print_function

import sys
sys.path.insert(1, '..')

import numpy as np
import pickle
import matplotlib.pyplot as plt

from arguments import get_parser
from model import load_checkpoint 
from utils import *
from data import get_loader


##################################################################
def get_filename(args, exp_id1):
    checkpoint1 = os.path.join(args.checkpoint_folder, f"net_exp_{exp_id1}.pkl")
    
    early_stopped_checkpoint1 = os.path.join(args.checkpoint_folder, f"net_exp_{exp_id1}_early_stopped_model.pkl")
    
    best_checkpoint1 = f'{args.checkpoint_folder}/net_exp_{exp_id1}_best.pkl'
    
    if args.early_stopping:
        if os.path.exists(early_stopped_checkpoint1):
            checkpoint1 = early_stopped_checkpoint1
            print("Using the early stopping model!")
        elif os.path.exists(best_checkpoint1):
            checkpoint1 = best_checkpoint1
            print("Using best model!")
    
    print(checkpoint1)
    return checkpoint1 


##################################################################
def hook(model, input, output):
    if len(output) == 2:
        model._activations = torch.cat((model._activations, output[0].detach().float()), 1)
    else:
        model._activations = torch.cat((model._activations, output.detach().float()), 1)


def register_hooks(model):
    for name, layer in model.named_children():
        layer.__name__ = name
        layer._activations = torch.tensor([])
        layer.register_forward_hook(hook)


def cleanup(model):
    for _name, layer in model.named_children():
        layer._activations = torch.tensor([])


##################################################################
def compute_neural_efficiency(model, data_loader):
    batch_eff = []
    register_hooks(model)

    for inputs, _ in data_loader:
        _ = model(inputs)
        activations = get_activations(model, layer_types=('Linear', 'Conv2d','QuantLinear', 'QuantConv2d'))
        b_eff = layer_entropy(model, activations, len(inputs))
        batch_eff.append(b_eff)

    neural_eff = np.mean(np.array(batch_eff))
    print(f"[Model] Neural Efficiency: {neural_eff}")

    return neural_eff


def num_nodes(module):
    class_name = module.__class__.__name__
    if 'Linear' in class_name and hasattr(module, 'in_features'):
        return module.out_features
    elif 'Conv' in class_name and hasattr(module, 'out_channels'):
        return np.prod(module._activations.shape[1:])
    elif 'BatchNorm' in class_name and hasattr(module, 'num_features'):
        return module.num_features


def layer_entropy(model, activations, width):
    entropy = []
    for layer_name, acts in activations.items():
        layer = getattr(model, layer_name)
        # layer neural_eff = entropy/num_nodes
        # print(f'Layer {layer_name} non-zero count: {np.count_nonzero(acts.numpy(), axis=0)}')
        entropy.append(
            (np.count_nonzero(acts.numpy(), axis=0) / width).sum() / num_nodes(layer)
        )
    cleanup(model)
    return np.sqrt(np.sqrt(np.prod(entropy)))


##################################################################
param_layers = ['Linear', 'Bilinear', 'Conv1d', 'Conv2d', 'Conv3d', 'BatchNorm1d', 'BatchNorm2d', 'BatchNorm3d', 'QuantLinear', 'QuantConv2d','QuantBnConv2d']
act_layers = ['ReLU', 'LeakyReLU', 'ReLU6', 'PReLU', 'SELU', 'CELU', 'GELU', 'Sigmoid', 'Tanh', 'QuantAct', 'QuantMaxPool2d', 'QuantAveragePool2d']
layers = param_layers + act_layers


def get_activations(model, layer_types=()):
    if not layer_types:
        layer_types = layers
    layer_a = {}
    for _, module in model.named_children():
        if module.__class__.__name__ in layer_types:
            layer_a[module.__name__] = module._activations
    return layer_a


##################################################################
parser = get_parser(code_type='neural_eff')
args = parser.parse_args()

model_eff = []

train_loader, test_loader = get_loader(args)

# if args.train_or_test == 'train':
    # eval_loader = train_loader
# elif args.train_or_test == 'test':
    # eval_loader = test_loader
eval_loader = test_loader

for exp_id1 in range(5):
    file_name1 = get_filename(args, exp_id1)
    model = load_checkpoint(args, file_name1)    
    model_eff.append(compute_neural_efficiency(model, eval_loader))

f = open(args.result_location, "wb")
pickle.dump(model_eff, f)
f.close()
