// =====================================================
// MEADOW PROBABILITY VISUALIZATION - REAL WETLAND DATA
// =====================================================

// Load the meadow probability raster (trained on REAL wetlands)
var meadowProb = ee.Image('projects/lost-meadows/assets/meadow_probability_real');

// Load the original study area for context
var studyArea = ee.Geometry.Rectangle([-122.0, 41.46, -121.73, 41.85]);

// Center the map on the study area
Map.centerObject(studyArea, 11);

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
  'Wetland Probability (0-1)'
);

// Visualize high-confidence wetlands (>0.5 threshold from paper)
var highConfidence = meadowProb.gt(0.5);
Map.addLayer(
  highConfidence.selfMask(),
  {palette: ['green']},
  'High Confidence Wetlands (>0.5)',
  true
);

// Add title panel
var title = ui.Panel({
  style: {
    position: 'top-center',
    padding: '8px 15px',
    backgroundColor: 'white'
  }
});

title.add(ui.Label({
  value: 'Wetland Detection - Real Training Data',
  style: {fontSize: '20px', fontWeight: 'bold'}
}));

title.add(ui.Label({
  value: 'Random Forest Model (AUC: 0.845) | 729 hectares predicted',
  style: {fontSize: '14px', color: 'gray'}
}));

Map.add(title);

// Add legend
var legend = ui.Panel({
  style: {
    position: 'bottom-left',
    padding: '8px 15px'
  }
});

var legendTitle = ui.Label({
  value: 'Wetland Probability',
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

print('Wetland Probability Statistics:');
print('Study Area:', studyArea);
print('Model Performance: AUC 0.845');
print('Predicted high-confidence wetlands: ~729 hectares (1.42% of watershed)');