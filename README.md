# tag2influx.py
Simple Python 3 script to copy data from Wireless Tags API to your own InfluxDB

# Usage
## Configuration
Change the mostly self-explanatory settings in the `tag2influx.conf` file. You can use the influx `schema` settings to change measurement name and what field names are used for tag stats (`stat_map`). Stat name is used if no mapping exists.

## Running
By default the script will fetch data for the last 30 minutes, this can be changed with the `--last N` parameter.

Other parameters can be seen with `--help`.

Running the script multiple times with overlapping time ranges should be fine, influxdb will not add duplicate data points for the same timestamp. So you can run the script every 15 minutes from cron and the default 30 minute fetch range should make sure you don't miss any data.

In case of API outages or otherwise missed syncs, you can easily backfill any missing data by running the script once with a larger `--last N` value or even multiple days at a time with the `--fromdate` option.

# Known issues
- ~~Supports only temperature data for now~~
- Does not support authentication for InfluxDB
