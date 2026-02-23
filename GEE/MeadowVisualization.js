// Import the meadow probability raster as an asset
var meadowProb = ee.Image('projects/lost-meadows/assets/Bear_Creek_1710030801_xgboost_model_probability');

// Print image information to the console
print('Meadow Probability Image:', meadowProb);

// Get the image bounds and center the map
var bounds = meadowProb.geometry();
Map.centerObject(bounds, 12);

// Define visualization parameters for probability (0-1 scale)
var probVis = {
  min: 0,
  max: 1,
  palette: [
    '#440154', // Low probability (purple)
    '#3b528b', // 
    '#21918c', // Medium-low (teal)
    '#5ec962', // Medium-high (green)
    '#fde724'  // High probability (yellow)
  ]
};

// Add the meadow probability layer to the map
Map.addLayer(meadowProb, probVis, 'Meadow Probability');

// Alternative visualization: Binary threshold
// Show areas with >50% probability of being meadow
var meadowBinary = meadowProb.gt(0.5);
Map.addLayer(meadowBinary, {min: 0, max: 1, palette: ['white', 'darkgreen']},
             'Meadow (>50%)', false);

// Confidence threshold layers
Map.addLayer(meadowProb.gt(0.6).selfMask(), {palette: ['#41ab5d']}, 'Threshold >0.6', false);
Map.addLayer(meadowProb.gt(0.7).selfMask(), {palette: ['#238b45']}, 'Threshold >0.7', false);
Map.addLayer(meadowProb.gt(0.8).selfMask(), {palette: ['#006d2c']}, 'Threshold >0.8', false);
Map.addLayer(meadowProb.gt(0.9).selfMask(), {palette: ['#00441b']}, 'Threshold >0.9', false);

// Add a legend
var legend = ui.Panel({
  style: {
    position: 'bottom-left',
    padding: '8px 15px'
  }
});

var legendTitle = ui.Label({
  value: 'Meadow Probability',
  style: {
    fontWeight: 'bold',
    fontSize: '16px',
    margin: '0 0 4px 0',
    padding: '0'
  }
});
legend.add(legendTitle);

// Create color bar
var makeRow = function(color, name) {
  var colorBox = ui.Label({
    style: {
      backgroundColor: color,
      padding: '8px',
      margin: '0 0 4px 0'
    }
  });
  var description = ui.Label({
    value: name,
    style: {margin: '0 0 4px 6px'}
  });
  return ui.Panel({
    widgets: [colorBox, description],
    layout: ui.Panel.Layout.Flow('horizontal')
  });
};

legend.add(makeRow('#440154', 'Low (0.0)'));
legend.add(makeRow('#3b528b', '0.25'));
legend.add(makeRow('#21918c', '0.50'));
legend.add(makeRow('#5ec962', '0.75'));
legend.add(makeRow('#fde724', 'High (1.0)'));

Map.add(legend);

// Calculate and print statistics
var stats = meadowProb.reduceRegion({
  reducer: ee.Reducer.mean()
    .combine(ee.Reducer.min(), '', true)
    .combine(ee.Reducer.max(), '', true)
    .combine(ee.Reducer.stdDev(), '', true),
  geometry: bounds,
  scale: 30, // Adjust based on your actual pixel size
  maxPixels: 1e9
});

print('Statistics:', stats);

// Calculate area of high-probability meadows (>0.7)
var highProbArea = meadowProb.gt(0.7);
var areaImage = highProbArea.multiply(ee.Image.pixelArea());
var area = areaImage.reduceRegion({
  reducer: ee.Reducer.sum(),
  geometry: bounds,
  scale: 30,
  maxPixels: 1e9
});

print('High probability meadow area (m²):', area);
print('High probability meadow area (acres):', 
      ee.Number(area.get('b1')).divide(4046.86));