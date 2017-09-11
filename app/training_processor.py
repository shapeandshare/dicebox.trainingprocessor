#!flask/bin/python
from lib import dicebox_config as config
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
#import logging
#import lib.dicebox_config as config
from lib.network import Network
#from datetime import datetime
import json


# Setup logging.
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%m/%d/%Y %I:%M:%S %p',
    level=logging.DEBUG,
    filemode='w',
    filename="%s/training_processor.log" % config.LOGS_DIR
)


url = config.TRAINING_PROCESSOR_SERVICE_RABBITMQ_URL
parameters = pika.URLParameters(url)
parameters.heartbeat = 0 # turn this off for now, the timeout otherwise
connection = pika.BlockingConnection(parameters=parameters)
channel = connection.channel()

channel.queue_declare(queue=config.TRAINING_PROCESSOR_SERVICE_RABBITMQ_TRAIN_REQUEST_TASK_QUEUE, durable=True)


# https://stackoverflow.com/questions/273192/how-can-i-create-a-directory-if-it-does-not-exist
def make_sure_path_exists(path):
    try:
        os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise


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
    logging.debug("processing training request id: (%s)" % training_request_id)
    network = Network(config.NN_PARAM_CHOICES)
    if config.LOAD_BEST_WEIGHTS_ON_START is True:
        logging.info('attempting to restart training from previous session..')
        network.create_lonestar(create_model=True,
                                weights_filename="%s/%s" % (config.WEIGHTS_DIR, config.MODEL_WEIGHTS_FILENAME))
    else:
        network.create_lonestar(create_model=True)

    with open('./category_map.json', 'w') as category_mapping_file:
        category_mapping_file.write(json.dumps(network.fsc.CATEGORY_MAP))

    i = 1
    while i <= config.EPOCHS:
        logging.info("epoch (%i of %i)" % (i, config.EPOCHS))
        network.train_and_save(config.DATASET)

        # save the model after every epoch, regardless of accuracy.
        #path = "%s/%s/" % (config.WEIGHTS_DIR, training_request_id)
        #make_sure_path_exists(path)
        #filename = "weights.epoch_%i.final.%s.hdf5" % (i, datetime.now().strftime('%Y-%m-%d_%H_%M_%S_%f'))

        #full_path = "%s%s" % (path, filename)
        #logging.info("saving model weights after epoch %i to file %s" % (i, full_path))
        #network.save_model(filename)

        make_sure_path_exists(config.WEIGHTS_DIR)
        full_path = "%s/%s.hdf5" % (config.WEIGHTS_DIR, training_request_id)
        logging.info("saving model weights after epoch %i to file %s" % (i, full_path))
        network.save_model(full_path)

        # the next epoch..
        i += 1

    logging.info("network accuracy: %.2f%%" % (network.accuracy * 100))
    logging.info('-'*80)
    network.print_network()

    return None





print(' [*] Waiting for messages. To exit press CTRL+C')

def callback(ch, method, properties, body):
    logging.info(" [x] Received %r" % body)
    ch.basic_ack(delivery_tag=method.delivery_tag)
    train_call(json.loads(body)['training_request_id'])
    logging.info(" [x] Done")

channel.basic_qos(prefetch_count=1)
channel.basic_consume(callback,
                      queue=config.TRAINING_PROCESSOR_SERVICE_RABBITMQ_TRAIN_REQUEST_TASK_QUEUE)

channel.start_consuming()