import logging
import os
import shutil
import tempfile
from glob import glob
from pathlib import Path

log = logging.getLogger(__name__)

# Set the typical home directory for the gear, if running in Docker
FWV0 = "/flywheel/v0"
# Set a subdirectory name for the gear directories/files that will
# be linked from FLYWHEEL to /tmp. /tmp is auto-mounted by Singularity,
# so adding another layer of organization below /tmp will allow one to
# search for Flywheel-created files/dirs to remove, zip, use, etc. easily.
gear_temp_dir = "gear-temp-dir-"


def check_for_singularity():
    """Determine if Singularity is enabled on the system and log it."""
    if "SINGULARITY_NAME" in os.environ:
        return True
    else:
        return False


def start_singularity(gear_name: str, writable_dir: os.PathLike, debug: bool):
    """
    Set up the environment for a clean Singularity run.
    Args:
        writable_dir (string): directory to use for temporary files if /flywheel/v0 is not
            writable.
    """
    if debug:
        log_singularity_details()

    # Favor containing the gear in normal gear locations
    use_wrtbl_dir = check_writable_dirs(FWV0)
    if not use_wrtbl_dir:
        use_wrtbl_dir = check_writable_dirs(writable_dir)
    writable_dir = use_wrtbl_dir
    # Use the writable directory to set up the rest of the env
    remove_previous_runs(gear_name, writable_dir)
    mount_gear_home_to_tmp(gear_name, writable_dir)
    return writable_dir


def check_writable_dirs(writable_dir: os.PathLike):
    locs = glob("/flywheel/v0/*")
    prmsns = []
    for loc in locs:
        prmsns.append(os.access(loc, os.W_OK))
    if all(prmsns):
        return writable_dir
    else:
        log.info(f"{writable_dir} is not writable in this environment.")
        return none


def log_singularity_details():
    """Help debug Singularity settings, including permissions and UID."""
    log.info(f"SINGULARITY_NAME is {os.environ['SINGULARITY_NAME']}")
    log.debug(f"UID is {os.getuid()}")
    log.debug("Permissions: 4=read, 2=write, 1=read")
    alt_locs = glob("/home/bidsapp")
    for loc in alt_locs:
        for prmsn in [os.R_OK, os.W_OK, os.X_OK]:
            log.debug(f"Permission {prmsn} for {loc}: {os.access(loc,prmsn)}")
        if ("gear_environ" in loc) and not os.access(loc, os.R_OK):
            log.error(
                "Cannot read gear_environ.json. Gear will download BIDS in the wrong spot and will not wrap up properly."
            )


def mount_gear_home_to_tmp(gear_name, writable_dir):
    """
    - Singularity auto-mounts /tmp and /var/tmp.
    - The Docker run.py script is initialized after creation of the
    Singularity container.
    - Therefore, there is no opportunity to mount /flywheel/v0 data
    or structure directly to Singularity.
    The resulting necessity is to use this method to create a
    subfolder inside the automounted /tmp directory that will
    contain the files Docker is instructed to use to run the gear.
    """
    # Create temporary place to run gear
    work_dir = tempfile.mkdtemp(prefix=gear_temp_dir + gear_name, dir=writable_dir)
    new_FWV0 = Path(work_dir + FWV0)
    new_FWV0.mkdir(parents=True)
    abs_path = Path(".").resolve()
    fw_paths = list(Path(FWV0).glob("*"))

    for fw_name in fw_paths:
        if fw_name.name == "gear_environ.json":  # always use real one, not dev
            (new_FWV0 / fw_name.name).symlink_to(Path(FWV0) / fw_name.name)
        else:
            (new_FWV0 / fw_name.name).symlink_to(abs_path / fw_name.name)
    os.chdir(new_FWV0)
    return new_FWV0


def remove_previous_runs(gear_name, writable_dir="/var/tmp"):
    """remove any previous runs (possibly left over from previous testing)"""
    previous_runs = glob(os.path.join(writable_dir, gear_temp_dir + gear_name + "*"))
    if previous_runs:
        log.debug("previous_runs = %s", previous_runs)
        for prev in previous_runs:
            log.debug("rm %s", prev)
            shutil.rmtree(prev)
    else:
        log.debug(f"No previous runs to worry about.")


def unlink_gear_mounts(gear_name_for_singularity):
    """
    Clean up the shared environment, since pieces (like FreeSurfer) may have
    left remnants in /tmp/flywheel/v0.
    """
    tmp_fw_dir = os.path.join("/tmp", gear_temp_dir + gear_name_for_singularity + "*")
    if tmp_fw_dir:
        for item in glob(tmp_fw_dir, recursive=True):
            if os.path.islink(item):
                os.unlink(item)  # don't remove anything links point to
                log.debug("unlinked {item}")
        shutil.rmtree(tmp_fw_dir)
        log.debug(f"Removed {tmp_fw_dir}")
