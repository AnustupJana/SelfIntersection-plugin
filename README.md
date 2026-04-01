# Self Intersection Check QGIS Plugin
![Diagram of the System](https://github.com/AnustupJana/SelfIntersection-plugin/blob/main/icon.png?raw=true)

## Overview
The **Self Intersection Check** plugin for QGIS detects invalid polygon geometries such as **self-intersections** and **overlapping features**. It helps users quickly identify problematic geometries in spatial datasets and visualize them clearly using styled output layers.

This plugin is especially useful for:
- Cadastral data validation
- GIS data cleaning
- Topology error detection
- Pre-processing before spatial analysis

---

## Features
- **Detect Self-Intersections**: Identifies invalid polygon geometries using GEOS validation and buffer checks.
- **Detect Overlaps**: Finds overlapping polygon features using spatial indexing for performance.
- **Automatic Geometry Fixing**: Internally runs *Fix Geometries* before validation.
- **Styled Output Layer**:
  - Red boundary
  - Dashed hatch fill for easy visualization
- **Processing Toolbox Integration**: Works as a native processing algorithm.
- **Toolbar & Menu Access**:
  - Available in **Vector menu**
  - Available in **Toolbar with icon**

---

## Installation

### 1. From ZIP File
- Go to: `Plugins > Manage and Install Plugins > Install from ZIP`
- Select your plugin ZIP file
- Click **Install**

---

### 2. Manual Installation
- Copy plugin folder to:

**Windows:**
C:\Users<YourUsername>\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\

**Linux:**
~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/

**macOS:**
~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/

- Restart QGIS

-----------------------------------

## Usage

### 1. Open the Tool
- Go to:
  - **Vector > Self Intersection Check**
  - OR click the toolbar icon

---

### 2. Run the Tool
- Select your **polygon layer**
- Click **Run**

---

### 3. Output
- A new layer named **Self-Intersection** will be created
- It contains:
  - Invalid polygons
  - Overlapping polygons
  - A `Reason` field explaining the issue

---

## Output Style
- **Boundary**: Red
- **Fill**: Black dashed hatch pattern
- Designed for clear visualization of topology errors

---

## Requirements
- **QGIS Version**: 3.0 – 3.99
- **Input Layer**: Polygon only

---

## Troubleshooting

### Plugin not visible
- Check plugin folder location
- Restart QGIS
- Verify `metadata.txt`

---

### No output features
- Ensure input layer has:
  - Self-intersections OR overlaps
- Try running:
  - `Fix Geometries`
  - `Check Validity`

---

### Errors in Processing
- Open **Python Console (Ctrl+Alt+P)**
- Check logs for debugging

---

## Contributing
- Fork the repository
- Submit pull requests
- Report issues on GitHub

---

## License
This plugin is licensed under the **GNU General Public License v2.0 or later**.  
See the LICENSE file for details.

---

## Author
**Anustup Jana**  
📧 anustupjana21@gmail.com  

© 2026 Anustup Jana
