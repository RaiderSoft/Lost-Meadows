from pathlib import Path
import ee
import os

def get_repo_root():
    return Path(__file__).resolve().parents[1]

ee.Initialize(project='lost-meadows')

repo_root = get_repo_root()

FOLDER_PATH = repo_root / "GEE" / "Predictions"
GEE_ASSET_FOLDER = 'projects/lost-meadows/assets/MeadowPredictions'

def upload_folder_to_gee(folder_path, asset_folder):
    tif_files = [f for f in os.listdir(folder_path) if f.endswith('.tif')]
    
    print(f"Found {len(tif_files)} files to upload...")
    
    for file_name in tif_files:
        local_path = str(os.path.join(folder_path, file_name))
        asset_name = os.path.splitext(file_name)[0]
        asset_id = f"{asset_folder}/{asset_name}"
        
        print(f"Uploading {file_name} {asset_id}")
        
        task = ee.data.startIngestion(
            request_id=ee.data.newTaskId()[0],
            params={
                'name': asset_id,
                'tilesets': [{'sources': [{'uris': [local_path]}]}]
            }
        )
        
        print(f"Task started: {task}")

upload_folder_to_gee(FOLDER_PATH, GEE_ASSET_FOLDER)