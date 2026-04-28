// ============================================================
// Lost Meadows Climate Adaptation Tool
// Google Earth Engine Application
//
// Displays machine-learning meadow probability predictions
// across the Cascade-Siskiyou Bioregion. Users can explore
// watershed boundaries, climate overlays (snowpack, drought,
// land cover), and inspect pixel-level probability values.
//
// Adapts methodology from Cummings et al. (2023).
// ============================================================

// ============================================================
// SECTION 1 — CONFIGURATION CONSTANTS
// Central place for all asset paths, band names, and palette
// definitions. Update here when assets change.
// ============================================================

var FOLDER_ID = "projects/lost-meadows/assets/MeadowPredictions";
var BAND_NAME = "b1"; // Band exported by the ML prediction pipeline
var WATERSHEDS = "projects/lost-meadows/assets/study_watersheds_HUC10";

// Coastal/ocean polygons in the HUC10 dataset that are not study watersheds
var EXCLUDED_WATERSHEDS = [
  "171003060500-Pacific Ocean",
  "Mack Arch Cove-Pacific Ocean",
  "North Cove-Pacific Ocean",
];

var WETLANDS = "projects/lost-meadows/assets/NWI_Wetlands";

// Color palettes for the meadow probability layer (low → high)
var PALETTES = {
  Blue: ["#f7fbff", "#c6dbef", "#6baed6", "#2171b5", "#084594"],
  Red: ["#fff5f0", "#fcbba1", "#fb6a4a", "#cb181d", "#67000d"],
  "Teal-Yellow": ["#ffffcc", "#a1dab4", "#41b6c4", "#2c7fb8", "#253494"],
};

var currentPalette = PALETTES["Blue"];

// Visualization params for climate/land-cover overlays
// SNODAS SWE in mm; Cascade April 1 range ≈ 0–2000 mm
var SNOW_VIS = {
  min: 0,
  max: 2000,
  palette: ["#f7fbff", "#c6dbef", "#6baed6", "#2171b5", "#08306b"],
};

// PDSI: negative = drought, positive = wet
var DROUGHT_VIS = {
  min: -4,
  max: 4,
  palette: ["#d73027", "#f46d43", "#fee08b", "#d9ef8b", "#1a9850"],
};

// Standard NLCD palette mapped to class values 11–95
var NLCD_VIS = {
  min: 11,
  max: 95,
  palette: [
    "476ba1",
    "d1ddf9",
    "dec57a",
    "d2cca1",
    "b3ac9f",
    "68ab63",
    "1c6330",
    "b5ca8e",
    "a68c30",
    "ccba7c",
    "e2e2c1",
    "c9c977",
    "99c147",
    "77ad93",
    "dbd83d",
    "aa7028",
    "bad9eb",
    "70a3ba",
  ],
};

// NLCD class definitions used to build legend swatches
// Defined here (not near the legend function) so both the sidebar
// legend and the inspector panel legend can share this list.
var NLCD_CLASSES = [
  { value: 11, color: "476ba1", label: "Open Water" },
  { value: 21, color: "d1ddf9", label: "Developed, Open Space" },
  { value: 22, color: "dec57a", label: "Developed, Low Intensity" },
  { value: 23, color: "d2cca1", label: "Developed, Medium Intensity" },
  { value: 31, color: "b3ac9f", label: "Barren Land" },
  { value: 41, color: "68ab63", label: "Deciduous Forest" },
  { value: 42, color: "1c6330", label: "Evergreen Forest" },
  { value: 43, color: "b5ca8e", label: "Mixed Forest" },
  { value: 52, color: "ccba7c", label: "Shrub/Scrub" },
  { value: 71, color: "e2e2c1", label: "Grassland/Herbaceous" },
  { value: 81, color: "dbd83d", label: "Pasture/Hay" },
  { value: 82, color: "aa7028", label: "Cultivated Crops" },
  { value: 90, color: "bad9eb", label: "Woody Wetlands" },
  { value: 95, color: "70a3ba", label: "Emergent Herbaceous Wetlands" },
];

// ============================================================
// SECTION 2 — DATA LOADING
// All server-side EE objects are built here before the UI is
// constructed. Client-side callbacks reference these objects.
// ============================================================

// --- Meadow Probability Composite ---
// List all IMAGE assets in the predictions folder, load each,
// and mosaic into a single probability surface (0–1).
var assetList = ee.data.listAssets(FOLDER_ID);

var imageIds = assetList.assets
  .filter(function (a) {
    return a.type === "IMAGE";
  })
  .map(function (a) {
    return a.name;
  });

var prob = ee
  .ImageCollection(
    imageIds.map(function (id) {
      return ee.Image(id).select(BAND_NAME);
    }),
  )
  .mosaic();
// Note: no scaling needed — predictions are already 0–1 from the pipeline.

// --- Watershed Boundaries ---
// Load HUC10 boundaries and drop non-study coastal polygons.
var watershedFC = ee
  .FeatureCollection(WATERSHEDS)
  .filter(ee.Filter.inList("name", EXCLUDED_WATERSHEDS).not());

// Client-side sorted list used by the search box and dropdown.
// Must stay in sync with the features in watershedFC.
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
  "Elk Creek (Rogue)",
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

var sortedNames = watershedNames.slice().sort();

// --- Climate & Land Cover Sources ---
// These are loaded once and clipped on demand by the refresh functions.

// SNODAS via GEE Community Catalog. April 1 SWE is the standard
// late-season snowpack benchmark for water resource planning.
var snowSource = ee
  .ImageCollection(
    "projects/earthengine-legacy/assets/projects/climate-engine/snodas/daily",
  )
  .filter(ee.Filter.calendarRange(4, 4, "month"))
  .filter(ee.Filter.calendarRange(1, 1, "day_of_month"))
  .sort("system:time_start", false)
  .first()
  .select("SWE");

// GRIDMET PDSI — 6-month rolling mean as a drought indicator.
// Note: EDDI is the preferred index (PRD §4.4); swap the collection
// path here once EDDI is imported to the shared GEE asset folder.
// ee.Date(Date.now()) wraps the JS timestamp in a server-side ee.Date.
// GEE does not have an ee.Date.now() method.
var droughtSource = ee
  .ImageCollection("GRIDMET/DROUGHT")
  .filterDate(ee.Date(Date.now()).advance(-6, "month"), ee.Date(Date.now()))
  .select("pdsi")
  .mean()
  .resample("bicubic");

// NLCD: most recent collection year
var nlcdSource = ee
  .ImageCollection("USGS/NLCD_RELEASES/2021_REL/NLCD")
  .sort("system:time_start", false)
  .first()
  .select("landcover");

// NWI wetlands (OR + CA), filtered to PEM/PSS meadow types
var wetlandsPEM = ee
  .FeatureCollection(WETLANDS)
  .filter(ee.Filter.stringStartsWith("ATTRIBUTE", "PEM"));
var wetlandsPSS = ee
  .FeatureCollection(WETLANDS)
  .filter(ee.Filter.stringStartsWith("ATTRIBUTE", "PSS"));

// ============================================================
// SECTION 3 — UI LAYOUT
// Three-panel layout: sidebar | map | inspector.
// The map widget is pulled from ui.root, cleared, then
// reinserted inside a SplitPanel arrangement.
// ============================================================

var map = ui.root.widgets().get(0);
map.setOptions("HYBRID");

var sidebar = ui.Panel({
  style: { width: "300px", padding: "10px", backgroundColor: "#f5f5f5" },
});

var inspectorPanel = ui.Panel({
  style: { width: "260px", padding: "10px", backgroundColor: "#f5f5f5" },
});

// mapWrapper holds both the map and the inspector so they share
// horizontal space in the outer SplitPanel.
var mapWrapper = ui.Panel({ style: { stretch: "both" } });

ui.root.clear();
ui.root.add(
  ui.SplitPanel({
    firstPanel: sidebar,
    secondPanel: mapWrapper,
    orientation: "horizontal",
    wipe: false,
  }),
);
mapWrapper.add(
  ui.SplitPanel({
    firstPanel: map,
    secondPanel: inspectorPanel,
    orientation: "horizontal",
    wipe: false,
  }),
);

// ============================================================
// SECTION 4 — UI HELPER FUNCTIONS
// Thin wrappers that keep widget styling consistent across
// the app. Call these instead of ui.Label/ui.Panel directly
// when building section headers or dividers.
// ============================================================

/** Bold section header for use inside panels. */
function sectionLabel(text) {
  return ui.Label(text, {
    fontWeight: "bold",
    fontSize: "14px",
    color: "#333333",
    margin: "12px 0 4px 0",
  });
}

/** Smaller descriptive text below a section header. */
function bodyLabel(text) {
  return ui.Label(text, {
    fontSize: "11px",
    color: "#666666",
    margin: "0 0 6px 0",
  });
}

/** Thin horizontal rule to visually separate sidebar sections. */
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

/**
 * Builds a gradient legend bar for a continuous layer.
 * @param {string} title    - Label above the bar.
 * @param {Array}  palette  - Array of hex color strings (low → high).
 * @param {string} minLabel - Text below the left end of the bar.
 * @param {string} maxLabel - Text below the right end of the bar.
 * @returns {ui.Panel} Ready-to-add legend panel.
 */
function buildGradientLegend(title, palette, minLabel, maxLabel) {
  var panel = ui.Panel({ style: { margin: "0 0 4px 0" } });
  panel.add(
    ui.Label(title, {
      fontWeight: "bold",
      fontSize: "11px",
      color: "#333",
      margin: "4px 0 2px 0",
    }),
  );
  panel.add(
    ui.Thumbnail({
      image: ee.Image.pixelLonLat()
        .select("longitude")
        .unitScale(-180, 180)
        .visualize({ min: 0, max: 1, palette: palette }),
      params: { bbox: "-180,-10,180,10", dimensions: "255x12", format: "png" },
      style: { stretch: "horizontal", margin: "0", height: "12px" },
    }),
  );
  panel.add(
    ui.Panel(
      [
        ui.Label(minLabel, { fontSize: "10px", color: "#555" }),
        ui.Label(maxLabel, {
          fontSize: "10px",
          color: "#555",
          textAlign: "right",
        }),
      ],
      ui.Panel.Layout.flow("horizontal"),
      { stretch: "horizontal" },
    ),
  );
  return panel;
}

// ============================================================
// SECTION 5 — WATERSHED HIGHLIGHT HELPERS
// Manages a single "selected watershed" highlight layer on the
// map. Only one watershed is highlighted at a time.
// ============================================================

var highlightLayer = null;

/**
 * Paints a yellow outline around the named watershed and adds
 * it as a map layer, replacing any previous highlight.
 * @param {string} name - The watershed's 'name' property value.
 */
function applyHighlight(name) {
  var selected = watershedFC.filter(ee.Filter.eq("name", name));
  var outline = ee.Image().byte().paint({
    featureCollection: selected,
    color: 1,
    width: 3,
  });
  if (highlightLayer) map.remove(highlightLayer);
  highlightLayer = ui.Map.Layer(
    outline,
    { palette: ["FFFF00"] },
    "Selected Watershed",
    true,
    1,
  );
  map.add(highlightLayer);
}

/** Removes the yellow watershed highlight from the map. */
function clearHighlight() {
  if (highlightLayer) map.remove(highlightLayer);
  highlightLayer = null;
}

// ============================================================
// SECTION 6 — OVERLAY REFRESH FUNCTIONS
// Each refresh function clips its source to the currently
// selected watershed and swaps only its own layer, then calls
// restackTopLayers() to keep probability/boundary/highlight on top.
//
// Draw order is always:
//   overlays → probability → watershed outline → highlight
//
// getClipTarget() returns null when no watershed is selected.
// All refresh functions and refreshActiveOverlays() bail early
// on a null clip target, making them safe to call at any time.
//
// Overlay checkboxes toggled on before a watershed is selected
// are treated as "pending" — their state is preserved but no
// layer is added. refreshActiveOverlays() picks them up as soon
// as a watershed is selected via click, search, or dropdown.
//
// clearOverlayLayers() removes active overlay layers from the
// map without touching checkbox state, so pending overlays
// reactivate automatically on the next watershed selection.
// ============================================================

/**
 * Shifts a vis-params min/max by a fractional offset. Used by
 * the scenario sliders to simulate wetter/drier/snowier conditions
 * WITHOUT re-running ML predictions — only the palette range moves.
 * @param {Object} base   - Original vis params {min, max, palette}.
 * @param {number} offset - Value from -1 to 1 (slider position).
 * @returns {Object} New vis params with shifted min/max.
 */
function shiftVis(base, offset) {
  var shift = offset * (base.max - base.min) * 0.5;
  return {
    min: base.min + shift,
    max: base.max + shift,
    palette: base.palette,
  };
}

/**
 * Returns the geometry of the currently selected watershed, or null
 * if no watershed is selected. All callers check for null and bail
 * early, so no downstream function ever receives a null geometry.
 * @returns {ee.Geometry|null}
 */
function getClipTarget() {
  var selected = watershedSelect.getValue();
  if (!selected) return null;
  return watershedFC.filter(ee.Filter.eq("name", selected)).geometry();
}

// Overlay layer handles — null means the layer is not currently on the map.
var snowLayer = null;
var droughtLayer = null;
var nlcdLayer = null;
var wetlandsLayer = null;
var wetlandsPSSLayer = null;

/**
 * Lifts the probability layer, watershed outline, and highlight back
 * to the top of the map's draw stack after an overlay is added or
 * removed. Only removes and re-adds these three layers — overlay
 * layers are left untouched, so no extra tile requests are triggered.
 */
function restackTopLayers() {
  if (currentLayer) map.remove(currentLayer);
  if (watershedLayer) map.remove(watershedLayer);
  if (highlightLayer) map.remove(highlightLayer);

  if (currentLayer) map.add(currentLayer);
  if (watershedLayer) {
    watershedLayer.setShown(watershedCheck.getValue());
    map.add(watershedLayer);
  }
  if (highlightLayer) map.add(highlightLayer);
}

/**
 * Removes all active overlay layers from the map and nulls their
 * handles, without touching checkbox state. Called when the watershed
 * selection is cleared so overlays disappear but their checkboxes
 * remain checked, ready to reload on the next watershed selection.
 */
function clearOverlayLayers() {
  if (snowLayer) {
    map.remove(snowLayer);
    snowLayer = null;
  }
  if (droughtLayer) {
    map.remove(droughtLayer);
    droughtLayer = null;
  }
  if (nlcdLayer) {
    map.remove(nlcdLayer);
    nlcdLayer = null;
  }
  if (wetlandsLayer) {
    map.remove(wetlandsLayer);
    wetlandsLayer = null;
  }
  if (wetlandsPSSLayer) {
    map.remove(wetlandsPSSLayer);
    wetlandsPSSLayer = null;
  }
}

/**
 * Clips SNODAS snowpack to the selected watershed and restacks.
 * Bails early if no watershed is selected.
 */
function refreshSnow() {
  var clip = getClipTarget();
  if (!clip) return;
  var vis = shiftVis(SNOW_VIS, snowSlider.getValue());
  if (snowLayer) map.remove(snowLayer);
  snowLayer = ui.Map.Layer(
    snowSource.clip(clip),
    vis,
    "Snowpack (April 1 SWE)",
    true,
    0.75,
  );
  map.add(snowLayer);
  restackTopLayers();
}

/**
 * Clips GRIDMET drought to the selected watershed and restacks.
 * Bails early if no watershed is selected.
 */
function refreshDrought() {
  var clip = getClipTarget();
  if (!clip) return;
  var vis = shiftVis(DROUGHT_VIS, droughtSlider.getValue());
  if (droughtLayer) map.remove(droughtLayer);
  droughtLayer = ui.Map.Layer(
    droughtSource.clip(clip),
    vis,
    "Drought Index (PDSI)",
    true,
    0.75,
  );
  map.add(droughtLayer);
  restackTopLayers();
}

/**
 * Clips NLCD land cover to the selected watershed and restacks.
 * Bails early if no watershed is selected.
 */
function refreshNlcd() {
  var clip = getClipTarget();
  if (!clip) return;
  if (nlcdLayer) map.remove(nlcdLayer);
  nlcdLayer = ui.Map.Layer(
    nlcdSource.clip(clip),
    NLCD_VIS,
    "Land Cover (NLCD)",
    true,
    0.8,
  );
  map.add(nlcdLayer);
  restackTopLayers();
}

/**
 * Filters NWI wetlands to the selected watershed and restacks.
 * Bails early if no watershed is selected.
 */
function refreshWetlands() {
  var clip = getClipTarget();
  if (!clip) return;
  if (wetlandsLayer) map.remove(wetlandsLayer);
  if (wetlandsPSSLayer) map.remove(wetlandsPSSLayer);
  wetlandsLayer = ui.Map.Layer(
    wetlandsPEM.filterBounds(clip),
    { color: "1a9641" },
    "NWI Wetlands — PEM",
    true,
    0.8,
  );
  wetlandsPSSLayer = ui.Map.Layer(
    wetlandsPSS.filterBounds(clip),
    { color: "a8d5b5" },
    "NWI Wetlands — PSS",
    true,
    0.8,
  );
  map.add(wetlandsLayer);
  map.add(wetlandsPSSLayer);
  restackTopLayers();
}

/**
 * Re-clips all checked overlays to the current watershed selection.
 * Bails early if no watershed is selected, making it safe to call
 * from selectWatershed() even during edge-case null name evaluations.
 * Rebuilds each active overlay layer object and adds it to the map,
 * then calls restackTopLayers() once at the end. Picks up any
 * checkboxes toggled on before a watershed was selected.
 */
function refreshActiveOverlays() {
  var clip = getClipTarget();
  if (!clip) return;

  if (snowCheck.getValue()) {
    var snowVis = shiftVis(SNOW_VIS, snowSlider.getValue());
    if (snowLayer) map.remove(snowLayer);
    snowLayer = ui.Map.Layer(
      snowSource.clip(clip),
      snowVis,
      "Snowpack (April 1 SWE)",
      true,
      0.75,
    );
    map.add(snowLayer);
  }

  if (droughtCheck.getValue()) {
    var droughtVis = shiftVis(DROUGHT_VIS, droughtSlider.getValue());
    if (droughtLayer) map.remove(droughtLayer);
    droughtLayer = ui.Map.Layer(
      droughtSource.clip(clip),
      droughtVis,
      "Drought Index (PDSI)",
      true,
      0.75,
    );
    map.add(droughtLayer);
  }

  if (nlcdCheck.getValue()) {
    if (nlcdLayer) map.remove(nlcdLayer);
    nlcdLayer = ui.Map.Layer(
      nlcdSource.clip(clip),
      NLCD_VIS,
      "Land Cover (NLCD)",
      true,
      0.8,
    );
    map.add(nlcdLayer);
  }

  if (wetlandsCheck.getValue()) {
    if (wetlandsLayer) map.remove(wetlandsLayer);
    if (wetlandsPSSLayer) map.remove(wetlandsPSSLayer);
    wetlandsLayer = ui.Map.Layer(
      wetlandsPEM.filterBounds(clip),
      { color: "1a9641" },
      "NWI Wetlands — PEM",
      true,
      0.8,
    );
    wetlandsPSSLayer = ui.Map.Layer(
      wetlandsPSS.filterBounds(clip),
      { color: "a8d5b5" },
      "NWI Wetlands — PSS",
      true,
      0.8,
    );
    map.add(wetlandsLayer);
    map.add(wetlandsPSSLayer);
  }

  // Single restack after all overlay objects are rebuilt
  restackTopLayers();
}

// ============================================================
// SECTION 7 — LEGEND UPDATE FUNCTIONS
// Two separate legend areas: the sidebar (climate overlays) and
// the inspector panel (NLCD class swatches). Both are rebuilt
// from scratch whenever their respective checkboxes change.
// ============================================================

// Container panels — populated by the update functions below.
// They live in the inspector panel (right side), not the sidebar.
var climateInspectorLegendPanel = ui.Panel({
  style: { shown: false, margin: "0 0 6px 0" },
});
var nlcdInspectorLegendPanel = ui.Panel({
  style: { shown: false, margin: "0 0 6px 0" },
});
var wetlandsInspectorLegendPanel = ui.Panel({
  style: { shown: false, margin: "0 0 6px 0" },
});

// Inspector panel headers for climate, NLCD, Wetlands legends
var climateInspectorDivider = divider();
var climateInspectorHeader = ui.Label("Climate Overlays", {
  fontWeight: "bold",
  fontSize: "13px",
  color: "#2c3e50",
  margin: "0 0 4px 0",
});
var nlcdInspectorDivider = divider();
var nlcdInspectorHeader = ui.Label("Land Cover (NLCD)", {
  fontWeight: "bold",
  fontSize: "13px",
  color: "#2c3e50",
  margin: "0 0 4px 0",
});
var wetlandsInspectorDivider = divider();
var wetlandsInspectorHeader = ui.Label("NWI Wetlands", {
  fontWeight: "bold",
  fontSize: "13px",
  color: "#2c3e50",
  margin: "0 0 4px 0",
});

// Hide inspector legend headers until their overlays are toggled on
climateInspectorDivider.style().set("shown", false);
climateInspectorHeader.style().set("shown", false);
nlcdInspectorDivider.style().set("shown", false);
nlcdInspectorHeader.style().set("shown", false);
wetlandsInspectorDivider.style().set("shown", false);
wetlandsInspectorHeader.style().set("shown", false);

/**
 * Rebuilds the climate legend in the inspector panel. Shows gradient
 * bars for whichever of snow/drought are currently active.
 */
function updateClimateLegend() {
  climateInspectorLegendPanel.clear();
  var showSnow = snowCheck.getValue();
  var showDrought = droughtCheck.getValue();
  var showClimate = showSnow || showDrought;

  climateInspectorDivider.style().set("shown", showClimate);
  climateInspectorHeader.style().set("shown", showClimate);
  climateInspectorLegendPanel.style().set("shown", showClimate);

  if (showSnow) {
    climateInspectorLegendPanel.add(
      buildGradientLegend(
        "Snowpack (SWE mm)",
        SNOW_VIS.palette,
        "0 mm",
        "2000 mm",
      ),
    );
  }
  if (showDrought) {
    climateInspectorLegendPanel.add(
      buildGradientLegend(
        "Drought Index (PDSI)",
        DROUGHT_VIS.palette,
        "Drought",
        "Wet",
      ),
    );
  }
}

/**
 * Shows or hides the NLCD class swatch legend in the inspector panel.
 * @param {boolean} visible - True to build and show; false to clear and hide.
 */
function updateNlcdInspectorLegend(visible) {
  nlcdInspectorDivider.style().set("shown", visible);
  nlcdInspectorHeader.style().set("shown", visible);
  nlcdInspectorLegendPanel.style().set("shown", visible);
  nlcdInspectorLegendPanel.clear();

  if (!visible) return;

  NLCD_CLASSES.forEach(function (c) {
    nlcdInspectorLegendPanel.add(
      ui.Panel(
        [
          ui.Label("", {
            backgroundColor: "#" + c.color,
            padding: "6px",
            margin: "2px 6px 2px 0",
          }),
          ui.Label(c.label, {
            fontSize: "10px",
            color: "#333",
            margin: "2px 0",
          }),
        ],
        ui.Panel.Layout.flow("horizontal"),
      ),
    );
  });
}

/**
 * Shows or hides the NWI wetlands swatch legend in the inspector panel.
 * @param {boolean} visible - True to build and show; false to clear and hide.
 */
function updateWetlandsInspectorLegend(visible) {
  wetlandsInspectorDivider.style().set("shown", visible);
  wetlandsInspectorHeader.style().set("shown", visible);
  wetlandsInspectorLegendPanel.style().set("shown", visible);
  wetlandsInspectorLegendPanel.clear();
  if (!visible) return;

  [
    { color: "1a9641", label: "PEM — Active wet meadow" },
    { color: "a8d5b5", label: "PSS — Shrub-encroached meadow" },
  ].forEach(function (c) {
    wetlandsInspectorLegendPanel.add(
      ui.Panel(
        [
          ui.Label("", {
            backgroundColor: "#" + c.color,
            padding: "6px",
            margin: "2px 6px 2px 0",
          }),
          ui.Label(c.label, {
            fontSize: "10px",
            color: "#333",
            margin: "2px 0",
          }),
        ],
        ui.Panel.Layout.flow("horizontal"),
      ),
    );
  });

  wetlandsInspectorLegendPanel.add(
    ui.Label("Source: National Wetlands Inventory (OR/CA)", {
      fontSize: "9px",
      color: "#999",
      margin: "4px 0 0 0",
    }),
  );
}

// ============================================================
// SECTION 8 — SIDEBAR UI
// Widgets are declared, added to the sidebar, then wired with
// onChange handlers in that order for readability.
// ============================================================

// ── Title ────────────────────────────────────────────────────
sidebar.add(
  ui.Label("Meadow Probability", {
    fontWeight: "bold",
    fontSize: "20px",
    color: "#2c3e50",
    margin: "0 0 2px 0",
  }),
);
sidebar.add(divider());

// ── Watershed Navigator ──────────────────────────────────────
sidebar.add(sectionLabel("Watershed Navigator"));
sidebar.add(
  bodyLabel(
    "Type to search, use the dropdown, or click a watershed on the map.",
  ),
);

var searchBox = ui.Textbox({
  placeholder: "Search watersheds…",
  style: { stretch: "horizontal", margin: "0 0 2px 0" },
});
sidebar.add(searchBox);

var searchClearBtn = ui.Button({
  label: "Clear search",
  style: { stretch: "horizontal", margin: "0 0 2px 0" },
});
sidebar.add(searchClearBtn);

// Shows "N of M watersheds" or "No matches found" during search
var matchCountLabel = ui.Label("", {
  fontSize: "10px",
  color: "#888888",
  margin: "0 0 2px 0",
});
sidebar.add(matchCountLabel);

// Autocomplete suggestion buttons (hidden until search produces results)
var suggestionPanel = ui.Panel({
  style: {
    shown: false,
    stretch: "horizontal",
    backgroundColor: "#ffffff",
    border: "1px solid #cccccc",
    margin: "0 0 4px 0",
    padding: "2px 0",
  },
});
sidebar.add(suggestionPanel);

var watershedSelect = ui.Select({
  items: sortedNames,
  placeholder: "Or select a watershed…",
  style: { stretch: "horizontal", margin: "0 0 4px 0" },
});
sidebar.add(watershedSelect);

var clearButton = ui.Button({
  label: "Clear Selection",
  style: { stretch: "horizontal", margin: "4px 0 0 0" },
});
sidebar.add(clearButton);

sidebar.add(divider());

// ── Layer Controls ───────────────────────────────────────────
sidebar.add(sectionLabel("Layer Controls"));

var toggleCheck = ui.Checkbox({
  label: "Show Meadow Probability Layer",
  value: true,
  style: { fontSize: "12px", color: "#333333", margin: "2px 0 8px 0" },
});
sidebar.add(toggleCheck);

var watershedCheck = ui.Checkbox({
  label: "Show Watershed Boundary",
  value: true,
  style: { fontSize: "12px", color: "#333333", margin: "2px 0 8px 0" },
});
sidebar.add(watershedCheck);

sidebar.add(bodyLabel("Opacity"));
var opacitySlider = ui.Slider({
  min: 0,
  max: 1,
  value: 0.5,
  step: 0.05,
  style: { stretch: "horizontal", margin: "0 0 4px 0" },
});
sidebar.add(opacitySlider);

sidebar.add(bodyLabel("Probability Threshold — hide pixels below:"));
var thresholdSlider = ui.Slider({
  min: 0,
  max: 0.95,
  value: 0,
  step: 0.05,
  style: { stretch: "horizontal", margin: "0 0 2px 0" },
});
sidebar.add(thresholdSlider);

var thresholdReadout = ui.Label("Threshold: 0.00", {
  fontSize: "11px",
  color: "#2171b5",
  margin: "0 0 4px 0",
});
sidebar.add(thresholdReadout);

sidebar.add(divider());

// ── Color Scheme ─────────────────────────────────────────────
sidebar.add(sectionLabel("Color Scheme"));
var paletteSelect = ui.Select({
  items: Object.keys(PALETTES),
  value: "Blue",
  style: { stretch: "horizontal", margin: "0 0 4px 0" },
});
sidebar.add(paletteSelect);

sidebar.add(divider());

// ── Basemap ──────────────────────────────────────────────────
sidebar.add(sectionLabel("Basemap"));
var basemapSelect = ui.Select({
  items: ["HYBRID", "SATELLITE", "TERRAIN", "ROADMAP"],
  value: "HYBRID",
  style: { stretch: "horizontal", margin: "0 0 4px 0" },
});
sidebar.add(basemapSelect);

sidebar.add(divider());

// ── Meadow Probability Legend ─────────────────────────────────
sidebar.add(sectionLabel("Legend"));
var legendPanel = ui.Panel({ style: { margin: "0 0 6px 0" } });
sidebar.add(legendPanel);

sidebar.add(divider());

// ── Climate & Land Cover ─────────────────────────────────────
sidebar.add(sectionLabel("Climate & Land Cover"));
sidebar.add(
  bodyLabel(
    "Select a watershed first, then toggle overlays to clip data to it.",
  ),
);

var snowCheck = ui.Checkbox({
  label: "Snowpack (April 1 SWE)",
  value: false,
  style: { fontSize: "12px", color: "#333333", margin: "2px 0 4px 0" },
});
sidebar.add(snowCheck);

var droughtCheck = ui.Checkbox({
  label: "Drought Index (PDSI/EDDI)",
  value: false,
  style: { fontSize: "12px", color: "#333333", margin: "2px 0 4px 0" },
});
sidebar.add(droughtCheck);

var nlcdCheck = ui.Checkbox({
  label: "Land Cover (NLCD)",
  value: false,
  style: { fontSize: "12px", color: "#333333", margin: "2px 0 8px 0" },
});
sidebar.add(nlcdCheck);

var wetlandsCheck = ui.Checkbox({
  label: "NWI Wetlands (PEM/PSS)",
  value: false,
  style: { fontSize: "12px", color: "#333333", margin: "2px 0 8px 0" },
});
sidebar.add(wetlandsCheck);

sidebar.add(
  bodyLabel("Explore scenarios — palette shift only, predictions unchanged:"),
);

sidebar.add(
  ui.Label("Snowpack offset:", {
    fontSize: "11px",
    color: "#555555",
    margin: "4px 0 0 0",
  }),
);
var snowSlider = ui.Slider({
  min: -1,
  max: 1,
  value: 0,
  step: 0.1,
  style: { stretch: "horizontal", margin: "0 0 2px 0" },
});
sidebar.add(snowSlider);
var snowOffsetLabel = ui.Label("Baseline", {
  fontSize: "11px",
  color: "#2171b5",
  margin: "0 0 2px 8px",
});
sidebar.add(snowOffsetLabel);

sidebar.add(
  ui.Label("Drought severity offset:", {
    fontSize: "11px",
    color: "#555555",
    margin: "6px 0 0 0",
  }),
);
var droughtSlider = ui.Slider({
  min: -1,
  max: 1,
  value: 0,
  step: 0.1,
  style: { stretch: "horizontal", margin: "0 0 2px 0" },
});
sidebar.add(droughtSlider);
var droughtOffsetLabel = ui.Label("Baseline", {
  fontSize: "11px",
  color: "#2171b5",
  margin: "0 0 2px 8px",
});
sidebar.add(droughtOffsetLabel);

var resetBaselineBtn = ui.Button({
  label: "Reset to Baseline",
  style: { stretch: "horizontal", margin: "8px 0 0 0", fontSize: "11px" },
});
sidebar.add(resetBaselineBtn);

sidebar.add(divider());

// ============================================================
// SECTION 9 — INSPECTOR PANEL UI
// Right-hand panel that shows watershed name, coordinates, and
// probability value for whatever pixel the user clicks.
// Legend sections for climate/NLCD overlays also live here.
// ============================================================

inspectorPanel.add(
  ui.Label("Pixel Summary", {
    fontWeight: "bold",
    fontSize: "20px",
    color: "#2c3e50",
    margin: "0 0 2px 0",
  }),
);
inspectorPanel.add(divider());
inspectorPanel.add(
  bodyLabel(
    "Click anywhere on the map to inspect the probability value at that location.",
  ),
);

inspectorPanel.add(sectionLabel("Watershed"));
var watershedOutput = ui.Label("—", {
  fontSize: "13px",
  color: "#2c3e50",
  margin: "2px 0 10px 0",
});
inspectorPanel.add(watershedOutput);

inspectorPanel.add(divider());

inspectorPanel.add(sectionLabel("Coordinates"));
var lonOutput = ui.Label("Lon: —", {
  fontSize: "13px",
  color: "#2c3e50",
  margin: "2px 0 2px 0",
});
var latOutput = ui.Label("Lat: —", {
  fontSize: "13px",
  color: "#2c3e50",
  margin: "2px 0 10px 0",
});
inspectorPanel.add(lonOutput);
inspectorPanel.add(latOutput);

inspectorPanel.add(divider());

inspectorPanel.add(sectionLabel("Meadow Probability"));
var probOutput = ui.Label("—", {
  fontSize: "13px",
  color: "#2171b5",
  fontWeight: "bold",
  margin: "2px 0 10px 0",
});
inspectorPanel.add(probOutput);

// Status line: shows sampling errors or "outside study area" messages
var statusOutput = ui.Label("", {
  fontSize: "11px",
  color: "#999999",
  margin: "4px 0 0 0",
});
inspectorPanel.add(statusOutput);

// Climate overlay legend (snow + drought) — shown/hidden by updateClimateLegend()
inspectorPanel.add(climateInspectorDivider);
inspectorPanel.add(climateInspectorHeader);
inspectorPanel.add(climateInspectorLegendPanel);

// NLCD class swatch legend — shown/hidden by updateNlcdInspectorLegend()
inspectorPanel.add(nlcdInspectorDivider);
inspectorPanel.add(nlcdInspectorHeader);
inspectorPanel.add(nlcdInspectorLegendPanel);

// NWI Wetlands swatch legend — shown/hidden by updateWetlandsInspectorLegend()
inspectorPanel.add(wetlandsInspectorDivider);
inspectorPanel.add(wetlandsInspectorHeader);
inspectorPanel.add(wetlandsInspectorLegendPanel);

// ============================================================
// SECTION 10 — EVENT HANDLERS
// All onChange / onClick wiring. Grouped here so the full
// interactive logic is in one place rather than scattered
// through the widget declarations above.
// ============================================================

// ── Watershed Selection ──────────────────────────────────────

/**
 * Core watershed selection handler. Bails immediately if name is
 * null or empty — this prevents edge cases where the map click
 * handler's async evaluate callback fires with a null result.
 * Syncs the search box and dropdown, applies the highlight, and
 * fires refreshActiveOverlays() which picks up any checkboxes
 * that were toggled on while no watershed was selected.
 *
 * @param {string}  name - Watershed name to select.
 * @param {boolean} zoom - If true, pan/zoom the map to the watershed bounds.
 */
function selectWatershed(name, zoom) {
  if (!name) return; // guard against null from async evaluate callbacks

  searchBox.setValue(name, false);
  matchCountLabel.setValue("");
  suggestionPanel.clear();
  suggestionPanel.style().set("shown", false);
  watershedSelect.items().reset(sortedNames);
  watershedSelect.setValue(name, false);

  if (zoom) {
    watershedFC
      .filter(ee.Filter.eq("name", name))
      .first()
      .geometry()
      .bounds()
      .evaluate(function (bounds) {
        map.centerObject(ee.Geometry(bounds), 11);
      });
  }

  applyHighlight(name);
  refreshActiveOverlays();
}

// Search box: filter and show autocomplete suggestions as the user types
searchBox.onChange(function (text) {
  var trimmed = text.trim();
  suggestionPanel.clear();

  if (trimmed === "") {
    suggestionPanel.style().set("shown", false);
    matchCountLabel.setValue("");
    watershedSelect.items().reset(sortedNames);
    watershedSelect.setValue(null, false);
    clearHighlight();
    return;
  }

  var lower = trimmed.toLowerCase();
  var filtered = sortedNames.filter(function (name) {
    return name.toLowerCase().indexOf(lower) !== -1;
  });

  if (filtered.length === 0) {
    matchCountLabel.setValue("No matches found");
    suggestionPanel.style().set("shown", false);
    return;
  }

  matchCountLabel.setValue(
    filtered.length + " of " + sortedNames.length + " watersheds",
  );

  if (filtered.length === 1) {
    selectWatershed(filtered[0], true);
    return;
  }

  var shown = filtered.slice(0, 6);
  shown.forEach(function (name) {
    suggestionPanel.add(
      ui.Button({
        label: name,
        style: {
          stretch: "horizontal",
          textAlign: "left",
          backgroundColor: "#ffffff",
          color: "#2c3e50",
          fontSize: "11px",
          margin: "0",
          padding: "4px 8px",
          border: "none",
        },
        onClick: function () {
          selectWatershed(name, true);
        },
      }),
    );
  });
  if (filtered.length > 6) {
    suggestionPanel.add(
      ui.Label("+ " + (filtered.length - 6) + " more — keep typing to narrow", {
        fontSize: "10px",
        color: "#aaaaaa",
        margin: "2px 8px 2px 8px",
      }),
    );
  }
  suggestionPanel.style().set("shown", true);
});

// Clear search button: resets search state and removes overlay layers
searchClearBtn.onClick(function () {
  searchBox.setValue("", false);
  suggestionPanel.clear();
  suggestionPanel.style().set("shown", false);
  matchCountLabel.setValue("");
  watershedSelect.items().reset(sortedNames);
  watershedSelect.setValue(null, false);
  clearHighlight();
  clearOverlayLayers();
});

// Dropdown: selecting a watershed zooms and highlights
watershedSelect.onChange(function (name) {
  if (!name) return;
  selectWatershed(name, true);
});

// Clear Selection button: resets all state and removes overlay layers.
// Checkbox state is preserved so overlays reload on next watershed selection.
clearButton.onClick(function () {
  clearHighlight();
  clearOverlayLayers();
  watershedSelect.items().reset(sortedNames);
  watershedSelect.setValue(null, false);
  searchBox.setValue("", false);
  matchCountLabel.setValue("");
  suggestionPanel.clear();
  suggestionPanel.style().set("shown", false);
});

// ── Map Click — Pixel Inspector ──────────────────────────────

map.onClick(function (coords) {
  watershedOutput.setValue("Sampling…");
  lonOutput.setValue("Lon: —");
  latOutput.setValue("Lat: —");
  probOutput.setValue("—");
  statusOutput.setValue("");

  var point = ee.Geometry.Point([coords.lon, coords.lat]);
  var inWatershed = watershedFC.filterBounds(point);

  inWatershed.size().evaluate(function (count) {
    if (count === 0) {
      watershedOutput.setValue("—");
      statusOutput.setValue(
        "Outside study area. Click inside a watershed boundary.",
      );
      clearHighlight();
      return;
    }

    lonOutput.setValue("Lon: " + coords.lon.toFixed(5));
    latOutput.setValue("Lat: " + coords.lat.toFixed(5));

    // selectWatershed guards against null internally, so a null name
    // returned from evaluate will silently no-op rather than crash.
    inWatershed
      .first()
      .get("name")
      .evaluate(function (watershedName) {
        watershedOutput.setValue(watershedName || "—");
        selectWatershed(watershedName, false);

        prob
          .sample({ region: point, scale: 30, numPixels: 1 })
          .first()
          .get(BAND_NAME)
          .evaluate(function (val, error) {
            if (error || val === null) {
              probOutput.setValue("No data");
              statusOutput.setValue(
                "No prediction data available for this location yet.",
              );
            } else {
              probOutput.setValue((val * 100).toFixed(1) + "%");
            }
          });
      });
  });
});

// ── Layer Controls ───────────────────────────────────────────

var currentLayer = null;
var watershedLayer = null; // declared here; initialized after map centers

/**
 * Re-renders the meadow probability layer using current slider
 * and checkbox values. Removes the old layer before adding the
 * new one, then re-stacks the watershed outline and highlight
 * on top so draw order stays consistent.
 */
function updateProbLayer() {
  var threshold = thresholdSlider.getValue();
  var opacity = opacitySlider.getValue();
  var visible = toggleCheck.getValue();

  thresholdReadout.setValue("Threshold: " + threshold.toFixed(2));

  var display = prob.updateMask(prob.gte(threshold));

  if (currentLayer) map.remove(currentLayer);
  currentLayer = ui.Map.Layer(
    display,
    { min: 0, max: 1, palette: currentPalette },
    "Meadow Probability",
    visible,
    opacity,
  );
  map.add(currentLayer);

  if (watershedLayer) {
    map.remove(watershedLayer);
    watershedLayer.setShown(watershedCheck.getValue());
    map.add(watershedLayer);
  }
  if (highlightLayer) {
    map.remove(highlightLayer);
    map.add(highlightLayer);
  }
}

opacitySlider.onChange(function () {
  updateProbLayer();
});
thresholdSlider.onChange(function () {
  updateProbLayer();
});
toggleCheck.onChange(function () {
  updateProbLayer();
});
watershedCheck.onChange(function (val) {
  if (watershedLayer) watershedLayer.setShown(val);
});

paletteSelect.onChange(function (val) {
  currentPalette = PALETTES[val];
  updateMeadowLegend();
  updateProbLayer();
});

basemapSelect.onChange(function (val) {
  map.setOptions(val);
});

// ── Climate Overlay Toggles ──────────────────────────────────
// If a watershed is selected, toggling ON fires the refresh immediately.
// If no watershed is selected, checkbox state is saved but no layer is
// added — refreshActiveOverlays() picks it up on the next selection.
// Toggling OFF always removes the layer regardless of watershed state.

snowCheck.onChange(function (val) {
  if (val) {
    if (watershedSelect.getValue()) refreshSnow();
  } else {
    if (snowLayer) {
      map.remove(snowLayer);
      snowLayer = null;
    }
    restackTopLayers();
  }
  updateClimateLegend();
});

droughtCheck.onChange(function (val) {
  if (val) {
    if (watershedSelect.getValue()) refreshDrought();
  } else {
    if (droughtLayer) {
      map.remove(droughtLayer);
      droughtLayer = null;
    }
    restackTopLayers();
  }
  updateClimateLegend();
});

nlcdCheck.onChange(function (val) {
  if (val) {
    if (watershedSelect.getValue()) refreshNlcd();
  } else {
    if (nlcdLayer) {
      map.remove(nlcdLayer);
      nlcdLayer = null;
    }
    restackTopLayers();
  }
  updateNlcdInspectorLegend(val);
});

wetlandsCheck.onChange(function (val) {
  if (val) {
    if (watershedSelect.getValue()) refreshWetlands();
  } else {
    if (wetlandsLayer) {
      map.remove(wetlandsLayer);
      wetlandsLayer = null;
    }
    if (wetlandsPSSLayer) {
      map.remove(wetlandsPSSLayer);
      wetlandsPSSLayer = null;
    }
    restackTopLayers();
  }
  updateWetlandsInspectorLegend(val);
});

// ── Scenario Sliders ─────────────────────────────────────────

snowSlider.onChange(function (val) {
  var pct = Math.round(val * 100);
  snowOffsetLabel.setValue(
    pct === 0
      ? "Baseline"
      : pct > 0
        ? "+" + pct + "% (above avg)"
        : pct + "% (below avg)",
  );
  if (snowCheck.getValue() && watershedSelect.getValue()) refreshSnow();
});

droughtSlider.onChange(function (val) {
  var pct = Math.round(val * 100);
  droughtOffsetLabel.setValue(
    pct === 0
      ? "Baseline"
      : pct > 0
        ? "+" + pct + "% (drier)"
        : Math.abs(pct) + "% (wetter)",
  );
  if (droughtCheck.getValue() && watershedSelect.getValue()) refreshDrought();
});

// Reset button: returns both sliders and labels to baseline state
resetBaselineBtn.onClick(function () {
  snowSlider.setValue(0, false);
  droughtSlider.setValue(0, false);
  snowOffsetLabel.setValue("Baseline");
  droughtOffsetLabel.setValue("Baseline");
  if (snowCheck.getValue() && watershedSelect.getValue()) refreshSnow();
  if (droughtCheck.getValue() && watershedSelect.getValue()) refreshDrought();
});

// ============================================================
// SECTION 11 — MEADOW PROBABILITY LEGEND
// Gradient bar below the layer controls. Rebuilt whenever the
// color scheme changes.
// ============================================================

/** Rebuilds the gradient color bar for the meadow probability layer. */
function updateMeadowLegend() {
  legendPanel.clear();
  legendPanel.add(
    buildGradientLegend(
      "Meadow Probability",
      currentPalette,
      "0 — Low",
      "1 — High",
    ),
  );
}

updateMeadowLegend(); // draw initial legend

// ============================================================
// SECTION 12 — INITIALIZATION
// Add base layers and center the map. Called last so all
// handler functions and layer variables are already defined.
// ============================================================

// Center on the full study area extent on load
watershedFC
  .geometry()
  .bounds()
  .evaluate(function (bounds) {
    map.centerObject(ee.Geometry(bounds), 8);
  });

// Red outline showing all HUC10 watershed boundaries
var watershedOutline = ee.Image().byte().paint({
  featureCollection: watershedFC,
  color: 1,
  width: 2,
});
watershedLayer = ui.Map.Layer(
  watershedOutline,
  { palette: ["FF0000"] },
  "Watershed Boundary",
  true,
  0.8,
);
map.add(watershedLayer);

// Draw the initial probability layer
updateProbLayer();
