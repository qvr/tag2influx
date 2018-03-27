# tag2influx.py
Simple Python script to copy data from Wireless Tags API to your own InfluxDB

# Usage
## Configuration
Change the mostly self-explanatory settings in the `tag2influx.conf` file

## Running
By default the script will fetch data for the last 30 minutes, this can be changed with the `--last N` parameter.

Other parameters can be seen with `--help`.

Running the script multiple times with overlapping time ranges should be fine, influxdb will not add duplicate data points for the same timestamp.

# Known issues
- Supports only temperature data for now
- Does not support authentication for InfluxDB
