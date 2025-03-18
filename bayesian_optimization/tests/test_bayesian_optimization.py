#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unittests for functions in the analysis module.
"""
import unittest
import os
import sys

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import bayesian_optimization as bo
import numpy as np

class TestBayesianOptimization(unittest.TestCase):

    def test_find_nearest_with_list(self):
        array = [1, 2, 3, 4, 5]
        value = 3.2
        expected_index = 2
        result = bo.find_nearest(array, value)
        self.assertTrue(result == expected_index)

    def test_find_nearest_with_numpy(self):
        array = np.array([1, 2, 3, 4, 5])
        value = 3.2
        expected_index = 2
        result = bo.find_nearest(array, value)
        self.assertTrue(result == expected_index)

    def test_find_nearest_value(self):
        array = np.array([1, 2, 3, 4, 5])
        value = 3.2
        retval = 0
        expected_value = 3
        result = bo.find_nearest(array, value, retval)
        self.assertTrue(result == expected_value)

    def test_find_nearest_both(self):
        array = np.array([1, 2, 3, 4, 5])
        value = 3.2
        retval = 2
        expected_index = 2
        expected_value = 3
        result, result_index = bo.find_nearest(array, value, retval)
        self.assertTrue((result == expected_value)*(result_index == expected_index))

if __name__ == "__main__":
    unittest.main()