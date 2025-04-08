#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This file initializes the `bern3d_spinup` module.
"""

import argparse
import spinup.utils as sp

def main(configuration_file: str) -> None:

    # Load the configuration file
    my_config = sp.read_config_file(configuration_file, sp.JobConfig)

    for spinup_phase in range(my_config.current_phase, my_config.spinup_phases + 1):

        # Load the configuration of the spinup phase
        if spinup_phase == 1:
            spinup_config_file = my_config.spinup_config_files_phase1
            spinup_executable_template = my_config.sbatch_script_phase1

        elif spinup_phase == 2:
            spinup_config_file = my_config.spinup_config_files_phase2
            spinup_executable_template = my_config.sbatch_script_phase2

        else:
            spinup_config_file = my_config.spinup_config_files_phase3
            spinup_executable_template = my_config.sbatch_script_phase3

        spinup_config = sp.read_config_file(spinup_config_file, sp.ConfigMainParameters)

        # Create a new directory for the spinup phase
        run_directory = sp.create_spinup_run_directory(my_config.bern3d_template,
                                                       my_config.bern3d_executable_name,
                                                       my_config.work_directory,
                                                       spinup_phase)

        # Change the main parameter file
        main_param_file = f"{run_directory}/Spinup{spinup_phase}.main.parameter"
        sp.save_config_as_assignment(spinup_config, main_param_file)

        # Start the simulation with potential dependencies
        dependency = None
        if spinup_phase > my_config.current_phase:
            dependency = [model_job_id]

        spinup_executable = f"Spinup{spinup_phase}"
        model_job_id = sp.submit_job(script_template=spinup_executable_template,
                                        executable_name=spinup_executable,
                                        executable_path=run_directory,
                                        time=my_config.time,
                                        dependency=dependency)


if __name__ == "__main__":

    # Example usage:
    # # python main.py --config_file /storage/homefs/uh24x373/bgc_bern/bern3d_tools/bern3d_spinup/config_files/spinup_setup.yaml
    parser = argparse.ArgumentParser(description="Run the model spinup.")
    parser.add_argument("--config_file", required=True, type=str,
                        help='Path to the configuration file')
    args = parser.parse_args()

    main(args.config_file)
