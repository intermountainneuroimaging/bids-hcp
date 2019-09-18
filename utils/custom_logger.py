import logging
import sys
import time

def log_config(context):
    config = context.config
    inputs = context._invocation['inputs']
    context.log.info('\n\nThe following inputs were used:')
    for fl in inputs.keys():
        context.log.info(
            '{}: {}'.format(fl,context.get_input_path(fl))
        )
    context.log.info('\n\nThe following configuration were set:')
    for k in config.keys():
        context.log.info(
            '{}: {}'.format(k,context.config[k])
        )
    context.log.info('\n')

def get_custom_logger(log_name):
    # Initialize Custom Logging
    # Timestamps with logging assist debugging algorithms
    # With long execution times
    handler = logging.StreamHandler(stream=sys.stdout)
    formatter = logging.Formatter(
                fmt='%(levelname)s - %(name)-8s - %(asctime)s -  %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S')
    handler.setFormatter(formatter)
    logger = logging.getLogger(log_name)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    return logger