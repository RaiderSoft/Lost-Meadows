// ============================================================
// Meadow Probability Viewer — Google Earth Engine App
// ============================================================
// Description:
//   Interactive web application for visualizing XGBoost-generated
//   meadow restoration probability predictions across HUC10 watersheds
//   in Southern Oregon and Northern California.
//
// Data Inputs:
//   - Meadow probability rasters: All IMAGE assets in FOLDER_ID
//     (loaded dynamically — add new rasters to the folder and
//     they appear automatically on the next app load)
//   - Watershed boundaries: HUC10 FeatureCollection (GEE Asset)
//
// Features:
//   - Dynamic asset discovery from MeadowPredictions folder
//   - Watershed navigator with zoom + highlight
//   - Probability threshold masking
//   - Opacity control
//   - Multiple color palettes
//   - Basemap switcher
//   - Pixel inspector with error handling
//   - Gradient legend
//
// Project: Lost Meadows Conservation Science
//
// NOTE: We grab a reference to GEE's default map widget BEFORE
// calling ui.root.clear(), then reuse it in the SplitPanel.
// This preserves the logo that GEE attaches to the map widget.
// ============================================================

// ------------------------------------------------------------
// ASSET CONFIGURATION
// FOLDER_ID: path to the GEE asset folder containing all
//   prediction rasters. Any IMAGE asset added to this folder
//   will be automatically included in the mosaic on next load.
// BAND_NAME: the band in each raster holding probability values.
// VALUE_SCALE: divisor to normalize raw values if needed
//   (e.g. 100 if stored as integers 0–100; leave at 1 for floats).
// WATERSHEDS: path to the HUC10 watershed FeatureCollection.
// ------------------------------------------------------------
var FOLDER_ID = "projects/lost-meadows/assets/MeadowPredictions";
var BAND_NAME = "b1";
var VALUE_SCALE = 1;
var WATERSHEDS = "projects/lost-meadows/assets/study_watersheds_HUC10";

// ------------------------------------------------------------
// EXCLUDED WATERSHEDS
// Add watershed names here to hide them from the map and the
// dropdown navigator. No other code changes needed.
// ------------------------------------------------------------
var EXCLUDED_WATERSHEDS = [
  "171003060500-Pacific Ocean",
  "Mack Arch Cove-Pacific Ocean",
  "North Cove-Pacific Ocean",
];

// ------------------------------------------------------------
// DYNAMIC ASSET DISCOVERY
// Lists all assets in FOLDER_ID at runtime, filters to IMAGE
// type only (skipping the watershed FeatureCollection and any
// other non-raster assets), then builds an ImageCollection
// from all discovered rasters.
//
// To add a new watershed prediction to the app:
//   1. Export your prediction raster to FOLDER_ID
//   2. Reload the app — no code changes needed.
// ------------------------------------------------------------
var assetList = ee.data.listAssets(FOLDER_ID);

var imageIds = assetList.assets
  .filter(function (a) {
    return a.type === "IMAGE";
  })
  .map(function (a) {
    return a.name;
  });

// Load each discovered raster, select the probability band,
// and combine into a single ImageCollection
var collection = ee.ImageCollection(
  imageIds.map(function (id) {
    return ee.Image(id).select(BAND_NAME);
  }),
);

// Mosaic all rasters into one image. Where watersheds overlap,
// later assets in the collection take precedence (paint on top).
var prob = collection.mosaic().divide(VALUE_SCALE);

// ------------------------------------------------------------
// LOAD WATERSHED FEATURE COLLECTION
// Excludes any watersheds in EXCLUDED_WATERSHEDS so they are
// hidden from the map boundary layer, navigator dropdown, and
// pixel inspector spatial check.
// ------------------------------------------------------------
var watershedFC = ee
  .FeatureCollection(WATERSHEDS)
  .filter(ee.Filter.inList("name", EXCLUDED_WATERSHEDS).not());

// ------------------------------------------------------------
// WATERSHED NAMES LIST
// Hard-coded from the HUC10 'name' property for use in the
// dropdown navigator. Sorted alphabetically in the UI.
// Remove a name here if you also add it to EXCLUDED_WATERSHEDS.
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
  "Elk Creek (Umpqua)",
  "Jackson Creek",
  "Elk Creek (Rogue)", //Added new names for Elk Creek Watersheds, made the name in change when pulling the data
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
// COLOR PALETTES
// Each palette maps low (0) → high (1) probability values.
// Add additional palettes here as key-value pairs to expose
// them in the Color Scheme dropdown without other code changes.
// ============================================================
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

// Only god knows why the logo won't appear at this point
// I'm like 95% sure this is a GEE bug when they made a change on MArch 30th
// Thank you google for taking a day of my life from me

// Grab a reference to GEE's default map widget BEFORE clearing
// root. The logo configured in App settings is attached to this
// widget — reusing it in the SplitPanel preserves the logo.
var map = ui.root.widgets().get(0);
map.setOptions("HYBRID");

// Sidebar panel — fixed width left panel for all controls
var sidebar = ui.Panel({
  style: { width: "300px", padding: "10px", backgroundColor: "#f5f5f5" },
});

ui.root.clear();
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

sidebar.add(divider());

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

// Toggle visibility of the red watershed boundary outlines.
// Uses a named layer reference rather than a fragile index.
var watershedCheck = ui.Checkbox({
  label: "Show Watershed Boundary",
  value: true,
  style: { fontSize: "12px", color: "#333333", margin: "2px 0 8px 0" },
});
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
// Swaps the active palette and re-renders the layer and legend.
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
// Renders a gradient thumbnail spanning the full palette from
// 0 (low) to 1 (high) probability. Rebuilt on palette change.
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
// Samples the mosaicked probability raster at the clicked
// location. Validates the click is inside a watershed first,
// then reports the probability value or a clear message if
// no prediction data exists for that location yet.
// ============================================================

sidebar.add(sectionLabel("Pixel Inspector"));
sidebar.add(
  bodyLabel(
    "Click anywhere on the map to inspect the probability value at that location.",
  ),
);

var clickOutput = ui.Label("Click the map to inspect…", {
  fontSize: "12px",
  color: "#2c3e50",
  margin: "2px 0 10px 0",
});
sidebar.add(clickOutput);

map.onClick(function (coords) {
  clickOutput.setValue("Sampling…");
  var point = ee.Geometry.Point([coords.lon, coords.lat]);
  var inWatershed = watershedFC.filterBounds(point);

  // First check whether the click falls inside any watershed
  inWatershed.size().evaluate(function (count) {
    if (count === 0) {
      clickOutput.setValue(
        "Outside study area.\nClick inside a watershed boundary.",
      );
      return;
    }

    // Get the watershed name, then sample the mosaicked raster.
    // Since prob is the full mosaic of all folder assets, one
    // sample call covers whichever watershed has data here.
    inWatershed
      .first()
      .get("name")
      .evaluate(function (watershedName) {
        prob
          .sample({ region: point, scale: 30, numPixels: 1 })
          .first()
          .get(BAND_NAME)
          .evaluate(function (val, error) {
            if (error || val === null) {
              // No raster coverage here — prediction not yet exported
              // for this watershed
              clickOutput.setValue(
                watershedName +
                  "\n\n" +
                  "No prediction data available\nfor this location yet.",
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
//
// Because prob is a mosaic of all assets in the folder, a
// single updateLayer() covers all watersheds automatically.
// ============================================================

var currentLayer = null; // Reference to the active probability layer

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
opacitySlider.onChange(function () {
  updateLayer();
});
thresholdSlider.onChange(function () {
  updateLayer();
});
toggleCheck.onChange(function () {
  updateLayer();
});

// ============================================================
// INITIALIZE
// Run once on app load — centers the map on the full study
// area, renders the probability layer, and adds the watershed
// boundary overlay.
// ============================================================

// Holds reference to the active watershed highlight layer.
// Initialized as null; set/replaced by the watershed navigator.
var highlightLayer = null;

// Center the map on the full watershed study area at load
watershedFC
  .geometry()
  .bounds()
  .evaluate(function (bounds) {
    map.centerObject(ee.Geometry(bounds), 8);
  });

// Render the initial probability layer with default settings
updateLayer();

// Paint watershed borders as a raster image to ensure no fill
// is rendered. FeatureCollection fillColor is unreliable in GEE
// UI apps, so this raster-paint approach is used instead.
var watershedOutline = ee.Image().byte().paint({
  featureCollection: watershedFC,
  color: 1,
  width: 2,
});

// Add watershed boundary layer — referenced by name so the
// visibility checkbox can toggle it without relying on fragile
// layer index lookups.
var watershedLayer = ui.Map.Layer(
  watershedOutline,
  { palette: ["FF0000"] }, // Red outlines for watershed boundaries
  "Watershed Boundary",
  true,
  0.8,
);
map.add(watershedLayer);
