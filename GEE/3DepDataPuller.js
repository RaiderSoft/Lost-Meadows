// Bounding box covering the study region in southern Oregon / northern California.
// Used to spatially filter the national watershed dataset down to relevant HUC10 units.
var studyArea = ee.Geometry.Polygon([
  [
    [-124.65, 41.8],
    [-121.75, 41.8],
    [-121.75, 43.35],
    [-124.65, 43.35],
    [-124.65, 41.8],
  ],
]);

// USGS Watershed Boundary Dataset at the HUC10 (sub-watershed) level.
var watersheds = ee.FeatureCollection("USGS/WBD/2017/HUC10");
// Narrow to only the HUC10 polygons that intersect the study area.
var studyWatersheds = watersheds.filterBounds(studyArea);

// Pull the HUC10 ID and human-readable name for every watershed in the study area.
// These two parallel arrays drive the export loop below.
var huc10Ids = studyWatersheds.aggregate_array("huc10");
var wsNames = studyWatersheds.aggregate_array("name");

// evaluate() transfers the server-side GEE lists into client-side JavaScript so
// we can iterate over them synchronously with forEach and queue one export per watershed.
ee.List([huc10Ids, wsNames]).evaluate(function (lists) {
  var ids = lists[0];
  var names = lists[1];
  print("Total watersheds:", ids.length);

  ids.forEach(function (huc10Id, i) {
    var rawName = names[i] || "unnamed";
    // Strip any character that isn't alphanumeric so the name is safe to use as a filename.
    var wsName = rawName.replace(/[^a-zA-Z0-9]/g, "_");
    var fileLabel = wsName;

    // Retrieve the geometry for this specific HUC10 watershed.
    var watershedGeom = studyWatersheds
      .filter(ee.Filter.eq("huc10", huc10Id))
      .first()
      .geometry();

    // Build the elevation layer from the USGS 3DEP 10m collection:
    //   - filterBounds: only load tiles that overlap this watershed
    //   - resample bilinear: smooth interpolation before reprojection
    //   - reproject to EPSG:5070 (Albers Equal Area CONUS) at 10 m resolution
    //   - mean: mosaic overlapping tiles by averaging
    //   - clip: trim to the watershed boundary
    var elevation = ee
      .ImageCollection("USGS/3DEP/10m_collection")
      .filterBounds(watershedGeom)
      .map(function (img) {
        return img
          .select("elevation")
          .resample("bilinear")
          .reproject({ crs: "EPSG:5070", scale: 10 });
      })
      .mean()
      .clip(watershedGeom);

    // Export each watershed's elevation raster to the "3DEPData" folder in Google Drive
    // as a cloud-optimized GeoTIFF at 10 m in Albers Equal Area (EPSG:5070).
    // maxPixels is set high (1e13) to handle large watersheds without hitting the default cap.
    Export.image.toDrive({
      image: elevation,
      description: "3DEP_" + fileLabel,
      folder: "3DEPData",
      fileNamePrefix: "3DEP_FIXED_" + fileLabel,
      region: watershedGeom,
      scale: 10,
      crs: "EPSG:5070",
      maxPixels: 1e13,
      fileFormat: "GeoTIFF",
      formatOptions: { cloudOptimized: true },
    });

    print("Queued:", fileLabel);
  });
});
