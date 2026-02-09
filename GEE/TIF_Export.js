// Load USGS HUC10 watershed boundaries
var watersheds = ee.FeatureCollection('USGS/WBD/2017/HUC10');
var studyWatersheds = watersheds.filterBounds(studyArea);
var studyAreaRefined = studyWatersheds.union().geometry();

// Visualize
var outline = ee.Image().byte().paint({
  featureCollection: studyWatersheds,
  color: 1,
  width: 2
});
Map.addLayer(outline, {palette: ['red']}, 'Study Watersheds');
Map.centerObject(studyArea, 8);

// =======================================================
// LOAD 3DEP DEM - RAW ELEVATION ONLY
// =======================================================
var dem3DEP = ee.ImageCollection('USGS/3DEP/10m_collection')
  .filterBounds(studyAreaRefined)
  .mosaic()
  .clip(studyAreaRefined);

var elevation = dem3DEP.select('elevation');

// =======================================================
// VISUALIZATION
// =======================================================
// Check elevation range
var elevStats = elevation.reduceRegion({
  reducer: ee.Reducer.minMax(),
  geometry: studyAreaRefined,
  scale: 100,
  maxPixels: 1e9,
  bestEffort: true
});

print('Elevation Statistics:', elevStats);

// Elevation visualization
Map.addLayer(elevation, {
  min: 0,
  max: 4000,
  palette: ['001f3f', '0074D9', '7FDBFF', '39CCCC', '3D9970', 
            '2ECC40', '01FF70', 'FFDC00', 'FF851B', 'FF4136']
}, '3DEP Elevation (Raw)');

// Hillshade for context (just for visualization, won't export)
var hillshade = ee.Terrain.hillshade(elevation);
Map.addLayer(hillshade, {
  min: 0,
  max: 255,
  opacity: 0.5
}, 'Hillshade (visual only)', false);

// =======================================================
// EXPORT: GEOTIFF RASTER (ELEVATION ONLY)
// =======================================================
Export.image.toDrive({
  image: elevation,
  description: '3DEP_10m_elevation_raster',
  folder: 'GEE_Exports',
  fileNamePrefix: '3DEP_10m_elevation_only',
  region: studyAreaRefined,
  scale: 10,
  maxPixels: 1e13,
  fileFormat: 'GeoTIFF',
  formatOptions: {
    cloudOptimized: true
  }
});

// =======================================================
// DIAGNOSTICS
// =======================================================
print('Study area (km²):', studyAreaRefined.area().divide(1e6));
print('Number of watersheds:', studyWatersheds.size());

// Estimate file size
var areaKm2 = studyAreaRefined.area().divide(1e6);
var estimatedPixels = areaKm2.multiply(10000);
var estimatedSizeMB = estimatedPixels.multiply(0.00004); // rough estimate for GeoTIFF
print('Estimated GeoTIFF size (MB):', estimatedSizeMB);