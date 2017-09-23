#!flask/bin/python
import lib.docker_config as config
from lib import sensory_interface
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
from lib.network import Network
import json



# https://stackoverflow.com/questions/273192/how-can-i-create-a-directory-if-it-does-not-exist
def make_sure_path_exists(path):
    try:
        if os.path.exists(path) is False:
            os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise


# Setup logging.
make_sure_path_exists(config.LOGS_DIR)
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%m/%d/%Y %I:%M:%S %p',
    level=logging.DEBUG,
    filemode='w',
    filename="%s/trainingprocessor.%s.log" % (config.LOGS_DIR, os.uname()[1])
)



url = config.TRAINING_PROCESSOR_SERVICE_RABBITMQ_URL
logging.debug('-'*80)
logging.debug("rabbitmq url: (%s)" % url)
logging.debug('-'*80)

parameters = pika.URLParameters(url)
parameters.heartbeat = 0 # turn this off for now, the timeout otherwise
connection = pika.BlockingConnection(parameters=parameters)
channel = connection.channel()

channel.queue_declare(queue=config.TRAINING_PROCESSOR_SERVICE_RABBITMQ_TRAIN_REQUEST_TASK_QUEUE, durable=True)


def train_request():
    training_request_id = uuid.uuid4()

    try:
        ## Submit our message
        url = config.TRAINING_SERVICE_RABBITMQ_URL
        logging.debug(url)
        parameters = pika.URLParameters(url)
        connection = pika.BlockingConnection(parameters=parameters)

        channel = connection.channel()

        channel.queue_declare(queue=config.TRAINING_SERVICE_RABBITMQ_TRAIN_REQUEST_TASK_QUEUE, durable=True)

        training_request = {}
        training_request['training_request_id'] = str(training_request_id)
        channel.basic_publish(exchange=config.TRAINING_SERVICE_RABBITMQ_EXCHANGE,
                              routing_key=config.TRAINING_SERVICE_RABBITMQ_TRAINING_REQUEST_ROUTING_KEY,
                              body=json.dumps(training_request),
                              properties=pika.BasicProperties(
                                  delivery_mode=2,  # make message persistent
                              ))
        logging.debug(" [x] Sent %r" % json.dumps(training_request))
        connection.close()
    except:
        # something went wrong..
        logging.error('we had a failure sending the request to the message system')
        return None

    return training_request_id


def train_call(training_request_id):
    logging.debug('-' * 80)
    logging.debug("processing training request id: (%s)" % training_request_id)
    logging.debug('-' * 80)
    network = Network(config.NN_PARAM_CHOICES)
    if config.LOAD_BEST_WEIGHTS_ON_START is True:
        logging.debug('-' * 80)
        logging.debug('attempting to restart training from previous session..')
        logging.debug('-' * 80)
        network.create_lonestar(create_model=True,
                                weights_filename="%s/%s" % (config.WEIGHTS_DIR, config.MODEL_WEIGHTS_FILENAME))
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

    logging.debug('-' * 80)
    logging.debug('loading category map')
    logging.debug('-' * 80)
    with open('./category_map.json', 'w') as category_mapping_file:
        category_mapping_file.write(json.dumps(network.fsc.CATEGORY_MAP))

    i = 1
    while i <= config.EPOCHS:
        logging.debug('-' * 80)
        logging.debug("epoch (%i of %i)" % (i, config.EPOCHS))
        logging.debug('-' * 80)
        network.train_and_save(config.DATASET)

        # save the model after every epoch, regardless of accuracy.
        #path = "%s/%s/" % (config.WEIGHTS_DIR, training_request_id)
        #make_sure_path_exists(path)
        #filename = "weights.epoch_%i.final.%s.hdf5" % (i, datetime.now().strftime('%Y-%m-%d_%H_%M_%S_%f'))

        #full_path = "%s%s" % (path, filename)
        #logging.debug("saving model weights after epoch %i to file %s" % (i, full_path))
        #network.save_model(filename)

        make_sure_path_exists(config.WEIGHTS_DIR)
        logging.debug('-' * 80)
        full_path = "%s/%s.hdf5" % (config.WEIGHTS_DIR, training_request_id)
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

logging.debug('-'*80)
print(' [*] Waiting for messages. To exit press CTRL+C')
logging.debug('-'*80)

def callback(ch, method, properties, body):
    logging.debug('-' * 80)
    logging.debug(" [x] Received %r" % body)
    logging.debug('-' * 80)
    ch.basic_ack(delivery_tag=method.delivery_tag)
    train_call(json.loads(body)['training_request_id'])
    logging.debug('-' * 80)
    logging.debug(" [x] Done")
    logging.debug('-'*80)

channel.basic_qos(prefetch_count=1)
channel.basic_consume(callback,
                      queue=config.TRAINING_PROCESSOR_SERVICE_RABBITMQ_TRAIN_REQUEST_TASK_QUEUE)

channel.start_consuming()