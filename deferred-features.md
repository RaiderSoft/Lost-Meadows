# Lost Meadows Climate Adaptation Tool — Deferred Features

## Overview

The Lost Meadows tool successfully delivered its first two features this term:

1. **Identify Lost Meadows** — ML-powered prediction of lost and degraded meadow locations displayed on an interactive Google Earth Engine map.
2. **Site to App Connection** — A static landing website with a direct link that launches the GEE application.

The following three features were scoped in the PRD but deferred due to time and complexity constraints. They are the top priorities for next term.

---

## Feature 3: Filter by Watershed

### Summary

Users will be able to select a specific watershed from a dropdown menu within the GEE application, zooming the map to display only that watershed and the meadows within it.

### What the Feature Does

- The GEE app presents a dropdown menu listing available watersheds in the Cascade-Siskiyou Bioregion.
- Selecting a watershed zooms the map to that area and displays all identified and predicted meadows within it.
- The app uses fuzzy matching to handle minor spelling variations or abbreviations in watershed names.
- If no results are found, the app displays a helpful message suggesting the user browse the full list or zoom to their area of interest.

### Known Risks

- Desired watershed may not be contained in the available list.
- Users may search with spelling variations or abbreviations.
- Multiple watersheds may share similar names.

### Definition of Done

Users launch the GEE application, select their desired watershed from the dropdown menu, and the map zooms to display that watershed with all associated meadow predictions.

---

## Feature 4: Slider Changing Conditions

### Summary

Users will be able to adjust environmental condition sliders — such as snowpack and drought intensity — within the GEE application. The sliders control a visual overlay that displays how those conditions manifest across the landscape; the underlying meadow predictions remain fixed. This allows users to contextualize predicted meadow locations against current or forecasted environmental stress.

### What the Feature Does

- The GEE app presents sliders on the side panel for key environmental variables (snowpack and drought/EDDI).
- Adjusting sliders updates a visual overlay showing how those conditions manifest across the landscape; the underlying meadow predictions do not change.

### Known Risks

- Desired slider variables may not be available in GEE at the required resolution.
- Extreme values may produce no results or unrealistic scenarios.

### Definition of Done

Users launch the GEE application, adjust snowpack and drought sliders, and the meadow probability map updates within 4–6 seconds to reflect the new conditions.

---

## Feature 5: Export Information

### Summary

Users will be able to export information about specific meadows (acreage, rainfall, snowfall, upstream area, etc.) from the GEE application to a downloadable file for offline use.

### What the Feature Does

- The GEE app includes an export button that packages meadow data for the selected area into a downloadable file.
- Supported export formats include CSV, GeoJSON, and Shapefile to maximize compatibility.
- Exported files include a metadata header with the export date, parameters used, and data source citations.

### Known Risks

- Desired data may not be available for all meadow locations.
- Export file format may be incompatible with the user's field software.
- Exported data may lack important metadata or context if not carefully structured.

### Definition of Done

Users launch the GEE application, filter to their desired location, press the export button, and successfully download a file containing meadow information with complete metadata.

---

## Next Steps

These three features should be implemented in the following recommended order based on dependency and complexity:

1. **Filter by Watershed** — Foundational UX improvement; enables users to scope the map before interacting with other features.
2. **Slider Changing Conditions** — Builds on the filtered view; requires climate data integration and GEE UI panel work.
3. **Export Information** — Can be implemented last as it depends on the filtered/scoped view being in place.
