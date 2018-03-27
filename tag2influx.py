#!/usr/bin/env python

import argparse
import requests
import json
from datetime import datetime, timedelta
import pytz
from calendar import timegm
import sys

## settings ##
with open('tag2influx.conf') as json_conf_file:
  conf = json.load(json_conf_file)

wtag_email = conf['wtag']['email']
wtag_password = conf['wtag']['password']
wtag_timezone = conf['wtag']['timezone']
wtag_tag_ids = conf['wtag'].get('tag_ids') or []

influx_write_url = conf['influx']['write_url']
influx_batch_size = conf['influx'].get('batch_size') or 1000

wtag_base_url = conf['wtag'].get('base_url') or "https://www.mytaglist.com"
wtag_signin_url = wtag_base_url + (conf['wtag'].get('signin_url') or "/ethAccount.asmx/SignIn")
wtag_getmultitagstatsraw_url = wtag_base_url + (conf['wtag'].get('getmultitagstatsraw_url') or "/ethLogs.asmx/GetMultiTagStatsRaw")
## settings end ##

def _batches(iterable, size):
  for i in xrange(0, len(iterable), size):
    yield iterable[i:i + size]

def _format_point(tag,stat,value,timestamp):
  try:
    series = conf['influx']['schema'].get('series') or "wtag"
  except KeyError:
    series = "wtag"

  try:
    stat = conf['influx']['schema']['stat_map'].get(stat) or stat
  except KeyError:
    pass

  tag = str(tag).replace(' ','\ ')
  timestamp = str(timestamp*1000000000)

  point = series + ",tag=\"" + tag + "\" " + stat + "=" + str(value) + " " + timestamp
  return point

def _main():
  parser = argparse.ArgumentParser(description="Copy data from Wireless Tags API to InfluxDB", epilog="Available STAT types depend on the tag, but these are the current known types: temperature, dp (dew point), cap (humidity), batteryVolt, signal, motion, light")

  parser.add_argument('--stat', metavar='STAT', default="temperature", help='stat type to fetch (defaults to temperature)')
  parser.add_argument('--last', metavar='N', type=int, default=30, help='fetch last N minutes of data')
  parser.add_argument('--fromdate', metavar='YYYY-MM-DD[THH:MM]', help='fetch data starting from date (optionally time)')
  parser.add_argument('--todate', metavar='YYYY-MM-DD', help='fetch data ending on date (defaults to now)')

  args = parser.parse_args()

  ## Stat translations: http://wirelesstag.net/jshtmlview.aspx?html=tempStatsMulti.html
  wtag_stat = args.stat

  if args.todate and not args.fromdate:
    parser.error('--todate can only be set with --fromdate')

  wtag_local_tz = pytz.timezone(wtag_timezone)
  if not args.fromdate:
    toDate = datetime.now(wtag_local_tz)
    fromDate = toDate - timedelta(minutes=args.last)
  else:
    try:
      fromDate = datetime.strptime(args.fromdate,'%Y-%m-%dT%H:%M')
    except ValueError:
      fromDate = datetime.strptime(args.fromdate,'%Y-%m-%d')
    fromDate = wtag_local_tz.localize(fromDate)
    if args.todate:
      toDate = datetime.strptime(args.todate,'%Y-%m-%d')
      toDate = wtag_local_tz.localize(toDate)
    else:
      toDate = datetime.now(wtag_local_tz)

  print "Requesting WTAG " + wtag_stat + " data, fromDate: " + str(fromDate.strftime("%Y-%m-%dT%H:%M")) + ", toDate: " + str(toDate.strftime("%Y-%m-%d"))

  wtag_rs = requests.Session()

  wtag_r = wtag_rs.post(wtag_signin_url, json = {"email":wtag_email,"password":wtag_password}, timeout=5)
  assert wtag_r.ok, "login failed"

  wtag_r = wtag_rs.post(wtag_getmultitagstatsraw_url, json = {"ids":wtag_tag_ids,"type":wtag_stat,"fromDate":fromDate.strftime("%Y-%m-%dT%H:%M"),"toDate":toDate.strftime("%Y-%m-%d")}, timeout=20)
  assert wtag_r.ok, "GetMultiTagStatsRaw failed"

  j = json.loads(wtag_r.content)

  idmap = {}
  for i,id in enumerate(j['d']['ids'],0):
    idmap[id]=j['d']['names'][i]

  points = []

  for day in j['d']['stats']:
    day_dt = datetime.strptime(day['date'],'%m/%d/%Y')
    day_dt = wtag_local_tz.localize(day_dt)
    for tag_index,tagvalues in enumerate(day['values'],0):
      for i,value in enumerate(tagvalues,0):
        value_dt = day_dt + timedelta(seconds=day['tods'][tag_index][i])
        value_dt_utc = value_dt.astimezone(pytz.utc)
        timestamp = timegm(value_dt_utc.timetuple())
        tag = idmap[day['ids'][tag_index]]
        point = _format_point(tag,wtag_stat,value,timestamp)
        points.append(point)

  if not points:
    print "No data points received from API"
    sys.exit(0)

  influx_rs = requests.Session()

  for batch,data in enumerate(_batches(points, influx_batch_size),1):
    print "WRITE batch " + str(batch) + ", " + str(len(data)) + " points"
    if isinstance(data, str):
      data = [data]
    influx_r = influx_rs.post(influx_write_url, data = ('\n'.join(data) + '\n').encode('utf-8'), timeout=15)
    assert influx_r.ok, "influx write failed: " + influx_r.text

  print "WROTE " + str(len(points)) + " points in " + str(batch) + " batches"

if __name__ == "__main__":
  _main()
