"""
Set all assets in the GlobalPredictions folder to public read.
"""
import ee
import google.auth

PROJECT = 'lost-meadows'
ASSET_FOLDER = 'projects/lost-meadows/assets/GlobalPredictions'

credentials, _ = google.auth.default()
ee.Initialize(credentials=credentials, project=PROJECT)
print('Connected to Earth Engine')

assets = ee.data.listAssets({'parent': ASSET_FOLDER}).get('assets', [])
print(f'Setting public ACL on {len(assets)} assets...')

for asset in assets:
    asset_id = asset['name']
    acl = ee.data.getAssetAcl(asset_id)
    acl['all_users_can_read'] = True
    ee.data.setAssetAcl(asset_id, acl)
    print(f'  ✓ {asset_id.split("/")[-1]}')

print(f'\nDone! {len(assets)} assets are now public.')
