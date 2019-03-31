#!flask/bin/python
###############################################################################
# Training Processor
#
# Copyright (c) 2017-2019 Joshua Burt
###############################################################################


###############################################################################
# Dependencies
###############################################################################

from flask import Flask, jsonify, request, make_response, abort
from flask_cors import CORS, cross_origin
import base64
import logging
import json
from datetime import datetime
import os
import errno
import uuid
import numpy
import pika
import json
import dicebox.docker_config
import dicebox.sensory_interface
import dicebox.network

# Config
config_file = './dicebox.config'
CONFIG = dicebox.docker_config.DockerConfig(config_file)


###############################################################################
# Allows for easy directory structure creation
# https://stackoverflow.com/questions/273192/how-can-i-create-a-directory-if-it-does-not-exist
###############################################################################
def make_sure_path_exists(path):
    try:
        if os.path.exists(path) is False:
            os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise


###############################################################################
# Setup logging.
###############################################################################
make_sure_path_exists(CONFIG.LOGS_DIR)
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%m/%d/%Y %I:%M:%S %p',
    level=logging.DEBUG,
    filemode='w',
    filename="%s/trainingprocessor.%s.log" % (CONFIG.LOGS_DIR, os.uname()[1])
)

# https://github.com/pika/pika/issues/692
# reduce log level of pika
logging.getLogger("pika").setLevel(logging.WARNING)

###############################################################################
# Message System Configuration
###############################################################################
url = CONFIG.TRAINING_PROCESSOR_SERVICE_RABBITMQ_URL
logging.debug('-'*80)
logging.debug("rabbitmq url: (%s)" % url)
logging.debug('-'*80)

parameters = pika.URLParameters(url)
parameters.heartbeat = 0 # turn this off for now, the timeout otherwise
connection = pika.BlockingConnection(parameters=parameters)
channel = connection.channel()

channel.queue_declare(queue=CONFIG.TRAINING_PROCESSOR_SERVICE_RABBITMQ_TRAIN_REQUEST_TASK_QUEUE, durable=True)
channel.basic_qos(prefetch_count=0)


###############################################################################
# Training Logic
###############################################################################
def train_call(training_request_id):
    logging.debug('-' * 80)
    logging.debug("processing training request id: (%s)" % training_request_id)
    logging.debug('-' * 80)
    network = dicebox.network.Network(CONFIG.NN_PARAM_CHOICES, True)
    if CONFIG.LOAD_BEST_WEIGHTS_ON_START is True:
        logging.debug('-' * 80)
        logging.debug('attempting to restart training from previous session..')
        logging.debug('-' * 80)
        network.create_lonestar(create_model=True,
                                weights_filename="%s/%s" % (CONFIG.WEIGHTS_DIR, CONFIG.MODEL_WEIGHTS_FILENAME))
        logging.debug('-' * 80)
        logging.debug('Done')
        logging.debug('-' * 80)
    else:
        logging.debug('-' * 80)
        logging.debug('creating model, but NOT loading previous weights.')
        logging.debug('-' * 80)
        network.create_lonestar(create_model=True)
        logging.debug('-' * 80)
        logging.debug('Done')
        logging.debug('-' * 80)

    if network.fsc is not None:
        logging.debug('-' * 80)
        logging.debug('writing category map to %s for later use with the weights.', CONFIG.TMP_DIR)
        logging.debug('-' * 80)
        with open('%s/category_map.json' % CONFIG.WEIGHTS_DIR , 'w') as category_mapping_file:
            category_mapping_file.write(json.dumps(network.fsc.CATEGORY_MAP))

    i = 1
    while i <= CONFIG.EPOCHS:
        logging.debug('-' * 80)
        logging.debug("epoch (%i of %i)" % (i, CONFIG.EPOCHS))
        logging.debug('-' * 80)
        network.train_and_save(CONFIG.DATASET)

        make_sure_path_exists(CONFIG.WEIGHTS_DIR)
        logging.debug('-' * 80)
        full_path = "%s/%s.%.2f.hdf5" % (CONFIG.WEIGHTS_DIR, training_request_id, (network.accuracy * 100))
        logging.debug("saving model weights after epoch %i to file %s" % (i, full_path))
        logging.debug('-' * 80)
        network.save_model(full_path)

        # the next epoch..
        i += 1

    logging.debug('-' * 80)
    logging.debug("network accuracy: %.2f%%" % (network.accuracy * 100))
    logging.debug('-'*80)

    network.print_network()
    logging.debug(network.print_network())
    logging.debug('-' * 80)
    return None


###############################################################################
# Our callback when message consumption is ready to occur
###############################################################################
def callback(ch, method, properties, body):
    logging.debug('-' * 80)
    logging.debug(" [x] Received %r" % body)
    logging.debug('-' * 80)
    ch.basic_ack(delivery_tag=method.delivery_tag)
    train_call(json.loads(body)['training_request_id'])
    logging.debug('-' * 80)
    logging.debug(" [x] Done")
    logging.debug('-'*80)


###############################################################################
# Main wait loop begins now ..
###############################################################################
logging.debug('-'*80)
print(' [*] Waiting for messages. To exit press CTRL+C')
logging.debug('-'*80)
channel.basic_consume(callback,
                      queue=CONFIG.TRAINING_PROCESSOR_SERVICE_RABBITMQ_TRAIN_REQUEST_TASK_QUEUE)
channel.start_consuming()
