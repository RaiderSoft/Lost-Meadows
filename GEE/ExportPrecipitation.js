// Export PRISM Precipitation Data for Watersheds
// PRISM provides high-resolution climate data for the contiguous US
// Resolution: ~800m (0.008333 degrees)

// ============================================================
// CONFIGURATION - Edit these values
// ============================================================

// Watershed bounds (get from your DEM or define manually)
var studyArea = ee.Geometry.Polygon(
  [[[-124.65, 41.8],
    [-121.75, 41.8],
    [-121.75, 43.35],
    [-124.65, 43.35],
    [-124.65, 41.8]]]
);

// Output settings
var watershedName = 'Hunter_Creek_1710031205';
var exportScale = 800;  // meters (PRISM native resolution)

// ============================================================
// PRISM CLIMATE DATA
// ============================================================

// Annual precipitation (30-year normal: 1991-2020)
var prismAnnual = ee.ImageCollection('OREGONSTATE/PRISM/AN81m')
  .filter(ee.Filter.date('2014-01-01', '2014-12-31'))
  .select('ppt')  // precipitation
  .first()
  .clip(studyArea);

// Monthly precipitation (for seasonal analysis)
// Get average precipitation for each month across multiple years
var months = ee.List.sequence(1, 12);

var monthlyPrecip = months.map(function(month) {
  var filtered = ee.ImageCollection('OREGONSTATE/PRISM/AN81m')
    .filter(ee.Filter.calendarRange(month, month, 'month'))
    .select('ppt')
    .mean()
    .clip(studyArea);
  return filtered.set('month', month);
});

// Seasonal precipitation (average monthly value for that season)
var springPrecip = ee.ImageCollection('OREGONSTATE/PRISM/AN81m')
  .filter(ee.Filter.date('2010-01-01', '2020-12-31'))  // 10-year average
  .filter(ee.Filter.calendarRange(3, 5, 'month'))       // March-May only
  .select('ppt')
  .mean()  // Average monthly spring precipitation
  .clip(studyArea);

var summerPrecip = ee.ImageCollection('OREGONSTATE/PRISM/AN81m')
  .filter(ee.Filter.calendarRange(6, 8, 'month'))  // June-August
  .select('ppt')
  .sum()
  .clip(studyArea);

var fallPrecip = ee.ImageCollection('OREGONSTATE/PRISM/AN81m')
  .filter(ee.Filter.calendarRange(9, 11, 'month'))  // Sept-Nov
  .select('ppt')
  .sum()
  .clip(studyArea);

var winterPrecip = ee.ImageCollection('OREGONSTATE/PRISM/AN81m')
  .filter(ee.Filter.calendarRange(12, 2, 'month'))  // Dec-Feb
  .select('ppt')
  .sum()
  .clip(studyArea);

// ============================================================
// VISUALIZATION
// ============================================================

// Center map on study area
Map.centerObject(studyArea, 8);

// Add layers
Map.addLayer(studyArea, {color: 'red'}, 'Study Area Boundary');
Map.addLayer(prismAnnual, {
  min: 0,
  max: 3000,
  palette: ['white', 'blue', 'darkblue']
}, 'Annual Precipitation (mm)');

Map.addLayer(springPrecip, {
  min: 0,
  max: 800,
  palette: ['white', 'lightblue', 'blue']
}, 'Spring Precipitation (mm)');

// ============================================================
// EXPORT TO GOOGLE DRIVE
// ============================================================

// Export annual precipitation
Export.image.toDrive({
  image: prismAnnual,
  description: 'SouthernOregon_PRISM_Annual_Precipitation',
  folder: 'GEE_Exports',
  fileNamePrefix: 'SouthernOregon_precip_annual',
  region: studyArea,
  scale: exportScale,
  crs: 'EPSG:4326',
  maxPixels: 1e13
});

// Export seasonal precipitation
Export.image.toDrive({
  image: springPrecip.rename('spring_ppt'),
  description: 'SouthernOregon_PRISM_Spring_Precipitation',
  folder: 'GEE_Exports',
  fileNamePrefix: 'SouthernOregon_precip_spring',
  region: studyArea,
  scale: exportScale,
  crs: 'EPSG:4326',
  maxPixels: 1e13
});

Export.image.toDrive({
  image: summerPrecip.rename('summer_ppt'),
  description: 'SouthernOregon_PRISM_Summer_Precipitation',
  folder: 'GEE_Exports',
  fileNamePrefix: 'SouthernOregon_precip_summer',
  region: studyArea,
  scale: exportScale,
  crs: 'EPSG:4326',
  maxPixels: 1e13
});

Export.image.toDrive({
  image: fallPrecip.rename('fall_ppt'),
  description: 'SouthernOregon_PRISM_Fall_Precipitation',
  folder: 'GEE_Exports',
  fileNamePrefix: 'SouthernOregon_precip_fall',
  region: studyArea,
  scale: exportScale,
  crs: 'EPSG:4326',
  maxPixels: 1e13
});

Export.image.toDrive({
  image: winterPrecip.rename('winter_ppt'),
  description: 'SouthernOregon_PRISM_Winter_Precipitation',
  folder: 'GEE_Exports',
  fileNamePrefix: 'SouthernOregon_precip_winter',
  region: studyArea,
  scale: exportScale,
  crs: 'EPSG:4326',
  maxPixels: 1e13
});

// ============================================================
// INFORMATION
// ============================================================

print('======================================');
print('PRISM Precipitation Export Ready');
print('======================================');
print('Study Area: Southern Oregon');
print('Bounds:', studyArea.coordinates());
print('Export Scale:', exportScale, 'meters');
print('');
print('PRISM Dataset: OREGONSTATE/PRISM/AN81m');
print('Resolution: ~800m (4km² grid cells)');
print('Time Period: 30-year normals');
print('');
print('Layers to Export:');
print('1. Annual Precipitation (mm/year)');
print('2. Spring Precipitation (mm) - March-May');
print('3. Summer Precipitation (mm) - June-August');
print('4. Fall Precipitation (mm) - Sept-Nov');
print('5. Winter Precipitation (mm) - Dec-Feb');
print('');
print('Click "Run" then go to Tasks tab to start exports');
print('Files will be saved to Google Drive > GEE_Exports/');
