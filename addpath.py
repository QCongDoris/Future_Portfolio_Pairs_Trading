from os.path import dirname, abspath, join

root_path = dirname(abspath(__file__))

data_path = join(root_path, 'data')
algo_path = join(root_path, 'algorithm')
output_path = join(root_path, 'output')
configfile_path = join(root_path, 'config', 'config.conf')