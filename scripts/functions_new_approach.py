from Bio.Nexus import Nexus
from Bio import AlignIO
from collections import defaultdict, OrderedDict
import numpy as np
import sys, os
from pathlib2 import Path
from tqdm import tqdm

def process_dataset(dataset_path, min_aln_size, outfilename):
    '''
    args: dataset_path: path to a nexus alignment
          min_ln_size: minimum size for a charaset nex data block
          outfilename: name of files
    return
         pFinder config files
    '''
    
    dataset_name = os.path.basename(dataset_path).rstrip(".nex")

    read_aln = charset_uce_aln(dataset_path)

    uce_dicts = []
    for uce in tqdm(read_aln):
        uce_dicts.append(dict_uce_sites(uce))

    conc_dicts = conc_dicts_by_key(uce_dicts)
    merge_small_aln = conc_end_flanks(conc_dicts, min_aln_size)

    export_charset(dataset_name, merge_small_aln, outfilename)

def charset_uce_aln(aln):
    '''
    args:
        aln: nexus aln with charasets
    return:
        a list of generic biopython alns, each representing an uce
    '''
    dat = Nexus.Nexus()
    dat.read(aln)
    aln = AlignIO.read(open(aln), "nexus")

    uce_pos = []
    for name in dat.charsets:
        uce_pos.append(dat.charsets[name])

    return(uce_pos)

def dict_uce_sites(uce_aln):
    '''
    uce_aln
        args: generic biopython aln
    return:
        dict with keys corresponding to sites (where middle site is set to zero)
            and values to actual position of a site in the aln
    '''

    N        = len(uce_aln)
    middle   = int(float(N) / 2.0)
    site_num = np.array(range(N)) - middle

    sites = {}
    for i, site in enumerate(range(len(uce_aln))):
        sites[site_num[i]] = uce_aln[i]

    return(sites)

def conc_dicts_by_key(tuple_dicts):
# inspired by http://stackoverflow.com/questions/5946236/how-to-merge-multiple-dicts-with-same-key
    '''
    args:
        tuple_dicts: dictionary of tuples
    return: 
        defautdict type of dicts, with keys (merged across all uce) as sites and 
            values as lists of conc site positions (acutal site in the aln) 
    '''

    uce_dicts = defaultdict(list)

    for dicts in tuple_dicts:
        for key, value in dicts.items():
            uce_dicts[key].append(value)

    return(uce_dicts)

def conc_end_flanks(conc_dicts, min_aln_size):
    # There is a bug in the built-it function 'range'. 
    # It doesn't work with decreasing numbers (e.g. range(max(x), 0))
    # below my way around this problem
    key_list  = list(conc_dicts.keys())
    num_list  = [num for num in key_list if num >= 0]
    key_range = num_list[::-1]
    
    for i in key_range: 
        key = i                        
        if len(conc_dicts[key]) < min_aln_size:
            conc_dicts[key - 1] = conc_dicts[key] + conc_dicts[key - 1]
            del conc_dicts[key]

    for i in range(min(conc_dicts), 0):
        key = i
        if len(conc_dicts[key]) < min_aln_size:
            conc_dicts[key + 1] = conc_dicts[key] + conc_dicts[key + 1]
            del conc_dicts[key]

    return(conc_dicts)

def output_paths(dataset_path):
    '''
    args: 
        dataset_path: path to a nexus alignment with UCE charsets 
    return: 
        folder path with the name of the nexus UCE dataset  
    '''
    
    dataset_name = os.path.basename(dataset_path).rstrip(".nex")

    repository_dir      = Path(dataset_path).parents[1]
    processed_data_dir  = os.path.join(str(repository_dir), "processed_data")

    output_path = os.path.join(processed_data_dir, dataset_name)
    
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    return (output_path)

def p_finder_start_block(dataset_name, branchlengths = 'linked', models = 'all', model_selection = 'aicc'):
    '''
    args: 
        dataset_name: name of the dataset
        branchlengths, models, model_selection: pFinder input arguments
    return:
        str with information about the begin block pFinder config block
    '''
    begin_block = str('## ALIGNMENT FILE ##\n' + 
                      'alignment = %s.phy;\n\n' % (dataset_name) +  


                      '## BRANCHLENGTHS: linked | unlinked ##\n' +
                      'branchlengths = %s;\n\n' % (branchlengths) +

                       '## MODELS OF EVOLUTION: all | allx | mrbayes | beast | gamma | gammai <list> ##\n' +
                       'models = %s;\n\n' % (models) + 

                       '# MODEL SELECCTION: AIC | AICc | BIC #\n' +
                       'model_selection = %s;\n\n' % (model_selection) +

                       '## DATA BLOCKS: see manual for how to define ##\n' +
                       '[data_blocks]\n')

    return (begin_block)

def p_finder_end_block(dataset_name, search = 'rcluster'):
    '''
    args: 
        dataset_name: name of the dataset
        search: pFinder input arguments
    return:
        str with information about the end block pFinder config block
    '''
    
    end_block = str('\n' +
                    '## SCHEMES, search: all | user | greedy | rcluster | hcluster | kmeans ##\n' +
                    '[schemes]\n' +
                    'search = %s;\n\n' % (search) +

                    '#user schemes go here if search=user. See manual for how to define.#')

    return (end_block)

def export_charset(dataset_name, uce_dics, outfilename):
    '''
    args:
        dataset_name: name of the dataset
        uce_dicts: defautdict type of dicts with keys as uce site and values
            acutal position in the full aln
    return:

    '''
    outfile = open('%s_new_approach_partition_finder.cfg' % (outfilename), 'w')

    outfile.write(p_finder_start_block(dataset_name))

    for key, value in uce_dics.items():
        keyi   = key
        valuei = (np.sort((np.array(value) + 1))).tolist()
        valuei = str(valuei).lstrip(' [').rstrip(']') # .replace(', ', ',') <- to exclude spaces too
        
        charset = 'uce_sites_%s = %s;\n' % (keyi, valuei)
        
        outfile.write(charset)
    
    outfile.write(p_finder_end_block(dataset_name))    

    outfile.close()