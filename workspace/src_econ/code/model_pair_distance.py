from __future__ import print_function

import sys
sys.path.insert(1, '..')

import numpy as np
import pickle
import matplotlib.pyplot as plt

from arguments import get_parser
from model import load_checkpoint 
from utils import *


# def get_params(model): 
#     # wrt data at the current step
#     res = []
#     for _, module in model.named_modules():
#         module_type = module.__class__.__name__
#         if module_type == 'QuantLinear':
#             res.append(module.weight_integer.data.view(-1))
#             if hasattr(module, 'bias_integer'):
#                 res.append(module.bias_integer.data.view(-1))
#         elif module_type == 'Linear':
#             res.append(module.weight.data.view(-1))
#             if hasattr(module, 'bias'):
#                 res.append(module.bias.data.view(-1))
#     weight_flat = torch.cat(res)
#     return weight_flat

def get_params(model): 
    # wrt data at the current step
    res = []
    for _, module in model.named_modules():
        module_type = module.__class__.__name__
        res.append(module.weight.data.view(-1))
        res.append(module.bias.data.view(-1))
    weight_flat = torch.cat(res)
    return weight_flat


def rescale_params(params1, params2, scale='min-max'):
    if scale == 'min-max':
        # scale to range [0,1]
        p_min = min(params1.min(), params2.min())
        p_max = max(params1.max(), params2.max())
        params1 = (params1-p_min)/(p_max-p_min)
        params2 = (params2-p_min)/(p_max-p_min)
    return params1, params2


def compute_distance(model1, model2):
    params1 = get_params(model1)
    params2 = get_params(model2)
    params1, params2 = rescale_params(params1, params2, scale='min-max')
    dist = (params1-params2).norm().item()
    return dist


parser = get_parser(code_type='model_dist')
args = parser.parse_args()

model_distance = {}

for exp_id1 in range(5):
    
    model_distance[exp_id1] = {}
    
    for exp_id2 in range(5):
        
        file_name1, file_name2 = return_file_name(args, exp_id1, exp_id2)
        
        model1 = load_checkpoint(args, file_name1)
        model2 = load_checkpoint(args, file_name2)
        
        model_distance[exp_id1][exp_id2] = {'dist': compute_distance(model1, model2)}
        
        temp_results = {'model_distance': model_distance}
        
        f = open(args.result_location, "wb")
        pickle.dump(temp_results, f)
        f.close()
        