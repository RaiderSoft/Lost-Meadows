import ee
import google.auth
credentials, _ = google.auth.default()
ee.Initialize(credentials=credentials, project='lost-meadows')
print('Connected!')
assets = ee.data.listAssets({'parent': 'projects/lost-meadows/assets/Predictions'})
print(f'Assets ready: {len(assets.get("assets", []))}')
