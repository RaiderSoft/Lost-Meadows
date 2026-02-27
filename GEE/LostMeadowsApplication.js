// ============================================================
// Meadow Probability Viewer — Google Earth Engine App
// ============================================================


var ASSET_ID    = 'projects/lost-meadows/assets/MeadowPredictions/Bear_Creek_1710030801_xgboost_model_probability20_80';
var BAND_NAME   = 'b1';
var VALUE_SCALE = 1;

// ============================================================
// IMAGE PREP
// ============================================================

var raw  = ee.Image(ASSET_ID).select(BAND_NAME);
var prob = raw.divide(VALUE_SCALE);

var PALETTES = {
  'Blue':        ['#f7fbff', '#c6dbef', '#6baed6', '#2171b5', '#084594'],
  'Red':         ['#fff5f0', '#fcbba1', '#fb6a4a', '#cb181d', '#67000d'],
  'Blue-Red':    ['#2166ac', '#92c5de', '#f7f7f7', '#f4a582', '#d6604d'],
  'Teal-Yellow': ['#ffffcc', '#a1dab4', '#41b6c4', '#2c7fb8', '#253494']
};

var currentPalette = PALETTES['Blue'];

// ============================================================
// UI LAYOUT — Sidebar + Map
// ============================================================

ui.root.clear();

var map = ui.Map();
map.setOptions('HYBRID');
map.setControlVisibility({ fullscreenControl: false, layerList: false });

var sidebar = ui.Panel({
  style: { width: '300px', padding: '10px', backgroundColor: '#f5f5f5' }
});

ui.root.add(ui.SplitPanel({
  firstPanel: sidebar,
  secondPanel: map,
  orientation: 'horizontal',
  wipe: false
}));

// ============================================================
// SIDEBAR HELPER FUNCTIONS
// ============================================================

function sectionLabel(text) {
  return ui.Label(text, {
    fontWeight: 'bold', fontSize: '14px', color: '#333333',
    margin: '12px 0 4px 0'
  });
}

function bodyLabel(text) {
  return ui.Label(text, {
    fontSize: '11px', color: '#666666', margin: '0 0 6px 0'
  });
}

function divider() {
  return ui.Panel({ style: {
    height: '1px', backgroundColor: '#cccccc',
    margin: '10px 0 10px 0', stretch: 'horizontal'
  }});
}

// ============================================================
// TITLE
// ============================================================

sidebar.add(ui.Label('🌿 Meadow Probability', {
  fontWeight: 'bold', fontSize: '20px', color: '#2c3e50', margin: '0 0 2px 0'
}));

sidebar.add(divider());

// ============================================================
// LAYER CONTROLS
// ============================================================

sidebar.add(sectionLabel('Layer Controls'));

var toggleCheck = ui.Checkbox({
  label: 'Show Meadow Probability Layer',
  value: true,
  style: { fontSize: '12px', color: '#333333', margin: '2px 0 8px 0' }
});
sidebar.add(toggleCheck);

sidebar.add(bodyLabel('Opacity'));
var opacitySlider = ui.Slider({
  min: 0, max: 1, value: 0.85, step: 0.05,
  style: { stretch: 'horizontal', margin: '0 0 4px 0' }
});
sidebar.add(opacitySlider);

sidebar.add(bodyLabel('Probability Threshold — hide pixels below:'));
var thresholdSlider = ui.Slider({
  min: 0, max: 0.95, value: 0, step: 0.05,
  style: { stretch: 'horizontal', margin: '0 0 2px 0' }
});
sidebar.add(thresholdSlider);

var thresholdReadout = ui.Label('Threshold: 0.00', {
  fontSize: '11px', color: '#2171b5', margin: '0 0 4px 0'
});
sidebar.add(thresholdReadout);

sidebar.add(divider());

// ============================================================
// COLOR SCHEME SELECTOR
// ============================================================

sidebar.add(sectionLabel('Color Scheme'));

var paletteSelect = ui.Select({
  items: Object.keys(PALETTES),
  value: 'Blue',
  style: { stretch: 'horizontal', margin: '0 0 4px 0' }
});
paletteSelect.onChange(function(val) {
  currentPalette = PALETTES[val];
  updateLegend();
  updateLayer();
});
sidebar.add(paletteSelect);

sidebar.add(divider());

// ============================================================
// BASEMAP SELECTOR
// ============================================================

sidebar.add(sectionLabel('Basemap'));
var basemapSelect = ui.Select({
  items: ['HYBRID', 'SATELLITE', 'TERRAIN', 'ROADMAP'],
  value: 'HYBRID',
  style: { stretch: 'horizontal', margin: '0 0 4px 0' }
});
basemapSelect.onChange(function(val) { map.setOptions(val); });
sidebar.add(basemapSelect);

sidebar.add(divider());

// ============================================================
// LEGEND
// ============================================================

sidebar.add(sectionLabel('Legend'));

var legendPanel = ui.Panel({ style: { margin: '0 0 6px 0' } });
sidebar.add(legendPanel);

function updateLegend() {
  legendPanel.clear();
  var gradientBar = ui.Thumbnail({
    image: ee.Image.pixelLonLat().select('longitude')
      .unitScale(-180, 180)
      .visualize({ min: 0, max: 1, palette: currentPalette }),
    params: { bbox: '-180,-10,180,10', dimensions: '255x16', format: 'png' },
    style: { stretch: 'horizontal', margin: '0', height: '16px' }
  });
  legendPanel.add(gradientBar);
  legendPanel.add(ui.Panel([
    ui.Label('0 — Low',  { fontSize: '10px', color: '#555', margin: '2px 0' }),
    ui.Label('0.5',      { fontSize: '10px', color: '#555', margin: '2px 0', textAlign: 'center' }),
    ui.Label('1 — High', { fontSize: '10px', color: '#555', margin: '2px 0', textAlign: 'right' })
  ], ui.Panel.Layout.flow('horizontal'), { stretch: 'horizontal' }));
}

updateLegend();

sidebar.add(divider());

// ============================================================
// AREA STATISTICS
// ============================================================

sidebar.add(sectionLabel('Area Statistics'));
sidebar.add(bodyLabel('Estimate meadow area above threshold within the current map view.'));

var statsOutput = ui.Label('—', {
  fontSize: '12px', color: '#2c3e50', margin: '2px 0 6px 0'
});
sidebar.add(statsOutput);

var statsButton = ui.Button({
  label: '📊 Compute Statistics',
  style: { stretch: 'horizontal', margin: '0 0 4px 0' }
});
sidebar.add(statsButton);

statsButton.onClick(function() {
  statsOutput.setValue('Computing… (may take a few seconds)');
  var bounds = map.getBounds();
  var region = bounds
    ? ee.Geometry.Rectangle([bounds.west, bounds.south, bounds.east, bounds.north])
    : prob.geometry();
  var threshold = thresholdSlider.getValue();
  var masked = prob.updateMask(prob.gte(threshold));

  masked.reduceRegion({
    reducer: ee.Reducer.mean().combine(ee.Reducer.stdDev(), '', true)
                             .combine(ee.Reducer.count(), '', true),
    geometry: region, scale: 30, maxPixels: 1e10, bestEffort: true
  }).evaluate(function(stats) {
    var mean = stats[BAND_NAME + '_mean'];
    var std  = stats[BAND_NAME + '_stdDev'];
    var cnt  = stats[BAND_NAME + '_count'];
    if (mean === null || mean === undefined ||
        std  === null || std  === undefined ||
        cnt  === null || cnt  === undefined) {
      statsOutput.setValue('No data in current view.');
      return;
    }
    var areaHa = (cnt * 900 / 10000).toFixed(0);
    statsOutput.setValue(
      'Mean probability: ' + mean.toFixed(3) + '\n' +
      'Std deviation:    ' + std.toFixed(3) + '\n' +
      'Pixels above threshold: ' + Number(cnt).toLocaleString() + '\n' +
      'Approx. area ≥ threshold: ' + Number(areaHa).toLocaleString() + ' ha'
    );
  });
});

sidebar.add(divider());

// ============================================================
// PIXEL INSPECTOR
// ============================================================

sidebar.add(sectionLabel('Pixel Inspector'));
sidebar.add(bodyLabel('Click anywhere on the map to inspect the probability value at that location.'));

var clickOutput = ui.Label('Click the map to inspect…', {
  fontSize: '12px', color: '#2c3e50', margin: '2px 0 10px 0'
});
sidebar.add(clickOutput);

map.onClick(function(coords) {
  clickOutput.setValue('Sampling…');
  var point = ee.Geometry.Point([coords.lon, coords.lat]);
  prob.sample({ region: point, scale: 30, numPixels: 1 })
    .first()
    .get(BAND_NAME)
    .evaluate(function(val) {
      if (val === null) {
        clickOutput.setValue('No data at this location.');
      } else {
        clickOutput.setValue(
          'Lon: ' + coords.lon.toFixed(5) + '\n' +
          'Lat: ' + coords.lat.toFixed(5) + '\n' +
          'Meadow Probability: ' + val.toFixed(4)
        );
      }
    });
});

sidebar.add(divider());

// ============================================================
// MAIN LAYER RENDER FUNCTION
// ============================================================

var currentLayer = null;

function updateLayer() {
  var threshold = thresholdSlider.getValue();
  var opacity   = opacitySlider.getValue();
  var visible   = toggleCheck.getValue();

  thresholdReadout.setValue('Threshold: ' + threshold.toFixed(2));

  var display = prob.updateMask(prob.gte(threshold));
  if (currentLayer) map.remove(currentLayer);
  currentLayer = ui.Map.Layer(
    display,
    { min: 0, max: 1, palette: currentPalette },
    'Meadow Probability',
    visible,
    opacity
  );
  map.add(currentLayer);
}

opacitySlider.onChange(updateLayer);
thresholdSlider.onChange(updateLayer);
toggleCheck.onChange(updateLayer);

// ============================================================
// INITIALIZE
// ============================================================

map.centerObject(prob, 10);
updateLayer();