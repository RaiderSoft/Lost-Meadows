// ============================================================
// Lost Meadows Climate Adaptation Tool
// Google Earth Engine Application
//
// Displays machine-learning meadow probability predictions
// across the Cascade-Siskiyou Bioregion. Users can explore
// watershed boundaries, climate overlays (snowpack, drought,
// land cover), and inspect pixel-level probability values.
//
// Two prediction layers are available:
//   - Watershed Model: predictions trained on watershed-scale data
//   - Global Model:    predictions from a global-scale model
// Both share the same opacity and threshold controls, but each has its
// own independent color scheme so they can be visually distinguished.
//
// Adapts methodology from Cummings et al. (2023).
// ============================================================

// ============================================================
// SECTION 1 — CONFIGURATION CONSTANTS
// Central place for all asset paths, band names, and palette
// definitions. Update here when assets change.
// ============================================================

// GEE asset folder path for the watershed-scale ML predictions
var FOLDER_ID = "projects/lost-meadows/assets/Predictions";

// GEE asset folder path for the global-scale ML predictions.
// This folder is mosaicked into a single image the same way
// the watershed predictions are, and shares all visual controls.
var FOLDER_ID_GLOBAL = "projects/lost-meadows/assets/GlobalPredictions";

// Band name exported by both ML prediction pipelines (0–1 probability)
var BAND_NAME = "b1";

// HUC10 watershed boundaries for the study area
var WATERSHEDS = "projects/lost-meadows/assets/study_watersheds_HUC10";

// Coastal/ocean polygons in the HUC10 dataset that are not study watersheds.
// These are excluded from the watershed navigator and boundary overlay.
var EXCLUDED_WATERSHEDS = [
  "171003060500-Pacific Ocean",
  "Mack Arch Cove-Pacific Ocean",
  "North Cove-Pacific Ocean"
];

// NWI wetlands asset (Oregon + California), filtered to meadow types below
var WETLANDS = "projects/lost-meadows/assets/NWI_Wetlands";

// Color palettes shared by both the watershed and global probability layers.
// Each layer has its own independent palette selector so they can be
// visually distinguished when displayed at the same time.
var PALETTES = {
  Blue: ["#f7fbff", "#c6dbef", "#6baed6", "#2171b5", "#084594"],
  Red: ["#fff5f0", "#fcbba1", "#fb6a4a", "#cb181d", "#67000d"],
  "Teal-Yellow": ["#ffffcc", "#a1dab4", "#41b6c4", "#2c7fb8", "#253494"]
};

// Tracks the active palette for the watershed model layer.
// Default is Blue; updated whenever the watershed palette selector changes.
var currentPalette = PALETTES["Blue"];

// Tracks the active palette for the global model layer.
// Default is Red so it is immediately distinguishable from the watershed layer.
// Updated whenever the global palette selector changes.
var currentGlobalPalette = PALETTES["Red"];

// Visualization parameters for the snowpack overlay.
// SNODAS SWE is in millimeters; the Cascade April 1 range is roughly 0–2000 mm.
var SNOW_VIS = {
  min: 0,
  max: 2000,
  palette: ["#f7fbff", "#c6dbef", "#6baed6", "#2171b5", "#08306b"]
};

// Visualization parameters for the drought overlay.
// PDSI is centered at 0: negative values indicate drought, positive indicate wet conditions.
var DROUGHT_VIS = {
  min: -4,
  max: 4,
  palette: ["#d73027", "#f46d43", "#fee08b", "#d9ef8b", "#1a9850"]
};

// Visualization parameters for the NLCD land cover overlay.
// Class values span 11–95 with the standard NLCD color scheme.
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
    "70a3ba"
  ]
};

// NLCD class definitions — shared by the sidebar legend and the inspector panel.
// Keeping this list here (rather than near one legend function) avoids duplication.
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
  { value: 95, color: "70a3ba", label: "Emergent Herbaceous Wetlands" }
];

// ============================================================
// SECTION 2 — DATA LOADING
// All server-side EE objects are built here before the UI is
// constructed. Client-side callbacks reference these objects.
// ============================================================

// --- Watershed-Scale Meadow Probability Composite ---
// Lists all IMAGE assets in the watershed predictions folder, loads each one,
// and mosaics them into a single probability surface covering the study area.
// Predictions are already scaled 0–1 by the ML pipeline, so no scaling is needed.
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
    })
  )
  .mosaic();

// --- Global-Scale Meadow Probability Composite ---
// Follows the exact same pattern as the watershed predictions above.
// Lists all IMAGE assets in the GlobalPredictions folder, loads each one,
// and mosaics them into a single global probability surface.
// Like the watershed model, values are already 0–1 from the pipeline.
var globalAssetList = ee.data.listAssets(FOLDER_ID_GLOBAL);

var globalImageIds = globalAssetList.assets
  .filter(function (a) {
    return a.type === "IMAGE";
  })
  .map(function (a) {
    return a.name;
  });

var probGlobal = ee
  .ImageCollection(
    globalImageIds.map(function (id) {
      return ee.Image(id).select(BAND_NAME);
    })
  )
  .mosaic();

// --- Watershed Boundaries ---
// Loads the HUC10 feature collection and drops the three coastal/ocean polygons
// that are included in the dataset but are not part of the study area.
var watershedFC = ee
  .FeatureCollection(WATERSHEDS)
  .filter(ee.Filter.inList("name", EXCLUDED_WATERSHEDS).not());

// Client-side sorted list of watershed names used by the search box and dropdown.
// Must remain in sync with the features in watershedFC.
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
  "Iron Gate Reservoir-Klamath River"
];

// Alphabetically sorted copy used to populate the dropdown and suggestion panel
var sortedNames = watershedNames.slice().sort();

// --- Climate & Land Cover Sources ---
// Loaded once at startup and clipped on demand inside the refresh functions.

// SNODAS via GEE Community Catalog. Filters to April 1 (late-season snowpack
// benchmark used for water resource planning) and takes the most recent year.
var snowSource = ee
  .ImageCollection(
    "projects/earthengine-legacy/assets/projects/climate-engine/snodas/daily"
  )
  .filter(ee.Filter.calendarRange(4, 4, "month"))
  .filter(ee.Filter.calendarRange(1, 1, "day_of_month"))
  .sort("system:time_start", false)
  .first()
  .select("SWE");

// GRIDMET PDSI — 6-month rolling mean used as a drought indicator.
// Note: EDDI is the preferred index (PRD §4.4); swap the collection path
// here once EDDI is imported to the shared GEE asset folder.
// ee.Date(Date.now()) wraps the JS timestamp in a server-side ee.Date
// because GEE does not expose an ee.Date.now() method.
var droughtSource = ee
  .ImageCollection("GRIDMET/DROUGHT")
  .filterDate(ee.Date(Date.now()).advance(-6, "month"), ee.Date(Date.now()))
  .select("pdsi")
  .mean()
  .resample("bicubic");

// NLCD: loads the most recent available collection year
var nlcdSource = ee
  .ImageCollection("USGS/NLCD_RELEASES/2021_REL/NLCD")
  .sort("system:time_start", false)
  .first()
  .select("landcover");

// NWI wetlands (OR + CA), pre-filtered to three meadow-relevant types:
//   PEM — Palustrine Emergent (active wet meadow)
//   PSS — Palustrine Scrub-Shrub (shrub-encroached meadow)
//   PFO — Palustrine Forested (conifer-encroached meadow)
var wetlandsPEM = ee
  .FeatureCollection(WETLANDS)
  .filter(ee.Filter.stringStartsWith("ATTRIBUTE", "PEM"));
var wetlandsPSS = ee
  .FeatureCollection(WETLANDS)
  .filter(ee.Filter.stringStartsWith("ATTRIBUTE", "PSS"));
var wetlandsPFO = ee
  .FeatureCollection(WETLANDS)
  .filter(ee.Filter.stringStartsWith("ATTRIBUTE", "PFO"));

// ============================================================
// SECTION 3 — UI LAYOUT
// Three-panel layout: sidebar | map | inspector.
// The default map widget is pulled from ui.root, the root is
// cleared, then everything is reinserted inside nested
// SplitPanel widgets to create the three-column arrangement.
// ============================================================

// Pull the default GEE map widget and switch to hybrid basemap
var map = ui.root.widgets().get(0);
map.setOptions("HYBRID");

// Left sidebar: watershed navigator, layer controls, climate overlays
var sidebar = ui.Panel({
  style: { width: "300px", padding: "10px", backgroundColor: "#f5f5f5" }
});

// Right inspector panel: pixel values, coordinates, and overlay legends
var inspectorPanel = ui.Panel({
  style: { width: "260px", padding: "10px", backgroundColor: "#f5f5f5" }
});

// mapWrapper holds both the map and the inspector so they share
// horizontal space inside the outer SplitPanel
var mapWrapper = ui.Panel({ style: { stretch: "both" } });

// Rebuild the root with a sidebar | (map + inspector) layout
ui.root.clear();
ui.root.add(
  ui.SplitPanel({
    firstPanel: sidebar,
    secondPanel: mapWrapper,
    orientation: "horizontal",
    wipe: false
  })
);
mapWrapper.add(
  ui.SplitPanel({
    firstPanel: map,
    secondPanel: inspectorPanel,
    orientation: "horizontal",
    wipe: false
  })
);

// ============================================================
// SECTION 4 — UI HELPER FUNCTIONS
// Thin wrappers that keep widget styling consistent across
// the app. Call these instead of ui.Label/ui.Panel directly
// when building section headers or dividers.
// ============================================================

/**
 * Returns a bold section header label for use inside panels.
 * @param {string} text - Header text to display.
 * @returns {ui.Label}
 */
function sectionLabel(text) {
  return ui.Label(text, {
    fontWeight: "bold",
    fontSize: "14px",
    color: "#333333",
    margin: "12px 0 4px 0"
  });
}

/**
 * Returns a smaller descriptive label, typically placed below a section header.
 * @param {string} text - Body text to display.
 * @returns {ui.Label}
 */
function bodyLabel(text) {
  return ui.Label(text, {
    fontSize: "11px",
    color: "#666666",
    margin: "0 0 6px 0"
  });
}

/**
 * Returns a thin horizontal rule panel for visually separating sidebar sections.
 * @returns {ui.Panel}
 */
function divider() {
  return ui.Panel({
    style: {
      height: "1px",
      backgroundColor: "#cccccc",
      margin: "10px 0 10px 0",
      stretch: "horizontal"
    }
  });
}

/**
 * Builds and returns a gradient color bar legend for a continuous layer.
 * @param {string} title    - Label displayed above the gradient bar.
 * @param {Array}  palette  - Array of hex color strings ordered low → high.
 * @param {string} minLabel - Text displayed below the left (low) end of the bar.
 * @param {string} maxLabel - Text displayed below the right (high) end of the bar.
 * @returns {ui.Panel} A ready-to-add legend panel containing the bar and labels.
 */
function buildGradientLegend(title, palette, minLabel, maxLabel) {
  var panel = ui.Panel({ style: { margin: "0 0 4px 0" } });
  panel.add(
    ui.Label(title, {
      fontWeight: "bold",
      fontSize: "11px",
      color: "#333",
      margin: "4px 0 2px 0"
    })
  );
  // Render the gradient as a stretched thumbnail of a longitude-based gradient image
  panel.add(
    ui.Thumbnail({
      image: ee.Image.pixelLonLat()
        .select("longitude")
        .unitScale(-180, 180)
        .visualize({ min: 0, max: 1, palette: palette }),
      params: { bbox: "-180,-10,180,10", dimensions: "255x12", format: "png" },
      style: { stretch: "horizontal", margin: "0", height: "12px" }
    })
  );
  // Min/max labels sit below the bar in a horizontal flow panel
  panel.add(
    ui.Panel(
      [
        ui.Label(minLabel, { fontSize: "10px", color: "#555" }),
        ui.Label(maxLabel, {
          fontSize: "10px",
          color: "#555",
          textAlign: "right"
        })
      ],
      ui.Panel.Layout.flow("horizontal"),
      { stretch: "horizontal" }
    )
  );
  return panel;
}

// ============================================================
// SECTION 5 — WATERSHED HIGHLIGHT HELPERS
// Manages a single "selected watershed" yellow outline on the
// map. Only one watershed is highlighted at a time.
// ============================================================

// Holds the current highlight layer handle, or null if none is active
var highlightLayer = null;

/**
 * Paints a yellow outline around the named watershed and adds it to the map,
 * replacing any previously active highlight layer.
 * @param {string} name - The watershed's 'name' property value in watershedFC.
 */
function applyHighlight(name) {
  var selected = watershedFC.filter(ee.Filter.eq("name", name));
  var outline = ee.Image().byte().paint({
    featureCollection: selected,
    color: 1,
    width: 3
  });
  if (highlightLayer) map.remove(highlightLayer);
  highlightLayer = ui.Map.Layer(
    outline,
    { palette: ["FFFF00"] },
    "Selected Watershed",
    true,
    1
  );
  map.add(highlightLayer);
}

/**
 * Removes the yellow watershed highlight from the map and clears the handle.
 */
function clearHighlight() {
  if (highlightLayer) map.remove(highlightLayer);
  highlightLayer = null;
}

// ============================================================
// SECTION 6 — OVERLAY REFRESH FUNCTIONS
// Each refresh function clips its source to the currently
// selected watershed and swaps only its own map layer, then
// calls restackTopLayers() to keep the probability layers,
// watershed boundary, and highlight on top.
//
// Draw order is always:
//   overlays → global probability → watershed probability → boundary → highlight
//
// getClipTarget() returns null when no watershed is selected.
// All refresh functions bail early on null, making them safe
// to call at any time regardless of selection state.
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
 * Returns a new vis-params object with min/max shifted by a fractional offset.
 * Used by the scenario sliders to simulate wetter/drier/snowier conditions
 * without re-running ML predictions — only the palette range moves.
 * @param {Object} base   - Original vis params {min, max, palette}.
 * @param {number} offset - Value from -1 to 1 (slider position).
 * @returns {Object} New vis params with shifted min/max and original palette.
 */
function shiftVis(base, offset) {
  var shift = offset * (base.max - base.min) * 0.5;
  return {
    min: base.min + shift,
    max: base.max + shift,
    palette: base.palette
  };
}

/**
 * Returns the geometry of the currently selected watershed, or null if none
 * is selected. All callers check for null and bail early, so no downstream
 * function ever receives a null geometry.
 * @returns {ee.Geometry|null}
 */
function getClipTarget() {
  var selected = watershedSelect.getValue();
  if (!selected) return null;
  return watershedFC.filter(ee.Filter.eq("name", selected)).geometry();
}

// Overlay layer handles — null means the layer is not currently on the map.
// Climate and land cover overlays are clipped to the selected watershed.
var snowLayer = null;
var droughtLayer = null;
var nlcdLayer = null;
var wetlandsLayer = null;
var wetlandsPSSLayer = null;
var wetlandsPFOLayer = null;

/**
 * Lifts the probability layers (global then watershed), watershed boundary,
 * and highlight back to the top of the draw stack after an overlay is added
 * or removed. Only removes and re-adds these layers — overlay layers are
 * left untouched, avoiding unnecessary tile re-requests.
 *
 * Draw order after restack (bottom → top):
 *   overlays → global probability → watershed probability → boundary → highlight
 */
function restackTopLayers() {
  // Remove all top layers before re-adding them in the correct order
  if (currentGlobalLayer) map.remove(currentGlobalLayer);
  if (currentLayer) map.remove(currentLayer);
  if (watershedLayer) map.remove(watershedLayer);
  if (highlightLayer) map.remove(highlightLayer);

  // Re-add in desired draw order (global underneath watershed model)
  if (currentGlobalLayer) map.add(currentGlobalLayer);
  if (currentLayer) map.add(currentLayer);
  if (watershedLayer) {
    watershedLayer.setShown(watershedCheck.getValue());
    map.add(watershedLayer);
  }
  if (highlightLayer) map.add(highlightLayer);
}

/**
 * Removes all active climate and land cover overlay layers from the map and
 * nulls their handles, without touching checkbox state. Called when the
 * watershed selection is cleared so overlays disappear but their checkboxes
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
  if (wetlandsPFOLayer) {
    map.remove(wetlandsPFOLayer);
    wetlandsPFOLayer = null;
  }
}

/**
 * Clips the SNODAS snowpack layer to the selected watershed and adds it to
 * the map, applying any offset from the scenario slider before rendering.
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
    0.75
  );
  map.add(snowLayer);
  restackTopLayers();
}

/**
 * Clips the GRIDMET drought index to the selected watershed and adds it to
 * the map, applying any offset from the scenario slider before rendering.
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
    0.75
  );
  map.add(droughtLayer);
  restackTopLayers();
}

/**
 * Clips the NLCD land cover layer to the selected watershed and adds it to
 * the map. Bails early if no watershed is selected.
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
    0.8
  );
  map.add(nlcdLayer);
  restackTopLayers();
}

/**
 * Filters NWI wetland features to the selected watershed and adds all three
 * wetland type layers (PEM, PSS, PFO) to the map.
 * Bails early if no watershed is selected.
 */
function refreshWetlands() {
  var clip = getClipTarget();
  if (!clip) return;
  if (wetlandsLayer) map.remove(wetlandsLayer);
  if (wetlandsPSSLayer) map.remove(wetlandsPSSLayer);
  if (wetlandsPFOLayer) map.remove(wetlandsPFOLayer);

  wetlandsLayer = ui.Map.Layer(
    wetlandsPEM.filterBounds(clip),
    { color: "4c956c" },
    "NWI Wetlands — PEM",
    true,
    0.8
  );
  wetlandsPSSLayer = ui.Map.Layer(
    wetlandsPSS.filterBounds(clip),
    { color: "e9c46a" },
    "NWI Wetlands — PSS",
    true,
    0.8
  );
  wetlandsPFOLayer = ui.Map.Layer(
    wetlandsPFO.filterBounds(clip),
    { color: "e76f51" },
    "NWI Wetlands — PFO",
    true,
    0.8
  );
  map.add(wetlandsLayer);
  map.add(wetlandsPSSLayer);
  map.add(wetlandsPFOLayer);
  restackTopLayers();
}

/**
 * Re-clips all currently checked overlays to the active watershed selection
 * and adds them to the map. Bails early if no watershed is selected, making
 * it safe to call from selectWatershed() even on edge-case null names.
 * Picks up any checkboxes that were toggled on before a watershed was chosen.
 * Calls restackTopLayers() once at the end rather than once per overlay.
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
      0.75
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
      0.75
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
      0.8
    );
    map.add(nlcdLayer);
  }

  if (wetlandsCheck.getValue()) {
    if (wetlandsLayer) map.remove(wetlandsLayer);
    if (wetlandsPSSLayer) map.remove(wetlandsPSSLayer);
    if (wetlandsPFOLayer) map.remove(wetlandsPFOLayer);
    wetlandsLayer = ui.Map.Layer(
      wetlandsPEM.filterBounds(clip),
      { color: "4c956c" },
      "NWI Wetlands — PEM",
      true,
      0.8
    );
    wetlandsPSSLayer = ui.Map.Layer(
      wetlandsPSS.filterBounds(clip),
      { color: "e9c46a" },
      "NWI Wetlands — PSS",
      true,
      0.8
    );
    wetlandsPFOLayer = ui.Map.Layer(
      wetlandsPFO.filterBounds(clip),
      { color: "e76f51" },
      "NWI Wetlands — PFO",
      true,
      0.8
    );
    map.add(wetlandsLayer);
    map.add(wetlandsPSSLayer);
    map.add(wetlandsPFOLayer);
  }

  // Single restack call after all overlay objects are rebuilt
  restackTopLayers();
}

// ============================================================
// SECTION 7 — LEGEND UPDATE FUNCTIONS
// Two separate legend areas: the sidebar (climate overlays) and
// the inspector panel (NLCD class swatches and wetland swatches).
// Both are rebuilt from scratch whenever their checkboxes change.
// ============================================================

// Container panels for inspector-panel legends; populated by the functions below.
var climateInspectorLegendPanel = ui.Panel({
  style: { shown: false, margin: "0 0 6px 0" }
});
var nlcdInspectorLegendPanel = ui.Panel({
  style: { shown: false, margin: "0 0 6px 0" }
});
var wetlandsInspectorLegendPanel = ui.Panel({
  style: { shown: false, margin: "0 0 6px 0" }
});

// Headers and dividers for each inspector legend section.
// All start hidden and are shown when their overlay is activated.
var climateInspectorDivider = divider();
var climateInspectorHeader = ui.Label("Climate Overlays", {
  fontWeight: "bold",
  fontSize: "13px",
  color: "#2c3e50",
  margin: "0 0 4px 0"
});
var nlcdInspectorDivider = divider();
var nlcdInspectorHeader = ui.Label("Land Cover (NLCD)", {
  fontWeight: "bold",
  fontSize: "13px",
  color: "#2c3e50",
  margin: "0 0 4px 0"
});
var wetlandsInspectorDivider = divider();
var wetlandsInspectorHeader = ui.Label("NWI Wetlands", {
  fontWeight: "bold",
  fontSize: "13px",
  color: "#2c3e50",
  margin: "0 0 4px 0"
});

// Hide all inspector legend headers until their overlays are toggled on
climateInspectorDivider.style().set("shown", false);
climateInspectorHeader.style().set("shown", false);
nlcdInspectorDivider.style().set("shown", false);
nlcdInspectorHeader.style().set("shown", false);
wetlandsInspectorDivider.style().set("shown", false);
wetlandsInspectorHeader.style().set("shown", false);

/**
 * Rebuilds the climate legend in the inspector panel, showing gradient bars
 * for whichever of snow/drought are currently checked. Hides the section
 * entirely when neither is active.
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
        "2000 mm"
      )
    );
  }
  if (showDrought) {
    climateInspectorLegendPanel.add(
      buildGradientLegend(
        "Drought Index (PDSI)",
        DROUGHT_VIS.palette,
        "Drought",
        "Wet"
      )
    );
  }
}

/**
 * Shows or hides the NLCD class swatch legend in the inspector panel.
 * Rebuilds swatches from NLCD_CLASSES whenever shown.
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
            margin: "2px 6px 2px 0"
          }),
          ui.Label(c.label, {
            fontSize: "10px",
            color: "#333",
            margin: "2px 0"
          })
        ],
        ui.Panel.Layout.flow("horizontal")
      )
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
    { color: "4c956c", label: "PEM — Active wet meadow" },
    { color: "e9c46a", label: "PSS — Shrub-encroached meadow" },
    { color: "e76f51", label: "PFO — Conifer-encroached meadow" }
  ].forEach(function (c) {
    wetlandsInspectorLegendPanel.add(
      ui.Panel(
        [
          ui.Label("", {
            backgroundColor: "#" + c.color,
            padding: "6px",
            margin: "2px 6px 2px 0"
          }),
          ui.Label(c.label, {
            fontSize: "10px",
            color: "#333",
            margin: "2px 0"
          })
        ],
        ui.Panel.Layout.flow("horizontal")
      )
    );
  });

  wetlandsInspectorLegendPanel.add(
    ui.Label("Source: National Wetlands Inventory (OR/CA)", {
      fontSize: "9px",
      color: "#999",
      margin: "4px 0 0 0"
    })
  );
}

// ============================================================
// SECTION 8 — SIDEBAR UI
// Widgets are declared, added to the sidebar, then wired with
// onChange handlers in Section 10. Kept in this order so the
// full widget tree is readable top-to-bottom.
// ============================================================

// ── Title ────────────────────────────────────────────────────
sidebar.add(
  ui.Label("Meadow Probability", {
    fontWeight: "bold",
    fontSize: "20px",
    color: "#2c3e50",
    margin: "0 0 2px 0"
  })
);
sidebar.add(divider());

// ── Watershed Navigator ──────────────────────────────────────
sidebar.add(sectionLabel("Watershed Navigator"));
sidebar.add(
  bodyLabel(
    "Type to search, use the dropdown, or click a watershed on the map."
  )
);

// Free-text search box; onChange filters the suggestion panel in real time
var searchBox = ui.Textbox({
  placeholder: "Search watersheds…",
  style: { stretch: "horizontal", margin: "0 0 2px 0" }
});
sidebar.add(searchBox);

// Clears the search box, suggestion panel, and dropdown without zooming
var searchClearBtn = ui.Button({
  label: "Clear search",
  style: { stretch: "horizontal", margin: "0 0 2px 0" }
});
sidebar.add(searchClearBtn);

// Displays "N of M watersheds" or "No matches found" during search
var matchCountLabel = ui.Label("", {
  fontSize: "10px",
  color: "#888888",
  margin: "0 0 2px 0"
});
sidebar.add(matchCountLabel);

// Autocomplete suggestion buttons; hidden until the search returns results
var suggestionPanel = ui.Panel({
  style: {
    shown: false,
    stretch: "horizontal",
    backgroundColor: "#ffffff",
    border: "1px solid #cccccc",
    margin: "0 0 4px 0",
    padding: "2px 0"
  }
});
sidebar.add(suggestionPanel);

// Full watershed dropdown — secondary to the search box
var watershedSelect = ui.Select({
  items: sortedNames,
  placeholder: "Or select a watershed…",
  style: { stretch: "horizontal", margin: "0 0 4px 0" }
});
sidebar.add(watershedSelect);

// Resets all watershed selection state and removes overlay layers from the map
var clearButton = ui.Button({
  label: "Clear Selection",
  style: { stretch: "horizontal", margin: "4px 0 0 0" }
});
sidebar.add(clearButton);

sidebar.add(divider());

// ── Layer Controls ───────────────────────────────────────────
sidebar.add(sectionLabel("Layer Controls"));

// Toggle for the watershed-scale probability layer
var toggleCheck = ui.Checkbox({
  label: "Show Meadow Probability (Watershed Model)",
  value: true,
  style: { fontSize: "12px", color: "#333333", margin: "2px 0 8px 0" }
});
sidebar.add(toggleCheck);

// Toggle for the global-scale probability layer.
// Both probability layers share the opacity, threshold, and color scheme controls.
// The global layer renders beneath the watershed layer in the draw stack,
// so watershed predictions are visible on top when both are active.
var toggleGlobalCheck = ui.Checkbox({
  label: "Show Meadow Probability (Global Model)",
  value: false,
  style: { fontSize: "12px", color: "#333333", margin: "2px 0 8px 0" }
});
sidebar.add(toggleGlobalCheck);

// Toggle for the red HUC10 watershed boundary outline
var watershedCheck = ui.Checkbox({
  label: "Show Watershed Boundary",
  value: true,
  style: { fontSize: "12px", color: "#333333", margin: "2px 0 8px 0" }
});
sidebar.add(watershedCheck);

// Opacity slider — controls both probability layers simultaneously
sidebar.add(bodyLabel("Opacity"));
var opacitySlider = ui.Slider({
  min: 0,
  max: 1,
  value: 0.5,
  step: 0.05,
  style: { stretch: "horizontal", margin: "0 0 4px 0" }
});
sidebar.add(opacitySlider);

// Threshold slider — hides pixels below this probability value in both layers
sidebar.add(bodyLabel("Probability Threshold — hide pixels below:"));
var thresholdSlider = ui.Slider({
  min: 0,
  max: 0.95,
  value: 0,
  step: 0.05,
  style: { stretch: "horizontal", margin: "0 0 2px 0" }
});
sidebar.add(thresholdSlider);

// Readout label showing the current threshold value
var thresholdReadout = ui.Label("Threshold: 0.00", {
  fontSize: "11px",
  color: "#2171b5",
  margin: "0 0 4px 0"
});
sidebar.add(thresholdReadout);

sidebar.add(divider());

// ── Color Scheme ─────────────────────────────────────────────
// Each probability layer has its own palette selector so the two models
// can be displayed in different colors for visual comparison.
// Changing either selector only updates that layer's palette.
sidebar.add(sectionLabel("Color Scheme"));

// Watershed model palette — defaults to Blue
sidebar.add(bodyLabel("Watershed Model:"));
var paletteSelect = ui.Select({
  items: Object.keys(PALETTES),
  value: "Blue",
  style: { stretch: "horizontal", margin: "0 0 6px 0" }
});
sidebar.add(paletteSelect);

// Global model palette — defaults to Red so it contrasts with the watershed layer
sidebar.add(bodyLabel("Global Model:"));
var globalPaletteSelect = ui.Select({
  items: Object.keys(PALETTES),
  value: "Red",
  style: { stretch: "horizontal", margin: "0 0 4px 0" }
});
sidebar.add(globalPaletteSelect);

sidebar.add(divider());

// ── Basemap ──────────────────────────────────────────────────
sidebar.add(sectionLabel("Basemap"));
var basemapSelect = ui.Select({
  items: ["HYBRID", "SATELLITE", "TERRAIN", "ROADMAP"],
  value: "HYBRID",
  style: { stretch: "horizontal", margin: "0 0 4px 0" }
});
sidebar.add(basemapSelect);

sidebar.add(divider());

// ── Meadow Probability Legend ─────────────────────────────────
// Two gradient bars: one for the watershed model, one for the global model.
// Each is rebuilt independently by updateMeadowLegend() when its palette changes.
sidebar.add(sectionLabel("Legend"));
var legendPanel = ui.Panel({ style: { margin: "0 0 6px 0" } });
sidebar.add(legendPanel);

sidebar.add(divider());

// ── Climate & Land Cover ─────────────────────────────────────
sidebar.add(sectionLabel("Climate & Land Cover"));
sidebar.add(
  bodyLabel(
    "Select a watershed first, then toggle overlays to clip data to it."
  )
);

// Snowpack overlay (SNODAS April 1 SWE)
var snowCheck = ui.Checkbox({
  label: "Snowpack (April 1 SWE)",
  value: false,
  style: { fontSize: "12px", color: "#333333", margin: "2px 0 4px 0" }
});
sidebar.add(snowCheck);

// Drought overlay (GRIDMET PDSI 6-month mean)
var droughtCheck = ui.Checkbox({
  label: "Drought Index (PDSI/EDDI)",
  value: false,
  style: { fontSize: "12px", color: "#333333", margin: "2px 0 4px 0" }
});
sidebar.add(droughtCheck);

// NLCD land cover overlay
var nlcdCheck = ui.Checkbox({
  label: "Land Cover (NLCD)",
  value: false,
  style: { fontSize: "12px", color: "#333333", margin: "2px 0 8px 0" }
});
sidebar.add(nlcdCheck);

// NWI wetlands overlay (PEM/PSS/PFO types)
var wetlandsCheck = ui.Checkbox({
  label: "NWI Wetlands (PEM/PSS/PFO)",
  value: false,
  style: { fontSize: "12px", color: "#333333", margin: "2px 0 8px 0" }
});
sidebar.add(wetlandsCheck);

// Scenario sliders shift the vis-params range to simulate climate changes.
// They do NOT re-run ML predictions — only the palette mapping moves.
sidebar.add(
  bodyLabel("Explore scenarios — palette shift only, predictions unchanged:")
);

sidebar.add(
  ui.Label("Snowpack offset:", {
    fontSize: "11px",
    color: "#555555",
    margin: "4px 0 0 0"
  })
);
var snowSlider = ui.Slider({
  min: -1,
  max: 1,
  value: 0,
  step: 0.1,
  style: { stretch: "horizontal", margin: "0 0 2px 0" }
});
sidebar.add(snowSlider);
var snowOffsetLabel = ui.Label("Baseline", {
  fontSize: "11px",
  color: "#2171b5",
  margin: "0 0 2px 8px"
});
sidebar.add(snowOffsetLabel);

sidebar.add(
  ui.Label("Drought severity offset:", {
    fontSize: "11px",
    color: "#555555",
    margin: "6px 0 0 0"
  })
);
var droughtSlider = ui.Slider({
  min: -1,
  max: 1,
  value: 0,
  step: 0.1,
  style: { stretch: "horizontal", margin: "0 0 2px 0" }
});
sidebar.add(droughtSlider);
var droughtOffsetLabel = ui.Label("Baseline", {
  fontSize: "11px",
  color: "#2171b5",
  margin: "0 0 2px 8px"
});
sidebar.add(droughtOffsetLabel);

// Resets both scenario sliders to 0 and refreshes the affected overlay layers
var resetBaselineBtn = ui.Button({
  label: "Reset to Baseline",
  style: { stretch: "horizontal", margin: "8px 0 0 0", fontSize: "11px" }
});
sidebar.add(resetBaselineBtn);

sidebar.add(divider());

// ============================================================
// SECTION 9 — INSPECTOR PANEL UI
// Right-hand panel displaying watershed name, click coordinates,
// and the sampled probability value for the clicked pixel.
// Overlay legend sections for climate, NLCD, and wetlands also live here.
// ============================================================

inspectorPanel.add(
  ui.Label("Pixel Summary", {
    fontWeight: "bold",
    fontSize: "20px",
    color: "#2c3e50",
    margin: "0 0 2px 0"
  })
);
inspectorPanel.add(divider());
inspectorPanel.add(
  bodyLabel(
    "Click anywhere on the map to inspect the probability value at that location."
  )
);

// Displays the name of the watershed containing the clicked point
inspectorPanel.add(sectionLabel("Watershed"));
var watershedOutput = ui.Label("—", {
  fontSize: "13px",
  color: "#2c3e50",
  margin: "2px 0 10px 0"
});
inspectorPanel.add(watershedOutput);

inspectorPanel.add(divider());

// Displays the longitude and latitude of the clicked point
inspectorPanel.add(sectionLabel("Coordinates"));
var lonOutput = ui.Label("Lon: —", {
  fontSize: "13px",
  color: "#2c3e50",
  margin: "2px 0 2px 0"
});
var latOutput = ui.Label("Lat: —", {
  fontSize: "13px",
  color: "#2c3e50",
  margin: "2px 0 10px 0"
});
inspectorPanel.add(lonOutput);
inspectorPanel.add(latOutput);

inspectorPanel.add(divider());

// Displays the watershed model probability at the clicked pixel
inspectorPanel.add(sectionLabel("Meadow Probability (Watershed Model)"));
var probOutput = ui.Label("—", {
  fontSize: "13px",
  color: "#2171b5",
  fontWeight: "bold",
  margin: "2px 0 10px 0"
});
inspectorPanel.add(probOutput);

// Displays the global model probability at the same clicked pixel.
// Sampled from probGlobal in the map.onClick handler below.
inspectorPanel.add(sectionLabel("Meadow Probability (Global Model)"));
var probGlobalOutput = ui.Label("—", {
  fontSize: "13px",
  color: "#2171b5",
  fontWeight: "bold",
  margin: "2px 0 10px 0"
});
inspectorPanel.add(probGlobalOutput);

// Status line: shows sampling errors or out-of-study-area messages
var statusOutput = ui.Label("", {
  fontSize: "11px",
  color: "#999999",
  margin: "4px 0 0 0"
});
inspectorPanel.add(statusOutput);

// Climate overlay gradient legend section — shown/hidden by updateClimateLegend()
inspectorPanel.add(climateInspectorDivider);
inspectorPanel.add(climateInspectorHeader);
inspectorPanel.add(climateInspectorLegendPanel);

// NLCD class swatch legend section — shown/hidden by updateNlcdInspectorLegend()
inspectorPanel.add(nlcdInspectorDivider);
inspectorPanel.add(nlcdInspectorHeader);
inspectorPanel.add(nlcdInspectorLegendPanel);

// NWI Wetlands swatch legend section — shown/hidden by updateWetlandsInspectorLegend()
inspectorPanel.add(wetlandsInspectorDivider);
inspectorPanel.add(wetlandsInspectorHeader);
inspectorPanel.add(wetlandsInspectorLegendPanel);

// ============================================================
// SECTION 10 — EVENT HANDLERS
// All onChange / onClick wiring. Grouped here so the full
// interactive logic is in one place rather than scattered
// through the widget declarations in Sections 8–9.
// ============================================================

// ── Watershed Selection ──────────────────────────────────────

/**
 * Core watershed selection handler. Syncs the search box, dropdown, and
 * suggestion panel, applies the highlight outline, and fires
 * refreshActiveOverlays() to pick up any checkboxes that were toggled
 * on while no watershed was selected.
 *
 * Bails immediately if name is null or empty — this guards against async
 * evaluate callbacks returning null before the feature is resolved.
 *
 * @param {string}  name - Watershed name to select.
 * @param {boolean} zoom - If true, pan and zoom the map to the watershed bounds.
 */
function selectWatershed(name, zoom) {
  if (!name) return; // Guard against null from async evaluate callbacks

  // Sync all three selection widgets to the chosen name
  searchBox.setValue(name, false);
  matchCountLabel.setValue("");
  suggestionPanel.clear();
  suggestionPanel.style().set("shown", false);
  watershedSelect.items().reset(sortedNames);
  watershedSelect.setValue(name, false);

  // Optionally zoom to the watershed's bounding box
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

  // Paint the yellow highlight and refresh any active overlay layers
  applyHighlight(name);
  refreshActiveOverlays();
}

// Search box: filters the suggestion panel as the user types.
// A single match selects that watershed immediately; multiple matches
// show up to 6 clickable suggestion buttons below the box.
searchBox.onChange(function (text) {
  var trimmed = text.trim();
  suggestionPanel.clear();

  if (trimmed === "") {
    // Empty search — reset to full list, clear selection and highlight
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
    filtered.length + " of " + sortedNames.length + " watersheds"
  );

  // Auto-select when the search narrows to exactly one result
  if (filtered.length === 1) {
    selectWatershed(filtered[0], true);
    return;
  }

  // Show up to 6 suggestion buttons; indicate how many more are hidden
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
          border: "none"
        },
        onClick: function () {
          selectWatershed(name, true);
        }
      })
    );
  });
  if (filtered.length > 6) {
    suggestionPanel.add(
      ui.Label("+ " + (filtered.length - 6) + " more — keep typing to narrow", {
        fontSize: "10px",
        color: "#aaaaaa",
        margin: "2px 8px 2px 8px"
      })
    );
  }
  suggestionPanel.style().set("shown", true);
});

// Clear search button: resets search state and removes all overlay layers
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

// Dropdown: selecting a name zooms and highlights that watershed
watershedSelect.onChange(function (name) {
  if (!name) return;
  selectWatershed(name, true);
});

// Clear Selection button: resets all state and removes overlay layers.
// Checkbox state is intentionally preserved so overlays reload on the
// next watershed selection without requiring the user to re-check them.
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

// Clicking the map selects the watershed at that point (without zooming),
// shows coordinates, and samples the probability value from both the
// watershed model and the global model at the clicked location.
map.onClick(function (coords) {
  // Reset inspector outputs while sampling is in progress
  watershedOutput.setValue("Sampling…");
  lonOutput.setValue("Lon: —");
  latOutput.setValue("Lat: —");
  probOutput.setValue("—");
  probGlobalOutput.setValue("—");
  statusOutput.setValue("");

  var point = ee.Geometry.Point([coords.lon, coords.lat]);
  var inWatershed = watershedFC.filterBounds(point);

  // First check whether the click falls inside any study watershed
  inWatershed.size().evaluate(function (count) {
    if (count === 0) {
      watershedOutput.setValue("—");
      statusOutput.setValue(
        "Outside study area. Click inside a watershed boundary."
      );
      clearHighlight();
      return;
    }

    // Show coordinates now that we know the point is in the study area
    lonOutput.setValue("Lon: " + coords.lon.toFixed(5));
    latOutput.setValue("Lat: " + coords.lat.toFixed(5));

    // Resolve the watershed name, then select it and sample both models.
    // selectWatershed guards against null internally, so a null name
    // returned by evaluate will silently no-op rather than crash.
    inWatershed
      .first()
      .get("name")
      .evaluate(function (watershedName) {
        watershedOutput.setValue(watershedName || "—");
        selectWatershed(watershedName, false);

        // Sample the watershed model probability at the clicked pixel
        prob
          .sample({ region: point, scale: 30, numPixels: 1 })
          .first()
          .get(BAND_NAME)
          .evaluate(function (val, error) {
            if (error || val === null) {
              probOutput.setValue("No data");
              statusOutput.setValue(
                "No watershed prediction data available for this location."
              );
            } else {
              probOutput.setValue((val * 100).toFixed(1) + "%");
            }
          });

        // Sample the global model probability at the same clicked pixel.
        // Runs as a separate evaluate call so watershed and global results
        // can appear independently as each resolves.
        probGlobal
          .sample({ region: point, scale: 30, numPixels: 1 })
          .first()
          .get(BAND_NAME)
          .evaluate(function (val, error) {
            if (error || val === null) {
              probGlobalOutput.setValue("No data");
              statusOutput.setValue(
                "No global prediction data available for this location."
              );
            } else {
              probGlobalOutput.setValue((val * 100).toFixed(1) + "%");
            }
          });
      });
  });
});

// ── Probability Layer Controls ───────────────────────────────

// Layer handles declared here so updateProbLayer() and restackTopLayers()
// can reference them before either layer has been added to the map.
var currentLayer = null; // Watershed model probability layer
var currentGlobalLayer = null; // Global model probability layer
var watershedLayer = null; // Red HUC10 boundary outline (initialized in Section 12)

/**
 * Re-renders both meadow probability layers using the current slider and
 * checkbox values. The watershed layer uses currentPalette and the global
 * layer uses currentGlobalPalette, allowing them to be shown in different
 * colors simultaneously. The global layer is drawn beneath the watershed
 * layer so watershed predictions remain visible on top when both are active.
 *
 * Called whenever opacity, threshold, visibility, or either palette changes.
 */
function updateProbLayer() {
  var threshold = thresholdSlider.getValue();
  var opacity = opacitySlider.getValue();
  var visible = toggleCheck.getValue();
  var visibleGlobal = toggleGlobalCheck.getValue();

  // Update the threshold readout label
  thresholdReadout.setValue("Threshold: " + threshold.toFixed(2));

  // Apply the probability threshold mask to both prediction images.
  // Pixels below the threshold are masked out (transparent).
  var display = prob.updateMask(prob.gte(threshold));
  var displayGlobal = probGlobal.updateMask(probGlobal.gte(threshold));

  // Replace the watershed model layer using the watershed palette
  if (currentLayer) map.remove(currentLayer);
  currentLayer = ui.Map.Layer(
    display,
    { min: 0, max: 1, palette: currentPalette },
    "Meadow Probability (Watershed)",
    visible,
    opacity
  );
  map.add(currentLayer);

  // Replace the global model layer using its own independent palette.
  // Added before the watershed layer so it renders underneath — the global
  // predictions are visible where no watershed predictions exist, and both
  // can be compared by adjusting opacity.
  if (currentGlobalLayer) map.remove(currentGlobalLayer);
  currentGlobalLayer = ui.Map.Layer(
    displayGlobal,
    { min: 0, max: 1, palette: currentGlobalPalette },
    "Meadow Probability (Global)",
    visibleGlobal,
    opacity
  );
  map.add(currentGlobalLayer);

  // Keep the watershed boundary and highlight on top of both probability layers
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

// Wire all layer control widgets to updateProbLayer()
opacitySlider.onChange(function () {
  updateProbLayer();
});
thresholdSlider.onChange(function () {
  updateProbLayer();
});
toggleCheck.onChange(function () {
  updateProbLayer();
});
toggleGlobalCheck.onChange(function () {
  updateProbLayer();
}); // Global model toggle
watershedCheck.onChange(function (val) {
  // Show/hide the boundary layer without rebuilding the probability layers
  if (watershedLayer) watershedLayer.setShown(val);
});

// Watershed palette change: updates currentPalette, rebuilds the legend,
// and re-renders only the watershed probability layer.
paletteSelect.onChange(function (val) {
  currentPalette = PALETTES[val];
  updateMeadowLegend();
  updateProbLayer();
});

// Global palette change: updates currentGlobalPalette, rebuilds the legend,
// and re-renders only the global probability layer via updateProbLayer().
globalPaletteSelect.onChange(function (val) {
  currentGlobalPalette = PALETTES[val];
  updateMeadowLegend();
  updateProbLayer();
});

// Basemap switcher — no layer rebuild needed
basemapSelect.onChange(function (val) {
  map.setOptions(val);
});

// ── Climate Overlay Toggles ──────────────────────────────────
// Toggling ON fires the refresh immediately if a watershed is selected;
// if not, the checkbox state is saved and refreshActiveOverlays() picks
// it up on the next watershed selection.
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
    if (wetlandsPFOLayer) {
      map.remove(wetlandsPFOLayer);
      wetlandsPFOLayer = null;
    }
    restackTopLayers();
  }
  updateWetlandsInspectorLegend(val);
});

// ── Scenario Sliders ─────────────────────────────────────────

// Snowpack scenario slider: shifts the SWE vis-params range.
// Label updates to reflect percentage above or below baseline.
snowSlider.onChange(function (val) {
  var pct = Math.round(val * 100);
  snowOffsetLabel.setValue(
    pct === 0
      ? "Baseline"
      : pct > 0
        ? "+" + pct + "% (above avg)"
        : pct + "% (below avg)"
  );
  if (snowCheck.getValue() && watershedSelect.getValue()) refreshSnow();
});

// Drought scenario slider: shifts the PDSI vis-params range.
// Label updates to reflect drier or wetter conditions.
droughtSlider.onChange(function (val) {
  var pct = Math.round(val * 100);
  droughtOffsetLabel.setValue(
    pct === 0
      ? "Baseline"
      : pct > 0
        ? "+" + pct + "% (drier)"
        : Math.abs(pct) + "% (wetter)"
  );
  if (droughtCheck.getValue() && watershedSelect.getValue()) refreshDrought();
});

// Reset button: returns both scenario sliders to 0 and refreshes active overlays
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
// Two gradient bars in the sidebar: one for the watershed model
// and one for the global model. Each bar uses its own palette so
// the legend always matches what is displayed on the map.
// Rebuilt by updateMeadowLegend() whenever either palette changes.
// ============================================================

/**
 * Rebuilds both gradient color bar legends for the meadow probability layers.
 * The watershed bar uses currentPalette; the global bar uses currentGlobalPalette.
 * Called on initialization and whenever either palette selector changes.
 */
function updateMeadowLegend() {
  legendPanel.clear();
  // Watershed model gradient bar
  legendPanel.add(
    buildGradientLegend(
      "Watershed Model",
      currentPalette,
      "0 — Low",
      "1 — High"
    )
  );
  // Global model gradient bar — shown below the watershed bar
  legendPanel.add(
    buildGradientLegend(
      "Global Model",
      currentGlobalPalette,
      "0 — Low",
      "1 — High"
    )
  );
}

// Draw the initial legend using the default Blue palette
updateMeadowLegend();

// ============================================================
// SECTION 12 — INITIALIZATION
// Adds base layers and centers the map. Called last so all
// handler functions and layer variable declarations are already
// in scope before any layer is added to the map.
// ============================================================

// Center the map on the full study area bounding box at zoom 8 on load
watershedFC
  .geometry()
  .bounds()
  .evaluate(function (bounds) {
    map.centerObject(ee.Geometry(bounds), 8);
  });

// Add the red HUC10 watershed boundary outline as a base layer.
// This layer is always present; the watershedCheck checkbox shows/hides it.
var watershedOutline = ee.Image().byte().paint({
  featureCollection: watershedFC,
  color: 1,
  width: 2
});
watershedLayer = ui.Map.Layer(
  watershedOutline,
  { palette: ["FF0000"] },
  "Watershed Boundary",
  true,
  0.8
);
map.add(watershedLayer);

// Draw both probability layers using initial slider and checkbox values.
// updateProbLayer() also adds currentGlobalLayer beneath currentLayer,
// and restacks the watershed boundary and highlight on top.
updateProbLayer();
