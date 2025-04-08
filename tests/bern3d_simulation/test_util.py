"""
This file defines the test cases for the simulation module using the unittest framework.
"""
import tempfile
import unittest
from pathlib import Path
import yaml
from unittest.mock import patch, MagicMock

from bern3d_simulation.simulation.utils import (
    read_config_file,
    create_simulation_run_directory,
    copy_template_directory,
    create_results_directory,
    replace_placeholders_in_files,
    rename_files,
    check_simulation_status,
    submit_job,
    JobConfig,
)

class TestUtilities(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory that should be cleaned automatically.
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.base_path = Path(self.temp_dir.name)

    def test_read_config_file_valid(self):
        """
        Test that a valid YAML configuration file is properly read into a JobConfig.
        """

        config_data = {
            "bern3d_template": "template_path",
            "bern3d_executable_name": "executable",
            "work_directory": str(self.base_path / "work"),
            "simulation_name": "test_simulation",
            "bern3d_submit_script": "submit.sh",
            "python_script": "python.py",
            "main_script": "main.py",
            "time_bern3d": "00:10:00",
            "time_python": "00:05:00",
            "config_file": "config.yaml"
        }

        config_file_path = self.base_path / "config.yaml"
        with config_file_path.open('w', encoding='utf-8') as f:
            yaml.dump(config_data, f)

        config = read_config_file(str(config_file_path), JobConfig)
        self.assertIsInstance(config, JobConfig)
        self.assertEqual(config.simulation_name, "test_simulation")

    def test_read_config_file_invalid_extension(self):
        """
        Test that passing a non-YAML filename raises an assertion error.
        """

        with self.assertRaises(AssertionError):
            read_config_file("config.txt", JobConfig)

    def test_copy_template_directory(self):
        """
        Test that a template directory is copied with its content intact.
        """

        src_dir = self.base_path / "src_template"
        src_dir.mkdir()
        file_path = src_dir / "test.txt"
        file_path.write_text("sample content")

        dest_dir = self.base_path / "dest_template"
        copy_template_directory(str(src_dir), dest_dir)
        self.assertTrue(dest_dir.exists())
        self.assertTrue((dest_dir / "test.txt").exists())

    def test_create_results_directory(self):
        """
        Test that the 'results' directory is created inside the work directory.
        """

        work_dir = self.base_path / "workdir"
        work_dir.mkdir()
        create_results_directory(str(work_dir))
        results_dir = work_dir / "results"
        self.assertTrue(results_dir.exists())
        self.assertTrue(results_dir.is_dir())

    def test_replace_placeholders_in_files(self):
        """
        Test that placeholders in files within a directory are correctly replaced.
        """

        temp_sim_dir = self.base_path / "sim_run"
        temp_sim_dir.mkdir()

        # Use the same file names as in the original code, and write dummy content.
        files = ["parallel.sh", "parallel_investor.sh", "OLDNAME.main.parameter"]
        for fname in files:
            fpath = temp_sim_dir / fname
            fpath.write_text("This file contains OLDNAME")

        replace_placeholders_in_files(temp_sim_dir, "OLDNAME", "NEWNAME")
        for fname in files:
            fpath = temp_sim_dir / fname
            content = fpath.read_text()
            self.assertNotIn("OLDNAME", content)
            self.assertIn("NEWNAME", content)

    def test_rename_files(self):
        """
        Test that files starting with the old name are properly renamed.
        """

        temp_dir = self.base_path / "rename_test"
        temp_dir.mkdir()
        old_file = temp_dir / "OLDNAME_file.txt"
        old_file.write_text("dummy")

        rename_files(temp_dir, "OLDNAME", "NEWNAME")
        new_file = temp_dir / "NEWNAME_file.txt"
        self.assertFalse(old_file.exists())
        self.assertTrue(new_file.exists())

    def test_check_simulation_status(self):
        """
        Test that check_simulation_status correctly detects the success string.
        """

        run_dir = self.base_path / "run_dir"
        run_dir.mkdir()
        output_file = run_dir / "executable.out"

        # Write a file that indicates the simulation completed successfully.
        output_file.write_text("Some log info... SIMULATION COMPLETE more info")
        status = check_simulation_status(str(run_dir), "executable")
        self.assertTrue(status)

        # Overwrite file with content that does not include the success string.
        output_file.write_text("Some log info... incomplete simulation")
        status = check_simulation_status(str(run_dir), "executable")
        self.assertFalse(status)

        # Test for a missing file -- an assertion should be raised.
        non_existing_dir = self.base_path / "non_existing"
        non_existing_dir.mkdir()
        with self.assertRaises(AssertionError):
            check_simulation_status(str(non_existing_dir), "executable")

    @patch("subprocess.run")
    def test_submit_job(self, mock_run):
        """
        Test that submit_job builds the correct command and returns the job ID.
        """

        process_mock = MagicMock()
        process_mock.stdout = "Submitted batch job 12345"
        mock_run.return_value = process_mock

        job_id = submit_job(
            script_template="script.sh",
            executable_name="my_executable",
            executable_path="/path/to/executable",
            time="00:30:00",
            dependency=["111", "222"],
            command_line_arg=["--arg1", "value1"]
        )

        # Verify that the command includes expected arguments.
        args_passed = mock_run.call_args[0][0]
        self.assertIn("--job-name=my_executable", args_passed)
        self.assertIn("--time=00:30:00", args_passed)
        self.assertIn("--chdir=/path/to/executable", args_passed)
        self.assertIn("--dependency=afterok:111:222", args_passed)
        self.assertIn("script.sh", args_passed)
        self.assertIn("--arg1", args_passed)
        self.assertIn("value1", args_passed)
        self.assertEqual(job_id, "12345")

    def test_create_simulation_run_directory(self):
        """
        Integration test for creating a simulation directory using a template.
        """
        # Set up a fake template directory with files that require placeholder replacement and renaming.
        template_dir = self.base_path / "template"
        template_dir.mkdir()
        file_names = [
            "parallel.sh",
            "parallel_investor.sh",
            "OLDNAME.main.parameter"
        ]
        for fname in file_names:
            fpath = template_dir / fname
            fpath.write_text(f"This is {fname} containing OLDNAME")

        work_dir = self.base_path / "work"
        work_dir.mkdir()
        sim_run_path = create_simulation_run_directory(
            bern3d_template_path=str(template_dir),
            bern3d_template_name="OLDNAME",
            work_directory=str(work_dir),
            new_name="NEWNAME"
        )

        # Verify that the new simulation directory was created.
        self.assertTrue(Path(sim_run_path).exists())
        # Check that the results directory exists in the work directory.
        self.assertTrue((work_dir / "results").exists())

        # Expected files should now have "NEWNAME" in place of "OLDNAME".
        expected_files = [
            "parallel.sh",
            "parallel_investor.sh",
            "NEWNAME.main.parameter"
        ]
        for fname in expected_files:
            file_path = Path(sim_run_path) / fname
            self.assertTrue(file_path.exists())
            content = file_path.read_text()
            self.assertNotIn("OLDNAME", content)
            self.assertIn("NEWNAME", content)

if __name__ == '__main__':
    # Usage example:
    # python -m unittest tests/bern3d_simulation/test_util.py

    unittest.main()
