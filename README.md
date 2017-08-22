# climon

Monitors DHT11 and DHT22 sensors connected to one or several Raspberry Pi(s) and renders graphs on a web interface.

## Installation

Get git, python3 and the correspondong pip:

`$ sudo apt-get install git python3 python3-pip`

Install the DHT library using pip:

`$ pip3 install adafruit_python_dht`

Clone the climon repository:

`$ git clone https://github.com/jwustrack/climon/`

## Configuration

Start with `climon.conf.example` as a base for your configuration by copying/renaming it to `climon.conf`.
Then adapt it to your needs.

There are two different types of sections in the configuration:

### common ###

This⋅section configures global options. You will probably only want to change the port.

```ini
# the database file
database=climon.db

# the port for the web interface
port=8765

# the interval in seconds at which new values are fetched from each sensor
monitor-interval=60
```

### sensor:* ###

There is one configuration section per sensor you want to monitor. The part after the colon is the ID of the sensor. You can chose any ID as long as it's composed of alphanumeric characters and dashes (no spaces or other special characters).
Once you have started fetching values for this sensor, don't change this ID or your data will become inaccessible.
The content of each sensor section will configure the sensor.

#### Sensor connected to the raspberry pi itself ####

```ini
# Sensor with ID "living-room"
[sensor:living-room]

# Name of the sensor (displayed on the web interface)
name=Living room

# Type of sensor (DHT11, DHT22 or climon)
type=DHT22

# Source: For DHT11 or DHT22 this is the PIN number
source=4

# Color of the graph on the web interface
color=#0033ff
```
#### Sensor on a remote climon instance ####

Each sensor will be published on a URL of the form:

`http://<ip>:<port>/sensor/<sensor_id>`

Thanks to this you can monitor its values from another climon instance and display graphs from multiple sensors in and around your house. To use such a remote sensor, use a `climon` sensor type:


```ini
[sensor:garden]
name=Garden

# Get values from a remote climon instance
type=climon

# Url on which sensor data is published by the other climon instance: http://<ip>:<port>/sensor/<sensor_id>
source=http://192.168.1.102:8765/sensor/garden

color=#ff3300
```

## Usage

Once its dependencies are installed and climon.conf is fully configured, you can start the deamon.
```sh
$ climon.sh start
```

And access the web interface:

`http://<ip>:<port>`

Configuration changes will be taken into account only after restarting the deamon:

```sh
$ climon.sh restart
```
You can also stop it:

```sh
$ climon.sh stop
```
For debugging purposes you can start the web UI and monitoring processes individually:

```sh
$ python3 web.py debug
```
or
```sh
$ python3 mon.py debug
```

## Autostart

To run `climon` during the boot process, run:

```sh
sudo ./autostart.sh
```
