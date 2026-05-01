def simulation_finished(log_path: str) -> bool:
    """
    Returns True if 'SIMULATION COMPLETE' appears anywhere in the file.
    """
    needle = "SIMULATION COMPLETE"
    with open(log_path, 'r', encoding='utf-8') as my_file:
        for line in my_file:
            if needle in line:
                return True
    return False

def nrmse(predictions: npt.ArrayLike, targets: npt.ArrayLike,
          weights: Optional[npt.ArrayLike] = None) -> float:
    """
    Calculate the Normalized Root Mean Square Error (NRMSE) between predictions and targets.

    Parameters:
    predictions (np.array): Predicted values.
    targets (np.array): Target values.

    Returns:
    float: NRMSE value.
    """
    assert len(predictions) == len(targets), "Predictions and targets must have the same length."
    weights = 1 if weights is None else weights

    mse = np.nanmean(weights*(predictions - targets) ** 2)
    nrmse_value = np.sqrt(mse) / (np.nanmax(targets) - np.nanmin(targets))

    return nrmse_value


def get_field_stability(ds: xr.Dataset, var_name: str, depth_level: Optional[int] = 0,
                        window: Optional[int] = 11,
                        time_dim: Optional[str] = "time",
                        min_stable_fraction: Optional[float] = 0.2) -> float:
    """
    Calculate the stability level of a field in a dataset.

    Parameters:
    ds (xr.Dataset): Input dataset containing the variable
    var_name (str): Name of the variable to analyze
    depth_level (int): Depth level index to select (default: 0)
    window (int): Rolling window size (default: 10)
    time_dim (str): Name of the time dimension (default: "time")
    min_stable_fraction (float): Minimum fraction of total time that must be stable (default: 0.2)

    Returns:
    float: Stability threshold (0.005-1.0), where lower values indicate higher stability
    """
    # Ensure odd window size for symmetric rolling window
    window = window + 1 if window % 2 == 0 else window

    # Calculate rolling variance
    data = ds[var_name].isel(z_t=depth_level).mean(dim=("lat_t", "lon_t"))
    data_variance = data.rolling({time_dim: window}, center=True).var()

    # Remove NaN values at the beginning and end due to rolling window
    half_window = window // 2
    valid_slice = slice(half_window, -half_window if half_window > 0 else None)
    data_variance_clean = data_variance[valid_slice]

    # Calculate stability level
    threshold = np.arange(0.001, 1.0, 0.001)
    max_variance = np.nanmax(data_variance_clean)

    if max_variance == 0 or np.isnan(max_variance):
        return 1.0

    relative_variance = data_variance_clean / max_variance
    valid_mask = ~np.isnan(relative_variance)
    no_nan_variance = relative_variance[valid_mask]

    if len(no_nan_variance) == 0:
        return 1.0

    total_length = len(no_nan_variance)
    min_stable_length = int(total_length * min_stable_fraction)

    # Find the lowest threshold where there's a point after which all remaining points are below it
    # and the stable period is at least min_stable_fraction of total time 
    for thr in threshold:
        below_threshold = no_nan_variance < thr
        if np.any(below_threshold):
            # Find the first point that goes below threshold
            first_below_idx = np.where(below_threshold)[0][0]
            # Check if all points from that index onwards are below threshold
            stable_length = total_length - first_below_idx
            if (np.all(no_nan_variance[first_below_idx:] < thr) and
                stable_length >= min_stable_length):
                return thr

    return 1.0

def get_config_value(path: Union[str, list[str]], param: str):
    """
    Get the value of a parameter from a configuration file.

    Parameters:
    path (str or list[str]): Path to the configuration file.
    param (str): Parameter name to retrieve.

    Returns:
    str or int or float: Value of the parameter.
    """
    if not isinstance(path, list):
        path = [path]
    for path_item in path:
        with open(path_item, encoding='utf-8') as f:
            for line in f:
                line = line.split('#', 1)[0].strip()

                if line.startswith('[') and line.endswith(']'):
                    continue

                if not line or ("=" not in line and ":" not in line):
                    continue

                symbol = "=" if "=" in line else ":"

                if line.count(symbol) != 1:
                    continue

                key, raw = map(str.strip, line.split(symbol, 1))
                if key == param:
                    v = raw.strip()
                    if v.lower() in ('.true.', 'true'):
                        return True
                    if v.lower() in ('.false.', 'false'):
                        return False
                    if re.fullmatch(r'[+-]?\d+', v):
                        return int(v)
                    if re.fullmatch(r'[+-]?\d*\.?\d*[eE][+-]?\d+', v):
                        return float(v)
                    if re.fullmatch(r'[+-]?\d*\.\d*', v) and '.' in v:
                        return float(v)

                    return v.strip('"').strip("'")

    raise KeyError(f"No parameter named {param!r} in {path!r}")
