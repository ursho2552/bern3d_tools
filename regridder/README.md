# Bern3D Regridder Module

This module provides utilities for regridding observational datasets (WOA, OCIM, etc.) to the Bern3D model grid. It automates the process of interpolating data from various oceanographic datasets to match the Bern3D grid resolution and coordinate system.

---

## Table of Contents

- [Overview](#overview)
- [How It Works](#how-it-works)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Directory Structure](#directory-structure)
- [Extending and Customization](#extending-and-customization)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

This module automates the regridding process for oceanographic datasets to the Bern3D model grid. It handles coordinate transformations, vertical interpolation, and horizontal regridding while preserving data quality and physical consistency.

**Key features:**
- Automated regridding from WOA (World Ocean Atlas) datasets to Bern3D grid
- Support for multiple variables (temperature, salinity, nutrients, oxygen)
- Vertical interpolation using linear methods
- Horizontal regridding using bilinear interpolation via xESMF
- Proper handling of NetCDF encodings and metadata
- Integration of ideal age data from OCIM (Ocean Circulation Inverse Model)

---

## How It Works

1. **Data Loading:**
   Loads source datasets (WOA2023, OCIM) and target Bern3D grid template

2. **Coordinate Standardization:**
   Harmonizes dimension names and coordinate systems between datasets

3. **Vertical Interpolation:**
   Interpolates data vertically to match Bern3D depth levels using linear interpolation

4. **Horizontal Regridding:**
   Uses xESMF bilinear regridding to match Bern3D horizontal grid (68x46)

5. **Output Generation:**
   Creates NetCDF4-classic compatible files with proper metadata and encoding

---

## Installation

Clone the repository and set up the conda environment:

```bash
git clone <repository-url>
cd bern3d_tools/regridder
conda env create -f requirements.yml
conda activate py3_regrid
```

**Required dependencies:**
- Python 3.11
- xarray
- numpy
- matplotlib
- esmpy
- xesmf
- netcdf4
- scipy

---

## Configuration

The regridder has to be customized for each variable. Here, in the notebook, we show how the utility functions can be used.

**Key configuration elements:**

**Input Data Sources:**
```python
# WOA2023 data directory
woa_dir = "/path/to/WOA2023/"

# OCIM ideal age data
file = "/path/to/OCIM/ideal_age.nc"

# Bern3D template grid
path_bern3d_observations = "/path/to/bern3d/world_68x46.observations.nc"
```

**Variable Mapping:**
```python
# WOA/OCIM variable names to Bern3D variable names
bern3d_variables = {
    'p_an': 'po4',      # Phosphate
    'n_an': 'no3',      # Nitrate
    'i_an': 'sio',      # Silicate
    'o_an': 'o2',       # Oxygen
    's_an': 'salt',     # Salinity
    't_an': 'temp',     # Temperature
    'ideal_age': 'ida'  # Ideal Age
}
```

**Dimension Mapping:**
```python
# Source dimension names to standard names
dim_dictionary = {
    'lon': 'Longitude',
    'lat': 'Latitude',
    'depth': 'Depth'
}
```

---

## Usage

### Basic Regridding Workflow

1. **Set up your data paths**
   Edit the file paths in the notebook to point to your WOA and OCIM datasets.

2. **Run the regridding notebook:**
   ```bash
   jupyter notebook Regrid_WOA.ipynb
   ```

3. **Execute all cells to:**
   - Load source datasets
   - Perform vertical interpolation
   - Execute horizontal regridding
   - Generate regridded NetCDF file

### Using the Utility Functions

```python
import utils as my_utils
import xarray as xr

# Load datasets
ds_observation = xr.open_dataset('woa_data.nc')
template_grid = xr.open_dataset('bern3d_template.nc')

# Regrid a single variable
regridded_data = my_utils.regrid_to_bern3d(
    ds_observation,
    'temperature',
    template_grid,
    dim_dictionary={'lon': 'longitude', 'lat': 'latitude', 'depth': 'depth'}
)

# Clean encodings for NetCDF output
valid_encodings = {'zlib', 'complevel', 'shuffle', 'fletcher32', '_FillValue'}
encoding = my_utils.clean_encodings(regridded_data, valid_encodings)
```

---

## Directory Structure

```
regridder/
├── Regrid_WOA.ipynb      # Main notebook for WOA regridding workflow
├── utils.py              # Utility functions for regridding operations
├── requirements.yml      # Conda environment specification
└── README.md            # This documentation file
```

**File descriptions:**
- **`Regrid_WOA.ipynb`** — Interactive notebook demonstrating the complete regridding workflow
- **`utils.py`** — Core regridding functions and NetCDF utilities
- **`requirements.yml`** — Conda environment with all required dependencies

---

## Extending and Customization

### Adding New Variables
```python
# Add new variable mappings in the notebook
variables_to_regrid['new_var'] = xr.open_dataset('new_dataset.nc')
bern3d_variables['new_var'] = 'new_bern3d_name'
attributes['new_var'] = {'units': 'units', 'long_name': 'description'}
```

### Supporting New Data Sources
- Modify dimension mapping in `dim_dictionary`
- Add coordinate standardization for new coordinate systems
- Update variable attributes as needed

### Custom Interpolation Methods
- Modify the `regrid_to_bern3d` function in `utils.py`
- Change interpolation method from 'linear' to 'nearest' or other xarray methods
- Adjust regridding method from 'bilinear' to 'conservative' or other xESMF methods

### Output Format Customization
- Modify NetCDF encoding settings
- Add custom metadata and attributes
- Change output file naming conventions

---

## Troubleshooting

### Common Issues

**Missing coordinate information:**
```python
# Ensure datasets have proper coordinate names
ds = ds.assign_coords(Depth=("Depth", ds['zt'].values))
```

**NetCDF encoding errors:**
```python
# Clean encodings before saving
encoding = my_utils.clean_encodings(dataset, valid_encodings_nc4)
dataset.to_netcdf('output.nc', encoding=encoding, format="NETCDF4_CLASSIC")
```

**Dimension mismatch:**
- Check that dimension names match between source and target grids
- Verify coordinate bounds and resolution compatibility

**Memory issues with large datasets:**
- Process variables individually rather than all at once
- Use chunking for large datasets: `ds.chunk({'time': 1})`

**Interpolation artifacts:**
- Check for missing values and land/ocean masks
- Verify that source and target grids have reasonable overlap

---

## Contributing

Contributions are welcome! Please open issues or submit pull requests for:
- Bug fixes and improvements
- Support for additional data sources
- New interpolation or regridding methods
- Documentation enhancements
- Performance optimizations

---

## License

This project is licensed under the MIT License. See the LICENSE file for details.

---
