from collections import defaultdict

def sort_gear_args(in_dict):
    """
    Convert basic config.json to a nested dictionary that will be referenced throughout
    the gear. Each modality is a key within the dictionary at the highest level, allowing
    subsets of the dictionary to be passed to functions. Common parameters are kept as
    keys at the main level for ease of access.
    Args:
        in_dict (dictionary): any dictionary of parameters for the gear. Can be inputs, configs, or
        single entry updates.
    Returns:
        sifted_dict (dictionary): sifted according to HCP-related logic. Use dict.update() to add
        this dictionary to pre-existing ones.
    """
    sifted_dict = defaultdict()
    for k, v in in_dict:
        if 'struct' in k.lower():
            sifted_dict['struct'][k] = v
        elif 'func' in k.lower():
            sifted_dict['func'][k] = v
        elif 'diff' in k.lower():
            sifted_dict['diff'][k] = v
        elif k.startswith('gear-'):
            sifted_dict['fw_param'][k] = v
        else:
            sifted_dict[k] = v

    return sifted_dict