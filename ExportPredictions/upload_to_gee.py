"""
Delete existing GEE Predictions assets and re-ingest all 119 TIFs from GCS.

Prerequisites (run in order before this script):
  1. Run the full pipeline on ORCA to generate *_Probability.tif files
  2. scp outputs from ORCA to local FinalOutputOrca/:
       scp lm1@login.orca.pdx.edu:~/Lost-Meadows/GEE/TIF_Output/FinalOutput/* \\
           ~/Capstone/Lost-Meadows/GEE/TIF_Output/FinalOutputOrca/
  3. Authenticate gcloud (if session expired):
       gcloud auth login
       gcloud auth application-default login
  4. Upload TIFs to GCS bucket:
       cd GEE/TIF_Output/FinalOutputOrca
       gsutil -m cp *.tif gs://lost-meadows-predictions/

Then run this script from the repo root:
  python upload_to_gee.py

After ingestion completes (~5-10 min), run set_public_acl.py to make assets public.
"""
import ee
import google.auth
import time

PROJECT = 'lost-meadows'
ASSET_FOLDER = 'projects/lost-meadows/assets/Predictions'
GCS_BUCKET = 'gs://lost-meadows-predictions'

credentials, _ = google.auth.default()
ee.Initialize(credentials=credentials, project=PROJECT)
print('Connected to Earth Engine')

# Delete all existing assets in the Predictions folder
print('\nDeleting existing assets...')
try:
    children = ee.data.listAssets({'parent': ASSET_FOLDER})['assets']
    for asset in children:
        ee.data.deleteAsset(asset['name'])
        print(f"  Deleted: {asset['name'].split('/')[-1]}")
    print(f'Deleted {len(children)} assets')
except Exception as e:
    print(f'  No assets to delete or folder empty: {e}')

# List TIFs in GCS bucket
import subprocess
result = subprocess.run(
    ['gsutil', 'ls', f'{GCS_BUCKET}/*.tif'],
    capture_output=True, text=True
)
tif_paths = [p.strip() for p in result.stdout.strip().split('\n') if p.strip()]
print(f'\nFound {len(tif_paths)} TIFs in GCS')

# Ingest each TIF as a GEE asset
print('\nStarting ingestion...')
task_ids = []
for gcs_path in tif_paths:
    filename = gcs_path.split('/')[-1].replace('.tif', '')
    asset_id = f'{ASSET_FOLDER}/{filename}'
    request = {
        'name': asset_id,
        'tilesets': [{'sources': [{'uris': [gcs_path]}]}],
    }
    task = ee.data.startIngestion(ee.data.newTaskId()[0], request)
    task_ids.append((filename, task['id']))
    print(f'  Queued: {filename}')

print(f'\nAll {len(task_ids)} ingestion tasks submitted.')
print('Monitor progress at: https://code.earthengine.google.com/tasks')
