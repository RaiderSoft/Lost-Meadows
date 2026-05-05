"""
Ingest global model prediction TIFs from GCS into GEE GlobalPredictions folder.

Prerequisites (run in order before this script):
  1. Run global model pipeline on ORCA (submit_global_features.slurm + submit_global_model.slurm)
  2. scp outputs from ORCA to local FinalOutputGlobal/:
       scp -r lm1@login.orca.pdx.edu:~/Lost-Meadows/GEE/TIF_Output/FinalOutputGlobal \
           ~/Capstone/Lost-Meadows/GEE/TIF_Output/
  3. Authenticate gcloud (if session expired):
       gcloud auth login
       gcloud auth application-default login
  4. Upload TIFs to GCS bucket:
       cd GEE/TIF_Output/FinalOutputGlobal
       gsutil -m cp *.tif gs://lost-meadows-predictions/global/

Then run this script from the repo root:
  python ExportPredictions/upload_global_to_gee.py

After ingestion completes (~5-10 min), run set_public_acl_global.py to make assets public.
"""

import subprocess
import sys
import ee
import google.auth

PROJECT = 'lost-meadows'
ASSET_FOLDER = 'projects/lost-meadows/assets/GlobalPredictions'
GCS_PREFIX = 'gs://lost-meadows-predictions/global'

credentials, _ = google.auth.default()
ee.Initialize(credentials=credentials, project=PROJECT)
print('Connected to Earth Engine')

# Create folder if it doesn't exist
try:
    ee.data.createAsset({'type': 'Folder'}, ASSET_FOLDER)
    print(f'Created folder: {ASSET_FOLDER}')
except Exception:
    print(f'Folder already exists: {ASSET_FOLDER}')

# Delete existing assets in folder
print('\nDeleting existing assets...')
try:
    children = ee.data.listAssets({'parent': ASSET_FOLDER}).get('assets', [])
    for asset in children:
        ee.data.deleteAsset(asset['name'])
        print(f"  Deleted: {asset['name'].split('/')[-1]}")
    print(f'Deleted {len(children)} assets')
except Exception as e:
    print(f'  Nothing to delete: {e}')

# List TIFs in GCS
result = subprocess.run(
    ['gsutil', 'ls', f'{GCS_PREFIX}/*.tif'],
    capture_output=True, text=True
)
tif_paths = [p.strip() for p in result.stdout.strip().split('\n') if p.strip()]
print(f'\nFound {len(tif_paths)} TIFs in GCS')

# Ingest each TIF
print('\nStarting ingestion...')
for gcs_path in tif_paths:
    filename = gcs_path.split('/')[-1].replace('.tif', '')
    asset_id = f'{ASSET_FOLDER}/{filename}'
    request = {
        'name': asset_id,
        'tilesets': [{'sources': [{'uris': [gcs_path]}]}],
    }
    ee.data.startIngestion(ee.data.newTaskId()[0], request)
    print(f'  Queued: {filename}')

print(f'\nAll {len(tif_paths)} ingestion tasks submitted.')
print('Monitor progress at: https://code.earthengine.google.com/tasks')
print('\nOnce complete, run: python ExportPredictions/set_public_acl_global.py')
