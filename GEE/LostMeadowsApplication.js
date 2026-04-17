// ============================================================
// Meadow Probability Viewer — Google Earth Engine App
// ============================================================

var FOLDER_ID = "projects/lost-meadows/assets/MeadowPredictions";
var BAND_NAME = "b1";
var VALUE_SCALE = 1;
var WATERSHEDS = "projects/lost-meadows/assets/study_watersheds_HUC10";

var EXCLUDED_WATERSHEDS = [
  "171003060500-Pacific Ocean",
  "Mack Arch Cove-Pacific Ocean",
  "North Cove-Pacific Ocean",
];

var assetList = ee.data.listAssets(FOLDER_ID);

var imageIds = assetList.assets
  .filter(function (a) {
    return a.type === "IMAGE";
  })
  .map(function (a) {
    return a.name;
  });

var collection = ee.ImageCollection(
  imageIds.map(function (id) {
    return ee.Image(id).select(BAND_NAME);
  }),
);

var prob = collection.mosaic().divide(VALUE_SCALE);

var watershedFC = ee
  .FeatureCollection(WATERSHEDS)
  .filter(ee.Filter.inList("name", EXCLUDED_WATERSHEDS).not());

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

var PALETTES = {
  Blue: ["#f7fbff", "#c6dbef", "#6baed6", "#2171b5", "#084594"],
  Red: ["#fff5f0", "#fcbba1", "#fb6a4a", "#cb181d", "#67000d"],
  "Teal-Yellow": ["#ffffcc", "#a1dab4", "#41b6c4", "#2c7fb8", "#253494"],
};

var currentPalette = PALETTES["Blue"];

// ============================================================
// UI LAYOUT
// ============================================================

var map = ui.root.widgets().get(0);
map.setOptions("HYBRID");

var sidebar = ui.Panel({
  style: { width: "300px", padding: "10px", backgroundColor: "#f5f5f5" },
});

var inspectorPanel = ui.Panel({
  style: { width: "260px", padding: "10px", backgroundColor: "#f5f5f5" },
});

var mapWrapper = ui.Panel({
  style: { stretch: "both" },
});

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
// HELPER FUNCTIONS
// ============================================================

function sectionLabel(text) {
  return ui.Label(text, {
    fontWeight: "bold",
    fontSize: "14px",
    color: "#333333",
    margin: "12px 0 4px 0",
  });
}

function bodyLabel(text) {
  return ui.Label(text, {
    fontSize: "11px",
    color: "#666666",
    margin: "0 0 6px 0",
  });
}

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
// HIGHLIGHT HELPER
// ============================================================

var highlightLayer = null;

function applyHighlight(name) {
  var selected = watershedFC.filter(ee.Filter.eq("name", name));

  var highlight = ee.Image().byte().paint({
    featureCollection: selected,
    color: 1,
    width: 3,
  });

  if (highlightLayer) map.remove(highlightLayer);
  highlightLayer = ui.Map.Layer(
    highlight,
    { palette: ["FFFF00"] },
    "Selected Watershed",
    true,
    1,
  );
  map.add(highlightLayer);
}

function clearHighlight() {
  if (highlightLayer) map.remove(highlightLayer);
  highlightLayer = null;
}

// ============================================================
// SIDEBAR — TITLE
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
// SIDEBAR — WATERSHED NAVIGATOR
// ============================================================

sidebar.add(sectionLabel("Watershed Navigator"));
sidebar.add(
  bodyLabel(
    "Type to search, use the dropdown, or click a watershed on the map.",
  ),
);

var sortedNames = watershedNames.slice().sort();

// ── Search textbox ───────────────────────────────────────────
var searchBox = ui.Textbox({
  placeholder: "Search watersheds…",
  style: { stretch: "horizontal", margin: "0 0 2px 0" },
});
sidebar.add(searchBox);

// ── Clear search button ──────────────────────────────────────
var searchClearBtn = ui.Button({
  label: "Clear search",
  style: { stretch: "horizontal", margin: "0 0 2px 0" },
  onClick: function () {
    searchBox.setValue("", false);
    suggestionPanel.clear();
    suggestionPanel.style().set("shown", false);
    matchCountLabel.setValue("");
    watershedSelect.items().reset(sortedNames);
    watershedSelect.setValue(null, false);
    clearHighlight();
  },
});
sidebar.add(searchClearBtn);

// ── Match count label ────────────────────────────────────────
var matchCountLabel = ui.Label("", {
  fontSize: "10px",
  color: "#888888",
  margin: "0 0 2px 0",
});
sidebar.add(matchCountLabel);

// ── Autocomplete suggestion list ─────────────────────────────
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

// ── Dropdown — alternative to search ────────────────────────
var watershedSelect = ui.Select({
  items: sortedNames,
  placeholder: "Or select a watershed…",
  style: { stretch: "horizontal", margin: "0 0 4px 0" },
});
sidebar.add(watershedSelect);

// ============================================================
// SELECT WATERSHED
// zoom=true  → also pan/zoom the map (navigator + single match)
// zoom=false → highlight only, no zoom (map click)
// ============================================================

function selectWatershed(name, zoom) {
  suggestionPanel.clear();
  suggestionPanel.style().set("shown", false);
  searchBox.setValue(name, false);
  matchCountLabel.setValue("");

  watershedSelect.items().reset(sortedNames);
  watershedSelect.setValue(name, false);

  if (zoom) {
    var selected = watershedFC.filter(ee.Filter.eq("name", name));
    selected
      .first()
      .geometry()
      .bounds()
      .evaluate(function (bounds) {
        map.centerObject(ee.Geometry(bounds), 11);
      });
  }

  applyHighlight(name);
}

// ── Search box onChange — rebuilds suggestion list ───────────
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

  // Auto-select and zoom if exactly one match
  if (filtered.length === 1) {
    selectWatershed(filtered[0], true);
    return;
  }

  // Show up to 6 suggestions as clickable rows
  var maxSuggestions = 6;
  var shown = filtered.slice(0, maxSuggestions);

  shown.forEach(function (name) {
    var btn = ui.Button({
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
    });
    suggestionPanel.add(btn);
  });

  if (filtered.length > maxSuggestions) {
    suggestionPanel.add(
      ui.Label(
        "+ " +
          (filtered.length - maxSuggestions) +
          " more — keep typing to narrow",
        { fontSize: "10px", color: "#aaaaaa", margin: "2px 8px 2px 8px" },
      ),
    );
  }

  suggestionPanel.style().set("shown", true);
});

// ── Dropdown onChange — zooms to selected watershed ──────────
watershedSelect.onChange(function (name) {
  if (!name) return;
  selectWatershed(name, true);
});

// ── Clear selection button ───────────────────────────────────
var clearButton = ui.Button({
  label: "Clear Selection",
  style: { stretch: "horizontal", margin: "4px 0 0 0" },
  onClick: function () {
    clearHighlight();
    watershedSelect.items().reset(sortedNames);
    watershedSelect.setValue(null, false);
    searchBox.setValue("", false);
    matchCountLabel.setValue("");
    suggestionPanel.clear();
    suggestionPanel.style().set("shown", false);
  },
});
sidebar.add(clearButton);

sidebar.add(divider());

// ============================================================
// SIDEBAR — LAYER CONTROLS
// ============================================================

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
watershedCheck.onChange(function (val) {
  watershedLayer.setShown(val);
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

// ============================================================
// SIDEBAR — COLOR SCHEME
// ============================================================

sidebar.add(sectionLabel("Color Scheme"));

var paletteSelect = ui.Select({
  items: Object.keys(PALETTES),
  value: "Blue",
  style: { stretch: "horizontal", margin: "0 0 4px 0" },
});
paletteSelect.onChange(function (val) {
  currentPalette = PALETTES[val];
  updateLegend();
  updateLayer();
});
sidebar.add(paletteSelect);

sidebar.add(divider());

// ============================================================
// SIDEBAR — BASEMAP
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
// SIDEBAR — LEGEND
// ============================================================

sidebar.add(sectionLabel("Legend"));

var legendPanel = ui.Panel({ style: { margin: "0 0 6px 0" } });
sidebar.add(legendPanel);

function updateLegend() {
  legendPanel.clear();
  var gradientBar = ui.Thumbnail({
    image: ee.Image.pixelLonLat()
      .select("longitude")
      .unitScale(-180, 180)
      .visualize({ min: 0, max: 1, palette: currentPalette }),
    params: { bbox: "-180,-10,180,10", dimensions: "255x16", format: "png" },
    style: { stretch: "horizontal", margin: "0", height: "16px" },
  });
  legendPanel.add(gradientBar);
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

// ============================================================
// INSPECTOR PANEL — PIXEL SUMMARY
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

// ── Watershed field ──────────────────────────────────────────
inspectorPanel.add(sectionLabel("Watershed"));
var watershedOutput = ui.Label("—", {
  fontSize: "13px",
  color: "#2c3e50",
  margin: "2px 0 10px 0",
});
inspectorPanel.add(watershedOutput);

inspectorPanel.add(divider());

// ── Coordinates field ────────────────────────────────────────
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

// ── Meadow probability field ─────────────────────────────────
inspectorPanel.add(sectionLabel("Meadow Probability"));
var probOutput = ui.Label("—", {
  fontSize: "13px",
  color: "#2171b5",
  fontWeight: "bold",
  margin: "2px 0 10px 0",
});
inspectorPanel.add(probOutput);

// ── Status / error message ───────────────────────────────────
var statusOutput = ui.Label("", {
  fontSize: "11px",
  color: "#999999",
  margin: "4px 0 0 0",
});
inspectorPanel.add(statusOutput);

// ============================================================
// MAP CLICK HANDLER
// ============================================================

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
      lonOutput.setValue("Lon: —");
      latOutput.setValue("Lat: —");
      probOutput.setValue("—");
      statusOutput.setValue(
        "Outside study area. Click inside a watershed boundary.",
      );
      clearHighlight();
      return;
    }

    lonOutput.setValue("Lon: " + coords.lon.toFixed(5));
    latOutput.setValue("Lat: " + coords.lat.toFixed(5));

    inWatershed
      .first()
      .get("name")
      .evaluate(function (watershedName) {
        watershedOutput.setValue(watershedName);

        // Highlight only — no zoom on map click
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
              statusOutput.setValue("");
            }
          });
      });
  });
});

// ============================================================
// MAIN LAYER RENDER FUNCTION
// ============================================================

var currentLayer = null;

function updateLayer() {
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
// ============================================================

watershedFC
  .geometry()
  .bounds()
  .evaluate(function (bounds) {
    map.centerObject(ee.Geometry(bounds), 8);
  });

var watershedOutline = ee.Image().byte().paint({
  featureCollection: watershedFC,
  color: 1,
  width: 2,
});

var watershedLayer = ui.Map.Layer(
  watershedOutline,
  { palette: ["FF0000"] },
  "Watershed Boundary",
  true,
  0.8,
);
map.add(watershedLayer);

updateLayer();
