"""
This module contains the changes to the main parameter file for the spinup phases.
It is used to set up the spinup phases for the Bern3D model in sequence, i.e., it changes the
default values (all boolean are set to False, all integers are set to 0, and all floats are set to
0.0) and then changes the values for the spinup phase in sequence.
"""

override_dictionary = {
    "phase_1": {
        'ndtyear': 144,
        'runYears': 6000,
        'npstp_years': 10,
        'iwstp_years': 10,
        'itstp_years': 1,
        't00': 1765,
        'lin_name': "Spinup1.00001765",
        'lin_nr': 0,
        'lin_continue': False,
        'rundesc': "Spinup Phase 1",
        'atmTSres': True
    },
    "phase_2": {
        'lin_nr': -1,
        'rundesc': "Spinup Phase 2",
        'atmTSres': False,
        'atm_init': True,
        'atmConstInsol': True
    },
    "phase_3": {
        'rundesc': "Spinup Phase 3",
        'lin_name': "Spinup2.00001765",
        'diag_atmtemp_opt': True,
        'atmCTRLpert': True,
        'bgc_init_opt': True,
        'bgc_spinup_opt': True,
        'bgc_dynP_opt': True,
        'bgc_NPZD_opt': True,
        'bgc_oNO3_opt': True,
        'bgc_land_opt': True,
        'bgc_gasEx_opt': True,
        'bgc_virtFl_opt': True
    }
}
