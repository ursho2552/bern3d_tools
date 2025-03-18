#!/usr/bin/env python3
# -*- coding: utf-8 -*-
""" Compare two netcdf files for equality. """

import sys
import argparse
import os
import xarray as xr
import numpy as np

def compare_files(file1: str, file2: str ,randvarnum: int,
                  randtimenum: int) -> tuple[str,int]:
    '''
    Compare two netcdf files for equality. The function checks whether the two files contain
    the same variables and whether the variables have the same values at randomly selected
    time steps. The number of variables and time steps to be checked can be specified by the
    user. The function returns a message that indicates whether the files are equal or not,
    and an exit code that can be used to exit the program with sys.exit(exit_code).

    Parameters:
    file1 (str): path to the first file
    file2 (str): path to the second file
    randvarnum (int): number of variables to be checked
    randtimenum (int): number of time steps to be checked

    Returns:
    tuple[str,int]: message indicating whether the files are equal or not, and an exit code
    '''

    ds1 = xr.open_dataset(file1, decode_times=False)
    ds2 = xr.open_dataset(file2, decode_times=False)

    #do inital checks, is dimension 'time' existing, are the same variables
    #saved in the two files, and do their coordinates have the same sizes?
    exit_code = 1

    # Check the time dimension
    if 'time' in ds1.coords:
        time = 'time'
    # Remove redundant check if time is not in ds1.coords
    elif 'TIME' in ds1.coords:
        time = 'TIME'
    else:
        message = f"time or TIME coordinate do not exist, ncequal can't handle this file - exit."
        return message, exit_code

    # Check if the two files contain the same variables
    # no need to use list comprehension here
    if set(ds1.variables) != set(ds2.variables):
        message = "the two files do not contain the same variables - files not equal."
        return message, exit_code

    # Check if the coordinates have the same sizes
    # you can create the dictionay in one line, no need to use zip
    if {cd: ds1[cd].shape for cd in ds1.coords} != {cd: ds2[cd].shape for cd in ds2.coords}:
        message = "the coordinates within the two files have different sizes - files not equal."
        return message, exit_code

    #create list that contains data variables that could be checked
    # - add all variables that are not dimensions or coordinates, and depend on time dimension.
    # use data_vars to only get the data variables and safe the additional checks
    varlist = [var for var in ds1.data_vars if time in ds1[var].coords]

    #draw random fields and times: (draw at most as many fields and times as exist in files)
    randvarnum = min(randvarnum, len(varlist))
    randtimenum = min(randtimenum, ds1[time].shape[0])

    # use random choice to recreate the possibility of choosing the same variable multiple times,
    # but remove list comprehension for readability
    randvars = np.random.choice(np.array(varlist), size=randvarnum, replace=True)
    randtimes = np.random.choice(range(ds1[time].shape[0]), size=randtimenum, replace=True)

    #for every variable, check whether all matrix entries for all selected time steps are
    #equal. Since nan == nan always avaluates to false, nans are set to zero.
    #then count the number of different variables.
    # use xarray equals method to compare the data arrays, which takes care of the nans
    ndifferences = 0
    for var in randvars:
        # add the result directly to ndifferences, no need to use if
        ndifferences += not ds1[var].isel({time: randtimes}).equals(ds2[var].isel({time: randtimes}))

    if ndifferences == 0:
        exit_code = 0
        message = f"{file1} and {file2} are equal in variables {', '.join(randvars)} at time steps {', '.join(map(str, randtimes))}."

    else:
        message = (
            f"{file1} and {file2} contain at least {ndifferences} data variables with different values - files not equal.\n"
            f"(picked variables {', '.join(randvars)} at time steps {', '.join(map(str, randtimes))})."
            )

    return message, exit_code

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='check files for equality')
    parser.add_argument('file1', metavar='file_1', type=str,
                                            help='first file')
    parser.add_argument('file2', metavar='file_2', type=str,
                                            help='second file to be compared to first file')
    parser.add_argument('--variable_number',
                        dest='randvarnum',default=3,type=int,
                        help='specify the number of variables to check, default is 3')
    parser.add_argument('--time_step_number',
                        dest='randtimenum',default=3,type=int,
                        help='specify the number of time steps to check, default is 3')

    args = parser.parse_args()
    FILE1 = args.file1
    FILE2 = args.file2
    RANDVARNUM = args.randvarnum
    RANDTIMENUM = args.randtimenum

    # if the files exists, execute compare files, if not raise error.
    if os.path.exists(FILE1) and os.path.exists(FILE2):
        out = compare_files(FILE1, FILE2, RANDVARNUM, RANDTIMENUM)
        print(out[0])
        sys.exit(out[1])
    else:
        print("files not found.")
        sys.exit(1)
