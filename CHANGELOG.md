Change Log
==========

03.09.2019
----------
* Added Change Log!
* Update dicebox.core libraries to the latest.
* Updated requirements.txt managed dependencies to the latest.
* Updated copyright dates.
* Added more exclusions to gitignore.
* Code cleanup and comments added.

03.10.2019
----------
* Updated dicebox.core libraries to address keras weights save/load unicode issue.

03.21.2019
----------
* Don't create a Network File System Connector, we don't have a file system, and not need one, or the categories to be stored to disk.

03.22.2019
----------
* Updated Core Libraries
* Moved category map save location from tmp to weights. (if enabled)

03.23.2019
----------
* Updated Core Libraries to address file descriptor leak when polling for queue consumption
* additional gitignore entries added for dev.

03.30.2019
----------
* Updated core libraries and refactored to support the changes

03.31.2019
----------
* Disabled code which cached data to disk for the training processor until the code to pull from cache is also completed.

04.06.2019
----------
* Refactored to support changes in the core libraries namespace.
