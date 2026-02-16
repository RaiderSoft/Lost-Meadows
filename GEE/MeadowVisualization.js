// =====================================================
// ENHANCED MEADOW PROBABILITY VISUALIZATION
// Flexible, works with any uploaded probability raster
// =====================================================

// ========================================
// CONFIGURATION - EDIT THIS SECTION
// ========================================

// PASTE YOUR ASSET ID HERE 
// Example: 'projects/your-project/assets/Hunter_Creek_1710031205_meadow_probability'
var assetId = 'projects/lost-meadows/assets/meadow_probability_HC';

// Optional: Manually set study area bounds [west, south, east, north]
// Leave as null to auto-detect from raster
var manualBounds = null; // e.g., [-122.0, 41.46, -121.73, 41.85]

// ========================================
// LOAD DATA
// ========================================

// Load the meadow probability raster
var meadowProb = ee.Image(assetId);

// Get study area from raster bounds or manual input
var studyArea = manualBounds
  ? ee.Geometry.Rectangle(manualBounds)
  : meadowProb.geometry();

// Center map on study area
Map.centerObject(studyArea, 12);

// ========================================
// BASE LAYERS
// ========================================

// Create a mask from the meadow probability raster (to match watershed shape)
var watershedMask = meadowProb.mask();

// Add satellite imagery for context (recent summer imagery)
var satellite = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
  .filterBounds(studyArea)
  .filterDate('2023-06-01', '2023-09-30')
  .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
  .median()
  .clip(studyArea)
  .updateMask(watershedMask);  // Match watershed shape, not bounding box

Map.addLayer(
  satellite,
  {bands: ['B4', 'B3', 'B2'], min: 0, max: 3000},
  'Satellite Imagery (Summer)',
  false
);

// ========================================
// MEADOW PROBABILITY VISUALIZATIONS
// ========================================

// Visualization 1: Continuous probability (terrain-inspired palette)
var probVisTerrain = {
  min: 0,
  max: 1,
  palette: [
    '#f7fbff',  // Very low (white-blue)
    '#deebf7',
    '#c6dbef',
    '#9ecae1',
    '#6baed6',  // Medium (blue)
    '#4292c6',
    '#2171b5',
    '#08519c',
    '#08306b'   // High (dark blue)
  ]
};

// Visualization 2: Heatmap style (warm colors)
var probVisHeat = {
  min: 0,
  max: 1,
  palette: [
    '#ffffcc',  // Low (pale yellow)
    '#ffeda0',
    '#fed976',
    '#feb24c',
    '#fd8d3c',  // Medium (orange)
    '#fc4e2a',
    '#e31a1c',
    '#bd0026',
    '#800026'   // High (dark red)
  ]
};

// Visualization 3: Green meadow palette
var probVisGreen = {
  min: 0,
  max: 1,
  palette: [
    '#f7fcf5',  // Low (pale green)
    '#e5f5e0',
    '#c7e9c0',
    '#a1d99b',
    '#74c476',  // Medium (green)
    '#41ab5d',
    '#238b45',
    '#006d2c',
    '#00441b'   // High (dark green)
  ]
};

// Add probability layers (default: terrain palette)
Map.addLayer(
  meadowProb,
  probVisTerrain,
  'Probability - Terrain Palette',
  true,
  0.7  // 70% opacity
);

Map.addLayer(
  meadowProb,
  probVisHeat,
  'Probability - Heat Palette',
  false,
  0.7
);

Map.addLayer(
  meadowProb,
  probVisGreen,
  'Probability - Green Palette',
  false,
  0.7
);

// ========================================
// THRESHOLD LAYERS
// ========================================

// High confidence (>0.7)
var highConfidence = meadowProb.gt(0.7);
Map.addLayer(
  highConfidence.selfMask(),
  {palette: ['#006d2c']},  // Dark green
  'High Confidence (>0.7)',
  false
);

// Medium confidence (0.5-0.7)
var mediumConfidence = meadowProb.gt(0.5).and(meadowProb.lte(0.7));
Map.addLayer(
  mediumConfidence.selfMask(),
  {palette: ['#74c476']},  // Medium green
  'Medium Confidence (0.5-0.7)',
  false
);

// Standard threshold (>0.5 from paper)
var standardThreshold = meadowProb.gt(0.5);
Map.addLayer(
  standardThreshold.selfMask(),
  {palette: ['#238b45']},
  'Standard Threshold (>0.5)',
  true
);

// ========================================
// UI PANELS
// ========================================

// Title Panel
var titlePanel = ui.Panel({
  style: {
    position: 'top-center',
    padding: '10px 20px',
    backgroundColor: 'rgba(255, 255, 255, 0.95)',
    border: '2px solid #2171b5'
  }
});

titlePanel.add(ui.Label({
  value: '🌿 Lost Meadows Detection',
  style: {
    fontSize: '22px',
    fontWeight: 'bold',
    color: '#08519c',
    margin: '0'
  }
}));

Map.add(titlePanel);

// ========================================
// LEGEND
// ========================================

var legendPanel = ui.Panel({
  style: {
    position: 'bottom-left',
    padding: '10px 15px',
    backgroundColor: 'rgba(255, 255, 255, 0.95)',
    border: '1px solid #ccc'
  }
});

legendPanel.add(ui.Label({
  value: 'Meadow Probability',
  style: {
    fontWeight: 'bold',
    fontSize: '16px',
    margin: '0 0 10px 0',
    color: '#333'
  }
}));

// Threshold guide
legendPanel.add(ui.Label({
  value: 'Classification Thresholds:',
  style: {fontWeight: 'bold', fontSize: '13px', margin: '10px 0 5px 0'}
}));

var thresholdInfo = [
  {color: '#006d2c', label: '>0.7 - High Confidence'},
  {color: '#74c476', label: '0.5-0.7 - Medium Confidence'},
  {color: '#c7e9c0', label: '<0.5 - Low Confidence'}
];

thresholdInfo.forEach(function(item) {
  var row = ui.Panel({
    widgets: [
      ui.Label({
        style: {
          backgroundColor: item.color,
          padding: '10px',
          margin: '2px 8px 2px 0',
          border: '1px solid #333'
        }
      }),
      ui.Label({
        value: item.label,
        style: {fontSize: '12px', margin: '2px 0'}
      })
    ],
    layout: ui.Panel.Layout.Flow('horizontal')
  });
  legendPanel.add(row);
});

Map.add(legendPanel);

// ========================================
// INTERACTIVE CLICK FUNCTIONALITY
// ========================================

Map.onClick(function(coords) {
  var point = ee.Geometry.Point([coords.lon, coords.lat]);
  var value = meadowProb.reduceRegion({
    reducer: ee.Reducer.first(),
    geometry: point,
    scale: 10
  });

  value.evaluate(function(val) {
    if (val && val.b1 !== null) {
      var prob = val.b1;
      var confidence = prob > 0.7 ? 'High' : (prob > 0.5 ? 'Medium' : 'Low');

      print('📍 Clicked Location:');
      print('  Coordinates: ' + coords.lon.toFixed(5) + ', ' + coords.lat.toFixed(5));
      print('  Meadow Probability: ' + prob.toFixed(4));
      print('  Confidence: ' + confidence);

      // Add marker
      var marker = ui.Map.Layer(point, {color: 'red'}, 'Clicked Point');
      Map.layers().set(Map.layers().length(), marker);
    }
  });
});

// ========================================
// INITIAL PRINT STATEMENTS
// ========================================

print('🌿 Lost Meadows Detection - Loaded Successfully!');
print('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
print('Asset ID:', assetId);
print('');
print('💡 Quick Guide:');
print('  • Toggle layers to explore different color palettes');
print('  • Click anywhere on the map for probability values');
print('  • Adjust layer opacity in Layers panel (top-right)');
print('  • Use threshold layers to see classified meadows');
print('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
