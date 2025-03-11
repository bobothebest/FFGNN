import os

# Base paths
BASE_DIR = '/mnt/drive/MyDrive/social_network/codes/FFGNN'
DATA_DIR = os.path.join(BASE_DIR, 'processed')
MODEL_DIR = os.path.join(BASE_DIR, 'models')
LOG_DIR = os.path.join(BASE_DIR, 'log')

# Ensure directories exist
for dir_path in [DATA_DIR, MODEL_DIR, LOG_DIR]:
    os.makedirs(dir_path, exist_ok=True)

# Data paths
def get_data_path(data_name):
    return os.path.join(DATA_DIR, f'ml_{data_name}.csv')

# Feature path
FEATURE_PATH = os.path.join(DATA_DIR, 'paper_features.npy')

# Make sure the necessary files exist
def check_files():
    required_files = [FEATURE_PATH]
    for file_path in required_files:
        if not os.path.exists(file_path):
            print(f"Warning: Required file {file_path} does not exist!")
            return False
    return True
