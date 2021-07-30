import json
import logging
import os.path as op
import pprint
import subprocess as sp

log = logging.getLogger(__name__)


def validate_bids(gtk_context):
    """Run BIDS Validator on bids_dir
    Install BIDS Validator into container with:
        RUN npm install -g bids-validator
    This prints a summary of files that are valid,
    and then lists errors and warnings.
    Then it exits if gear-abort-on-bids-error is set and
    if there are any errors.
    The config MUST contain both of these:
        gear-run-bids-validation
        gear-abort-on-bids-error
    """
    try:
        # Call the essences of bids-client's utils.validate_bids, but with stdout
        # and not needing to install bids-client
        bids_dir = op.join(gtk_context.work_dir, "bids")
        # Update to python based bids_validator solution.
        # command = [
        #     "bids-validator",
        #     "--verbose",
        #     "--json",
        #     bids_dir,
        # ]
        # log.info(" Command:" + " ".join(command))
        # result = sp.run(
        #     command, stdout=sp.PIPE, stderr=sp.PIPE, universal_newlines=True
        # )
        # log.info(" {} return code: ".format(command) + str(result.returncode))
        # bids_output = json.loads(result.stdout)
        # log.debug(f"BIDS validator error: {result.stderr}")

        # show summary of valid BIDS stuff
        log.info(
            " bids-validator results:\n\nValid BIDS files summary:\n"
            + pprint.pformat(bids_output["summary"], indent=8)
            + "\n"
        )

        num_bids_errors = len(bids_output["issues"]["errors"])
        if num_bids_errors > 0:
            log.error("BIDS validation errors were found.")
            for err in bids_output["issues"]["errors"]:
                log.error("%s: %s", err["key"], err["reason"])
            raise Exception(
                " {} BIDS validation errors ".format(num_bids_errors)
                + "were detected: NOT running command."
            )

        # show all warnings
        for warn in bids_output["issues"]["warnings"]:
            warn_msg = warn["reason"] + "\n"
            for ff in warn["files"]:
                if ff["file"]:
                    warn_msg += "       {}\n".format(ff["file"]["relativePath"])
            log.warning(" " + warn_msg)

        # NOTE: C-PAC runs its own bids validator that does
        # not report until the end of cpac execution
    except Exception as e:
        log.fatal(
            "Cannot download and validate bids.",
        )
        log.exception(e)
        if gtk_context.config["gear-abort-on-bids-error"]:
            return 1
            # There is no cleanup after this errors out or not.
            # We exit the program. Without validated bids, we
            # cannot proceed.