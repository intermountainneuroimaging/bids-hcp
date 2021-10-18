"""
This module elevates "safe_listed" files to the toplevel of this gear's output
directory.  This is as specified in
https://github.com/scitran-apps/freesurfer-recon-all/blob/master/bin/run#L206-L317.
However, what is requested in the volume and area information of the FS output
rather than the registered and segmented volumes and surfaces (L296-L317).
part of the hcp-struct gear
"""
import logging
import os.path as op

import pandas as pd
from flywheel_gear_toolkit.interfaces.command_line import exec_command

log = logging.getLogger(__name__)


def set_params(gear_args):
    gear_args.structural["metadata"] = {}


def set_metadata_from_csv(gear_args, csv_file):
    """
    Once the aseg_stats are available in a table format, the metadata
    can be updated with values for various ROIs.
    Args:
        gear_args (GearArgs): Custom class containing relevant gear and analysis set up parameters
        csv_file: aseg stats converted by asegstats2table from FreeSurfer

    Returns:
        updated metadata on the analysis container.
    """
    info = gear_args.structural["metadata"]["analysis"]["info"]
    if op.exists(csv_file):
        df = pd.read_csv(csv_file, sep=",")
        columns = df.columns
        # First column is the name of the csv
        # To avoid name collisions, organize these by seg_title
        seg_title = columns[0].replace(".", "_")
        info[seg_title] = {}
        # All but the first column which is subject_id
        for col in columns[1:]:
            info[seg_title][col] = df[col][0]


def process_aseg_csv(gear_args):
    """
    Convert the statistical output files from FreeSurfer into tables that can be read
    into other packages or metadata.
    Args:
        gear_args (GearArgs): Custom class containing relevant gear and analysis set up parameters
    """
    safe_list = gear_args.common["safe_list"]
    # Check for the presence of keys.
    metadata = gear_args.structural["metadata"]
    if "analysis" not in metadata.keys():
        metadata["analysis"] = {}

    if "info" not in metadata["analysis"].keys():
        metadata["analysis"]["info"] = {}

    tablefile = op.join(
        gear_args.dirs["bids_dir"],
        gear_args.common["subject"] + "_aseg_stats_vol_mm3.csv",
    )
    command = [
        "python2",
        op.join(gear_args.environ["FREESURFER_HOME"], "bin", "asegstats2table"),
        "-s",
        gear_args.common["subject"],
        "--delimiter",
        "comma",
        "--tablefile=" + tablefile,
    ]

    try:
        exec_command(command, environ=gear_args.environ)
    except Exception as e:
        log.exception(e)
    safe_list.append(tablefile)
    set_metadata_from_csv(gear_args, tablefile)

    for hemi in ["lh", "rh"]:
        for parc in ["aparc.a2009s", "aparc"]:
            tablefile = op.join(
                gear_args.dirs["bids_dir"],
                "{}_{}_{}_stats_area_mm2.csv".format(
                    gear_args.common["subject"], hemi, parc
                ),
            )
            command = [
                "python2",
                op.join(
                    gear_args.environ["FREESURFER_HOME"], "bin", "aparcstats2table"
                ),
                "-s",
                gear_args.common["subject"],
                "--hemi=" + hemi,
                "--delimiter=comma",
                "--parc=" + parc,
                "--tablefile=" + tablefile,
            ]
            exec_command(command, environ=gear_args.environ)
            safe_list.append(tablefile)
            set_metadata_from_csv(gear_args, tablefile)


def execute(gear_args):
    """
    Link the FreeSurfer SUBJECTS_DIR with the current subject being analyzed
    and convert the accompanying statistical files into other formats to be
    zipped or translated onto analysis containers.
    """
    subject = gear_args.common["subject"]
    # The commands below only work with this
    # symbolic link in place b/c of the SUBJECTS_DIR arg in asegstats2table
    command = [
        "ln",
        "-s",
        "-f",
        "{}/{}/T1w/{}".format(gear_args.dirs["bids_dir"], subject, subject),
        "/opt/freesurfer/subjects/",
    ]
    exec_command(
        command,
        dry_run=gear_args.fw_specific["gear_dry_run"],
        environ=gear_args.environ,
    )

    # Process segmentation data to csv and process to metadata
    if gear_args.fw_specific["gear_dry_run"] is False:
        log.info("Exporting stats files csv...")
        process_aseg_csv(gear_args)
