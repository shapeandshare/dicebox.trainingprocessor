# Training Processor

A back-end service for picking up a training request, and performing the training.

Overview
--------

The processor monitors a training request queue, once a request is picked up the service requests training and test data from the sensory service.  It fits the model and stores the weights off for later consumption.


High Level Components
---------------------

![Training Processor Diagram](https://github.com/shapeandshare/dicebox.trainingprocessor/raw/master/assets/Training%20Processor%20Diagram.png)


Production Deployment
---------------------

**Docker Container**

The recommended way to run the service is by using the official provided docker container.  The container is published to Docker Hub [here](https://hub.docker.com/r/shapeandshare/dicebox.trainingprocessor/).

The container should be deployed to a Docker Swarm as a service, or as a stand-alone container within a Docker Engine.



**Example**

```
docker service create \
--detach=false \
--replicas 1 \
--log-driver json-file \
--mount type=volume,volume-driver=cloudstor:aws,source=dicebox,destination=/dicebox \
--env SENSORY_SERVER='sensory.yourdomain.com' \
--env TRAINING_PROCESSOR_SERVICE_RABBITMQ_SERVER='rabbitmq.yourdomain.com' \
--env TRAINING_PROCESSOR_SERVICE_RABBITMQ_USERNAME='USERNAME' \
--env TRAINING_PROCESSOR_SERVICE_RABBITMQ_PASSWORD='PASSWORD' \
--env API_ACCESS_KEY='YOUR_API_ACCESS_KEY' \
--env LOAD_BEST_WEIGHTS_ON_START=True \
--env MODEL_WEIGHTS_FILENAME='PREVIOUS_TRAINING_GUID.hdf5' \
--name trainingprocessor shapeandshare/dicebox.trainingprocessor
```


How to apply rolling updates of the service within the swarm:

```
docker service update --image shapeandshare/dicebox.trainingprocessor:latest trainingprocessor
```

In the examples above the Docker Swarm was deployed to AWS and had the Cloudstor:aws plugin enabled and active.
The training service containers will store and read weights from the shared storage.

**Global shared Cloudstor volumes mounted by all tasks in a swarm service.**

The below command is an example of how to create the shared volume within the docker swarm:
```
docker volume create -d "cloudstor:aws" --opt backing=shared dicebox
```

Contributing
------------
1. Fork the [repository](https://github.com/shapeandshare/dicebox.trainingprocessor) on Github
2. Create a named feature branch (like `add_component_x`)
3. Write your change
4. Write tests for your change (if applicable)
5. Run the tests, ensuring they all pass
6. Submit a Pull Request using Github

License and Authors
-------------------
MIT License

Copyright (c) 2017 Joshua C. Burt

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.