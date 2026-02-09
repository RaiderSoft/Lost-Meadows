// =====================================================
// MEADOW PROBABILITY VISUALIZATION
// =====================================================

// Load the meadow probability raster
var meadowProb = ee.Image('projects/lost-meadows/assets/meadow_probability');

// Load the original study area for context
var studyArea = ee.Geometry.Rectangle([-124.62, 41.78, -121.78, 43.36]);

// Center the map on the study area
Map.centerObject(studyArea, 10);

// Add base imagery
Map.addLayer(
  ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
    .filterBounds(studyArea)
    .filterDate('2023-06-01', '2023-09-30')
    .median()
    .clip(studyArea),
  {bands: ['B4', 'B3', 'B2'], min: 0, max: 3000},
  'Satellite Imagery',
  false
);

// Visualize probability as a color gradient
var probVis = {
  min: 0,
  max: 1,
  palette: ['white', 'yellow', 'orange', 'red', 'darkred']
};

Map.addLayer(
  meadowProb,
  probVis,
  'Meadow Probability (0-1)'
);

// Visualize high-confidence meadows (>0.5 threshold from paper)
var highConfidence = meadowProb.gt(0.5);
Map.addLayer(
  highConfidence.selfMask(),
  {palette: ['green']},
  'High Confidence Meadows (>0.5)'
);

// Add watershed outline
var watersheds = ee.FeatureCollection('USGS/WBD/2017/HUC10')
  .filterBounds(studyArea);
  
Map.addLayer(
  watersheds.style({color: 'red', fillColor: '00000000', width: 2}),
  {},
  'Study Watersheds'
);

// Create a legend
var legend = ui.Panel({
  style: {
    position: 'bottom-left',
    padding: '8px 15px'
  }
});

var legendTitle = ui.Label({
  value: 'Meadow Probability',
  style: {fontWeight: 'bold', fontSize: '16px', margin: '0 0 4px 0'}
});
legend.add(legendTitle);

// Add color bar
var colors = ['white', 'yellow', 'orange', 'red', 'darkred'];
var labels = ['0.0', '0.25', '0.5', '0.75', '1.0'];

colors.forEach(function(color, i) {
  var colorBox = ui.Label({
    style: {
      backgroundColor: color,
      padding: '8px',
      margin: '0 0 4px 0'
    }
  });
  var description = ui.Label({
    value: labels[i],
    style: {margin: '0 0 4px 6px'}
  });
  
  var panel = ui.Panel({
    widgets: [colorBox, description],
    layout: ui.Panel.Layout.Flow('horizontal')
  });
  
  legend.add(panel);
});

Map.add(legend);

// Add title panel
var title = ui.Panel({
  style: {
    position: 'top-center',
    padding: '8px 15px',
    backgroundColor: 'white'
  }
});

title.add(ui.Label({
  value: 'Lost Meadow Detection - Test Watershed',
  style: {fontSize: '20px', fontWeight: 'bold'}
}));

title.add(ui.Label({
  value: 'Random Forest Model (Synthetic Training Data)',
  style: {fontSize: '14px', color: 'gray'}
}));

Map.add(title);

print('Meadow Probability Statistics:');
print('Study Area:', studyArea);
print('Total predicted meadow area (>0.5): ~5072 hectares');