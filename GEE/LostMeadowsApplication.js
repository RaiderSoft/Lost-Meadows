// ============================================================
// Meadow Probability Viewer — Google Earth Engine App
// ============================================================
// Description:
//   Interactive web application for visualizing XGBoost-generated
//   meadow restoration probability predictions across HUC10 watersheds
//   in Southern Oregon and Northern California.
//
// Data Inputs:
//   - Meadow probability raster: GEE Asset (XGBoost predictions, band 'b1')
//   - Watershed boundaries: HUC10 FeatureCollection (GEE Asset)
//
// Features:
//   - Watershed navigator with zoom + highlight
//   - Probability threshold masking
//   - Opacity control
//   - Multiple color palettes
//   - Basemap switcher
//   - Pixel inspector with error handling
//   - Gradient legend
//
// Project: Lost Meadows Conservation Science
// ============================================================

// ------------------------------------------------------------
// ASSET CONFIGURATION
// Change these values to point to different prediction rasters
// or watershed boundaries without modifying the rest of the app.
// ------------------------------------------------------------
var ASSET_ID =
  "projects/lost-meadows/assets/MeadowPredictions/Bear_Creek_23_Features_XGboost_2080";
var BAND_NAME = "b1"; // Band containing probability values (0–1 float)
var VALUE_SCALE = 1; // Divisor to normalize raw values if needed (e.g. 100 if stored as integers 0–100)
var WATERSHEDS =
  "projects/lost-meadows/assets/MeadowPredictions/study_watersheds_HUC10";

// ------------------------------------------------------------
// LOAD WATERSHED FEATURE COLLECTION
// Used for boundary rendering, watershed navigator, and
// pixel inspector spatial validation.
// ------------------------------------------------------------
var watershedFC = ee.FeatureCollection(WATERSHEDS);

// ------------------------------------------------------------
// WATERSHED NAMES LIST
// Hard-coded from the HUC10 'name' property for use in the
// dropdown navigator. Sorted alphabetically in the UI.
// Source: USGS WBD HUC10, filtered to study area bounding box.
// ------------------------------------------------------------
var watershedNames = [
  "Red Rock Valley-Antelope Creek",
  "Point Saint George-Frontal Pacific Ocean",
  "Badger Basin-Willow Creek",
  "Seiad Creek-Klamath River",
  "Horse Creek-Klamath River",
  "Yreka Creek-Shasta River",
  "Little Shasta River",
  "Humbug Creek-Klamath River",
  "Bogus Creek-Klamath River",
  "Ukonom Creek-Klamath River",
  "South Fork Smith River",
  "Clear Creek",
  "Swan Lake Valley",
  "Wood River",
  "Crater Lake-Williamson River",
  "Hog Creek-Williamson River",
  "Jack Creek-Williamson River",
  "Big Springs Creek-Klamath Marsh",
  "Beaver Marsh",
  "Sprague River",
  "Long Lake Valley-Upper Klamath Lake",
  "Fourmile Creek",
  "Lake Ewauna-Klamath River",
  "Spencer Creek",
  "Coos Bay-Frontal Pacific Ocean",
  "New River-Frontal Pacific Ocean",
  "Euchre Creek-Frontal Pacific Ocean",
  "Shady Cove-Rogue River",
  "Lost Creek-Rogue River",
  "Upper Umpqua River",
  "South Fork Coos River",
  "Calapooya Creek",
  "Deer Creek-South Umpqua River",
  "Olalla Creek-Lookingglass Creek",
  "Lower North Umpqua River",
  "Myrtle Creek",
  "Little River",
  "Dumont Creek-South Umpqua River",
  "Days Creek-South Umpqua River",
  "Clark Branch-South Umpqua River",
  "East Fork Coquille River",
  "North Fork Coquille River",
  "Coquille River",
  "South Fork Coquille River",
  "Sixes River",
  "Elk River",
  "Lobster Creek",
  "Stair Creek-Rogue River",
  "Middle Cow Creek",
  "Grave Creek",
  "Hellgate Canyon-Rogue River",
  "Jumpoff Joe Creek",
  "Indigo Creek",
  "Silver Creek",
  "Briggs Creek",
  "Shasta Costa Creek-Rogue River",
  "Rogue River",
  "Lawson Creek-Illinois River",
  "Hunter Creek",
  "Klondike Creek-Illinois River",
  "Pistol River",
  "Lower Applegate River",
  "Deer Creek",
  "Josephine Creek-Illinois River",
  "Chetco River",
  "Grants Pass-Rogue River",
  "Evans Creek",
  "Gold Hill-Rogue River",
  "Little Butte Creek",
  "Trail Creek",
  "Upper Cow Creek",
  "Elk Creek",
  "Jackson Creek",
  "Elk Creek",
  "Headwaters Rogue River",
  "South Fork Rogue River",
  "Big Butte Creek",
  "Diamond Lake",
  "Fish Creek",
  "Clearwater River",
  "Headwaters North Umpqua River",
  "Upper North Umpqua River",
  "Upper South Umpqua River",
  "Middle North Umpqua River",
  "Steamboat Creek",
  "Canton Creek",
  "Rock Creek",
  "Crescent Creek",
  "Upper Little Deschutes River",
  "Little Walker Mountain",
  "Middle Applegate River",
  "Williams Creek",
  "Upper Applegate River",
  "Little Applegate River",
  "Sucker Creek",
  "North Cove-Pacific Ocean",
  "171003060500-Pacific Ocean",
  "Bear Creek",
  "Lower Cow Creek",
  "Horseshoe Bend-Rogue River",
  "West Fork Cow Creek",
  "Middle Fork Coquille River",
  "Butte Valley",
  "Beaver Creek",
  "Smith River",
  "Cottonwood Creek",
  "Thompson Creek-Klamath River",
  "Indian Creek",
  "Middle Fork Smith River",
  "Lower Klamath Lake",
  "North Fork Smith River",
  "John C Boyle Reservoir-Klamath River",
  "Copco Reservoir-Klamath River",
  "Jenny Creek",
  "Whalehead Creek-Frontal Cape Ferrelo",
  "West Fork Illinois River",
  "Headwaters Applegate River",
  "East Fork Illinois River",
  "Althouse Creek",
  "Winchuck River",
  "Mack Arch Cove-Pacific Ocean",
  "Iron Gate Reservoir-Klamath River",
];

// ============================================================
// IMAGE PREP
// ============================================================

// Load the prediction raster and select the probability band.
// VALUE_SCALE allows normalization if predictions were stored as
// scaled integers rather than 0–1 floats (e.g. divide by 100).
var raw = ee.Image(ASSET_ID).select(BAND_NAME);
var prob = raw.divide(VALUE_SCALE);

// ------------------------------------------------------------
// COLOR PALETTES
// Each palette maps low (0) → high (1) probability values.
// Add additional palettes here as key-value pairs to expose
// them in the Color Scheme dropdown without other code changes.
// ------------------------------------------------------------
var PALETTES = {
  Blue: ["#f7fbff", "#c6dbef", "#6baed6", "#2171b5", "#084594"],
  Red: ["#fff5f0", "#fcbba1", "#fb6a4a", "#cb181d", "#67000d"],
  "Teal-Yellow": ["#ffffcc", "#a1dab4", "#41b6c4", "#2c7fb8", "#253494"],
};

// Tracks the active palette — updated when the user changes the color scheme
var currentPalette = PALETTES["Blue"];

// ============================================================
// UI LAYOUT — Sidebar + Map
// ============================================================

// Clear any default GEE UI elements before building the custom layout
ui.root.clear();

// Main map panel — defaults to hybrid satellite/road basemap
var map = ui.Map();
map.setOptions("HYBRID");
map.setControlVisibility({ fullscreenControl: false, layerList: false });

// Sidebar panel — fixed width left panel for all controls
var sidebar = ui.Panel({
  style: { width: "300px", padding: "10px", backgroundColor: "#f5f5f5" },
});

// Split layout: sidebar on left, map fills remaining space
ui.root.add(
  ui.SplitPanel({
    firstPanel: sidebar,
    secondPanel: map,
    orientation: "horizontal",
    wipe: false,
  }),
);

// ============================================================
// SIDEBAR HELPER FUNCTIONS
// Reusable UI component factories to keep styling consistent
// ============================================================

// Bold section header label
function sectionLabel(text) {
  return ui.Label(text, {
    fontWeight: "bold",
    fontSize: "14px",
    color: "#333333",
    margin: "12px 0 4px 0",
  });
}

// Smaller muted descriptive label for instructions/hints
function bodyLabel(text) {
  return ui.Label(text, {
    fontSize: "11px",
    color: "#666666",
    margin: "0 0 6px 0",
  });
}

// Thin horizontal rule for visual separation between sections
function divider() {
  return ui.Panel({
    style: {
      height: "1px",
      backgroundColor: "#cccccc",
      margin: "10px 0 10px 0",
      stretch: "horizontal",
    },
  });
}

// ============================================================
// TITLE
// ============================================================

sidebar.add(
  ui.Label("Meadow Probability", {
    fontWeight: "bold",
    fontSize: "20px",
    color: "#2c3e50",
    margin: "0 0 2px 0",
  }),
);

sidebar.add(divider());

// ============================================================
// WATERSHED NAVIGATOR
// Dropdown to select a watershed by name, zoom the map to its
// bounds, and render a yellow highlight outline over it.
// ============================================================

sidebar.add(sectionLabel("Watershed Navigator"));
sidebar.add(bodyLabel("Select a watershed to zoom to it."));

// Alphabetically sorted dropdown — GEE's ui.Select supports
// type-to-filter natively, so no separate search input is needed
var watershedSelect = ui.Select({
  items: watershedNames.sort(),
  placeholder: "Search or select a watershed…",
  style: { stretch: "horizontal", margin: "0 0 4px 0" },
});

watershedSelect.onChange(function (name) {
  // Filter the full FeatureCollection to just the selected watershed
  var selected = watershedFC.filter(ee.Filter.eq("name", name));

  // Zoom the map to fit the watershed's bounding box
  selected
    .first()
    .geometry()
    .bounds()
    .evaluate(function (bounds) {
      map.centerObject(ee.Geometry(bounds), 11);
    });

  // Paint the selected watershed border as a raster image so GEE
  // renders only the stroke with no fill — more reliable than
  // passing fillColor via ui.Map.Layer on a FeatureCollection
  var highlight = ee.Image().byte().paint({
    featureCollection: selected,
    color: 1,
    width: 3,
  });

  // Remove any previous highlight before adding the new one
  if (highlightLayer) map.remove(highlightLayer);
  highlightLayer = ui.Map.Layer(
    highlight,
    { palette: ["FFFF00"] }, // Yellow highlight for selected watershed
    "Selected Watershed",
    true,
    1,
  );
  map.add(highlightLayer);
});

sidebar.add(watershedSelect);

// Clear Selection button — removes highlight and resets the dropdown
var clearButton = ui.Button({
  label: "Clear Selection",
  style: { stretch: "horizontal", margin: "4px 0 0 0" },
  onClick: function () {
    if (highlightLayer) map.remove(highlightLayer);
    highlightLayer = null;
    watershedSelect.setValue(null);
  },
});
sidebar.add(clearButton);

// ============================================================
// LAYER CONTROLS
// Visibility toggle, opacity, and threshold masking for the
// main probability raster layer.
// ============================================================

sidebar.add(sectionLabel("Layer Controls"));

// Toggle visibility of the meadow probability raster entirely
var toggleCheck = ui.Checkbox({
  label: "Show Meadow Probability Layer",
  value: true,
  style: { fontSize: "12px", color: "#333333", margin: "2px 0 8px 0" },
});
sidebar.add(toggleCheck);

// Toggle visibility of the cyan watershed boundary outlines
var watershedCheck = ui.Checkbox({
  label: "Show Watershed Boundary",
  value: true,
  style: { fontSize: "12px", color: "#333333", margin: "2px 0 8px 0" },
});
// Uses the named watershedLayer reference (defined in INITIALIZE)
// rather than a fragile layer index to avoid breaking if layer
// order changes as predictions are added
watershedCheck.onChange(function (val) {
  watershedLayer.setShown(val);
});
sidebar.add(watershedCheck);

// Slider to control overall transparency of the probability layer
sidebar.add(bodyLabel("Opacity"));
var opacitySlider = ui.Slider({
  min: 0,
  max: 1,
  value: 0.85,
  step: 0.05,
  style: { stretch: "horizontal", margin: "0 0 4px 0" },
});
sidebar.add(opacitySlider);

// Slider to mask out pixels below a minimum probability value.
// Useful for focusing on high-confidence restoration candidates.
sidebar.add(bodyLabel("Probability Threshold — hide pixels below:"));
var thresholdSlider = ui.Slider({
  min: 0,
  max: 0.95,
  value: 0,
  step: 0.05,
  style: { stretch: "horizontal", margin: "0 0 2px 0" },
});
sidebar.add(thresholdSlider);

// Live readout of the current threshold value
var thresholdReadout = ui.Label("Threshold: 0.00", {
  fontSize: "11px",
  color: "#2171b5",
  margin: "0 0 4px 0",
});
sidebar.add(thresholdReadout);

sidebar.add(divider());

// ============================================================
// COLOR SCHEME SELECTOR
// Swaps the active palette and re-renders both the layer and
// the legend gradient bar to stay in sync.
// ============================================================

sidebar.add(sectionLabel("Color Scheme"));

var paletteSelect = ui.Select({
  items: Object.keys(PALETTES),
  value: "Blue",
  style: { stretch: "horizontal", margin: "0 0 4px 0" },
});
paletteSelect.onChange(function (val) {
  currentPalette = PALETTES[val];
  updateLegend(); // Redraw legend gradient to match new palette
  updateLayer(); // Re-render probability raster with new palette
});
sidebar.add(paletteSelect);

sidebar.add(divider());

// ============================================================
// BASEMAP SELECTOR
// Passes the selected string directly to map.setOptions().
// ============================================================

sidebar.add(sectionLabel("Basemap"));
var basemapSelect = ui.Select({
  items: ["HYBRID", "SATELLITE", "TERRAIN", "ROADMAP"],
  value: "HYBRID",
  style: { stretch: "horizontal", margin: "0 0 4px 0" },
});
basemapSelect.onChange(function (val) {
  map.setOptions(val);
});
sidebar.add(basemapSelect);

sidebar.add(divider());

// ============================================================
// LEGEND
// Renders a gradient thumbnail image spanning the full palette
// from 0 (low) to 1 (high) probability. Rebuilt whenever the
// active palette changes via updateLegend().
// ============================================================

sidebar.add(sectionLabel("Legend"));

var legendPanel = ui.Panel({ style: { margin: "0 0 6px 0" } });
sidebar.add(legendPanel);

function updateLegend() {
  legendPanel.clear();

  // Generate gradient bar by coloring a longitude ramp image
  // with the current palette — a standard GEE legend technique
  var gradientBar = ui.Thumbnail({
    image: ee.Image.pixelLonLat()
      .select("longitude")
      .unitScale(-180, 180)
      .visualize({ min: 0, max: 1, palette: currentPalette }),
    params: { bbox: "-180,-10,180,10", dimensions: "255x16", format: "png" },
    style: { stretch: "horizontal", margin: "0", height: "16px" },
  });
  legendPanel.add(gradientBar);

  // Low / mid / high labels below the gradient bar
  legendPanel.add(
    ui.Panel(
      [
        ui.Label("0 — Low", {
          fontSize: "10px",
          color: "#555",
          margin: "2px 0",
        }),
        ui.Label("0.5", {
          fontSize: "10px",
          color: "#555",
          margin: "2px 0",
          textAlign: "center",
        }),
        ui.Label("1 — High", {
          fontSize: "10px",
          color: "#555",
          margin: "2px 0",
          textAlign: "right",
        }),
      ],
      ui.Panel.Layout.flow("horizontal"),
      { stretch: "horizontal" },
    ),
  );
}

updateLegend();

sidebar.add(divider());

// ============================================================
// PIXEL INSPECTOR
// Samples the probability raster at the clicked location and
// displays the value in the sidebar. Includes spatial and
// raster coverage validation with user-friendly error messages.
// ============================================================

sidebar.add(sectionLabel("Pixel Inspector"));
sidebar.add(
  bodyLabel(
    "Click anywhere on the map to inspect the probability value at that location.",
  ),
);

// Output label — updated dynamically on each map click
var clickOutput = ui.Label("Click the map to inspect…", {
  fontSize: "12px",
  color: "#2c3e50",
  margin: "2px 0 10px 0",
});
sidebar.add(clickOutput);

map.onClick(function (coords) {
  clickOutput.setValue("Sampling…");
  var point = ee.Geometry.Point([coords.lon, coords.lat]);

  // Step 1: Check whether the click falls inside any watershed.
  // This catches clicks on ocean, outside the study area, etc.
  var inWatershed = watershedFC.filterBounds(point);

  inWatershed.size().evaluate(function (count) {
    if (count === 0) {
      // Click was outside all watershed boundaries
      clickOutput.setValue(
        "Outside study area.\n" + "Click inside a watershed boundary.",
      );
      return;
    }

    // Step 2: Click is inside a watershed — attempt raster sample.
    // Not all watersheds have predictions yet, so we handle both
    // the null (no data at pixel) and error (asset not covering
    // this area) cases separately.
    prob
      .sample({ region: point, scale: 30, numPixels: 1 })
      .first()
      .get(BAND_NAME)
      .evaluate(function (val, error) {
        inWatershed
          .first()
          .get("name")
          .evaluate(function (watershedName) {
            if (error) {
              clickOutput.setValue(
                watershedName +
                  "\n\n" +
                  "No prediction data available\n" +
                  "for this watershed yet.",
              );
              return;
            }
            if (val === null) {
              clickOutput.setValue(
                watershedName +
                  "\n\n" +
                  "No raster data at this pixel.\n" +
                  "Predictions may not fully cover\n" +
                  "this watershed.",
              );
            } else {
              clickOutput.setValue(
                watershedName +
                  "\n\n" +
                  "Meadow Probability: " +
                  val.toFixed(4) +
                  "\n" +
                  "Lon: " +
                  coords.lon.toFixed(5) +
                  "\n" +
                  "Lat: " +
                  coords.lat.toFixed(5),
              );
            }
          });
      });
  });
});

sidebar.add(divider());

// ============================================================
// MAIN LAYER RENDER FUNCTION
// Rebuilds and replaces the probability layer whenever opacity,
// threshold, visibility, or palette settings change.
// Called on init and by all relevant control onChange handlers.
// ============================================================

var currentLayer = null; // Holds reference to the active probability layer

function updateLayer() {
  var threshold = thresholdSlider.getValue();
  var opacity = opacitySlider.getValue();
  var visible = toggleCheck.getValue();

  // Keep the threshold readout label in sync with the slider
  thresholdReadout.setValue("Threshold: " + threshold.toFixed(2));

  // Apply threshold mask — pixels below the threshold are hidden
  var display = prob.updateMask(prob.gte(threshold));

  // Remove the old layer before adding the updated one to avoid stacking
  if (currentLayer) map.remove(currentLayer);
  currentLayer = ui.Map.Layer(
    display,
    { min: 0, max: 1, palette: currentPalette },
    "Meadow Probability",
    visible,
    opacity,
  );
  map.add(currentLayer);
}

// Wire all controls that affect the probability layer to updateLayer
opacitySlider.onChange(updateLayer);
thresholdSlider.onChange(updateLayer);
toggleCheck.onChange(updateLayer);

// ============================================================
// INITIALIZE
// Run once on app load — sets initial map view, renders the
// probability layer, and adds the watershed boundary overlay.
// ============================================================

// Holds reference to the active watershed highlight layer.
// Initialized as null; set/replaced by the watershed navigator.
var highlightLayer = null;

// Center the map on the probability raster extent at zoom 10
map.centerObject(prob, 10);

// Render the initial probability layer with default settings
updateLayer();

// Paint watershed borders as a raster image to ensure no fill
// is rendered. FeatureCollection fillColor is unreliable in GEE
// UI apps, so this approach is used instead.
var watershedOutline = ee.Image().byte().paint({
  featureCollection: watershedFC,
  color: 1,
  width: 2,
});

// Add watershed boundary layer — rendered on top of probability
// layer. Referenced by name so the visibility checkbox can
// toggle it without relying on fragile layer index lookups.
var watershedLayer = ui.Map.Layer(
  watershedOutline,
  { palette: ["00FFFF"] }, // Cyan outlines for watershed boundaries
  "Watershed Boundary",
  true,
  0.8,
);
map.add(watershedLayer);
