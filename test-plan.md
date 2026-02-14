# Test Cases

## Feature Testing


## 1.1 Feature 1: Identify Lost Meadows

| Test ID | Test Description | Steps | Expected Result |
|:--------|:-----------------|:------|:----------------|
| F1-TC01 | Verify Lost Meadows display on map load | 1. Launch app<br>2. Wait for map to load | Lost Meadows visible within 10–20 seconds |
| F1-TC02 | Verify confidence scores display | 1. Click on Lost Meadow<br>2. View details | Probability/confidence value shown |
| F1-TC03 | Test false positive handling | 1. Click on questionable meadow<br>2. Check metadata | Disclaimer/accuracy info available |

---

### 1.2 Feature 2: Site to App Connection

| Test ID | Test Description | Steps | Expected Result |
|:--------|:-----------------|:------|:----------------|
| F2-TC01 | Verify launch button works | 1. Navigate to static site<br>2. Click "Launch App" | GEE app opens |
| F2-TC02 | Test unsupported browser | 1. Access on old browser version | Warning banner displays |
| F2-TC03 | Test JavaScript disabled | 1. Disable JavaScript<br>2. Try to load app | Error message shown |

---

### 1.3 Feature 3: Filter by Watershed

| Test ID | Test Description | Steps | Expected Result |
|:--------|:-----------------|:------|:----------------|
| F3-TC01 | Verify watershed search | 1. Open dropdown<br>2. Type watershed name | Results filter in <1 second |
| F3-TC02 | Test fuzzy matching | 1. Enter misspelled name | Suggestions shown |
| F3-TC03 | Test "no results found" | 1. Enter invalid name | Helpful error message |
| F3-TC04 | Verify map zoom to watershed | 1. Select watershed<br>2. View map | Map centers on watershed |

---

### 1.4 Feature 4: Slider Changing Conditions

| Test ID | Test Description | Steps | Expected Result |
|:--------|:-----------------|:------|:----------------|
| F4-TC01 | Verify slider adjustments update map | 1. Move snowpack slider<br>2. Observe changes | Map updates within 10–20 seconds |
| F4-TC02 | Test extreme slider values | 1. Move slider to max<br>2. Check results | Warning if no results |
| F4-TC03 | Verify tooltip explanations | 1. Hover over info icon | Plain language explanation |
| F4-TC04 | Test multiple slider interactions | 1. Adjust both sliders<br>2. Check performance | No lag or crashes |

---

### 1.5 Feature 5: Export Information

| Test ID | Test Description | Steps | Expected Result |
|:--------|:-----------------|:------|:----------------|
| F5-TC01 | Verify CSV export | 1. Select meadow<br>2. Click export<br>3. Choose CSV | File downloads with data |
| F5-TC02 | Verify GeoJSON export | 1. Select meadow<br>2. Click export<br>3. Choose GeoJSON | File downloads with spatial data |
| F5-TC03 | Check export metadata | 1. Open exported file | Headers include date, parameters, citations |

---

## 2. Performance Testing

### 2.1 Load Time Tests

| Test ID | Metric | Target | Method |
|:--------|:--------|:--------|:--------|
| P-TC01 | Initial map load | <10–20 seconds | Browser developer tools |
| P-TC02 | Layer rendering | <4–5 seconds | Toggle layers and measure |
| P-TC03 | Search response | <1 second | Type in search and measure |
| P-TC04 | Slider updates | <10–20 seconds | Adjust slider and measure render |

---

### 2.2 Concurrent User Testing

**Test Procedure:**

- Simulate 50–100 concurrent users  
- Monitor response times and errors  
- Document any performance degradation  

**Expected Result:**

- No crashes  
- Acceptable response times  
- No critical errors  

---

## 3. Compatibility Testing

| Browser | Version | Operating System | 
|:--------|:--------|:-----------------|
| Chrome | Latest | Windows 10/11 |
| Chrome | Latest | macOS |
| Firefox | Latest | Windows 10/11 |
| Firefox | Latest | macOS |
| Safari | Latest | macOS |
| Edge | Latest | Windows 10/11 |

---
