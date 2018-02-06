#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Kalenderscraper
# c007, 10.06.14

import os
import datetime
import requests
from bs4 import BeautifulSoup
from icalendar import Calendar, Event
import json
import re
from itertools import groupby

requests.packages.urllib3.disable_warnings()



def match_class(target):
    def do_match(tag):
        classes = tag.get('class', [])
        return all(c in classes for c in target)
    return do_match


DayL = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday',
        'Saturday', 'Sunday']

now = datetime.datetime.now()

# Scrape calender data from wiki
soup = BeautifulSoup(requests.get('https://wiki.muc.ccc.de/kalender',
                     verify=False).text, 'html5lib')
table = soup.find('table', attrs={'class': 'inline'})
table_body = table.find('tbody')
rows = table_body.find_all('tr')

dates = []

pttrn_date = re.compile(ur'[\d]{1,2}.[\d]{1,2}.')
pttrn_time = re.compile(ur'[\d]{1,2}:[\d]{1,2}')

for row in rows:
    data = row.find_all("td")

    # If there is no valid date found, we skip this entry
    d_date = re.findall(pttrn_date, data[0].get_text().strip(' '))
    if len(d_date) == 1:
        d_date = d_date[0]
    else:
        continue

    # If there is no valid time given, we assume a whole-day event
    cell_time = data[1].get_text().strip(' ')
    d_time = re.findall(pttrn_date, cell_time)

    if len(d_time) == 1:
        d_time = d_time[0]
        d_duration_h = 2
    else:
        d_time = "00:00"
        d_duration_h = 24


    d_link_raw = data[2].find(match_class(["urlextern"]))
    d_link = u''
    if d_link_raw:
        d_link = d_link_raw.get('href')
    d_link_raw = data[2].find(match_class(["wikilink1"]))
    if d_link_raw:
        d_link = 'https://wiki.muc.ccc.de' + d_link_raw.get('href')

    entry = {
        'day': int(d_date.split('.')[0]),
        'month': int(d_date.split('.')[1]),
        'year': now.year,
        'time': d_time,
        'duration': d_duration_h,
        'name': data[2].get_text().strip(' '),
        'public': int(data[3].get_text().strip(' ')),
        'room': data[4].get_text().strip(' '),
        'keyholder': data[5].get_text().strip(' '),
        'url': d_link
    }

    dates.append(entry)
    #dates.append((d_day, d_month, d_time, d_name, d_public, d_anzahl, d_keyholder, d_link, d_duration_h))


# merge entries with same date and time together aka merge multi-day events
def accumulate(l):
    for key, group in groupby(l, key=lambda x: '%s:%s' % (x['name'], x['time'])):
        event_occurence = 0
        date_occurence = None
        for i, data in enumerate(group):
            if i == 0:
                first_day = data['day']
            event_occurence += 1

        data['day'] = first_day
        data['event_occurence'] = event_occurence

        yield(data)

        #yield (date_occurence, data[1], data[2], key.split(':')[0], data[4],
        #       data[5], data[6], data[7], event_occurence, data[8])



# Export ics file with all dates
cal = Calendar()
cal.add('prodid', '-//wiki.muc.ccc.de Kalenderexport//')
cal.add('version', '2.0')

# Separate calendar for public events
cal_public = Calendar()
cal_public.add('prodid', '-//wiki.muc.ccc.de Kalenderexport Public//')
cal_public.add('version', '2.0')

for entry in accumulate(dates):

    event = Event()
    event.add('summary', entry['name'])

    # first classic events, taking place on one single day
    if entry['event_occurence'] == 1 and entry['duration'] < 24:
        datestring = '{day}.{month}.{year} {time}'.format(**entry)
        dtstart = datetime.datetime.strptime(datestring, "%d.%m.%Y %H:%M")
        event.add('dtstart', dtstart)
        # just default duration of x hours for the each event
        event.add('dtend',   dtstart+datetime.timedelta(hours=entry['duration']))
    else:
        # It's an whole-day or multi-day event
        # Lightning compatible format: VALUE=DATE
        dtstart = datetime.date(entry['year'], entry['month'], entry['day'])
        event.add('dtstart', dtstart)
        event.add('dtend', dtstart + datetime.timedelta(days=int(entry['event_occurence'])))

    if entry['public']:
        if entry['public'] == 1:
            event.add('description', 'Public')
        else:
            event.add('description', 'Members')

    if entry['room']:
        event.add('location', entry['room'])

    if entry['url']:
        event.add('url', entry['url'])

    # Adding a UID, required by ical spec section 4.8.4.7 (Unique Identifier)
    # (...)
    # The property MUST be specified in the "VEVENT", "VTODO", "VJOURNAL" or
    # "VFREEBUSY" calendar components.
    # (...)
    # The UID itself MUST be a globally unique identifier. The generator of the
    # identifier MUST guarantee that the identifier is unique. There are
    # several algorithms that can be used to accomplish this. The identifier is
    # RECOMMENDED to be the identical syntax to the [RFC 822] addr-spec.
    #
    # Calendaring and scheduling applications MUST generate this property in
    # "VEVENT", "VTODO" and "VJOURNAL" calendar components to assure
    # interoperability with other group scheduling applications. This
    # identifier is created by the calendar system that generates an iCalendar
    # object.
    #
    # Implementations MUST be able to receive and persist values of at least
    # 255 characters for this property.
    entry['name_'] = entry['name'].replace(" ", "")
    uid = u'wikical{day}.{month}.{name_}.{time}@api.muc.ccc.de'.format(**entry)
    uid = uid.replace(':', '.')

    event.add('uid', uid)

    cal.add_component(event)

    if entry['public'] == 1:
        cal_public.add_component(event)

path = os.path.dirname(os.path.realpath(__file__))

fhandle = open(path + '/wiki_kalender.ics', "w+")
fhandle.write(cal.to_ical())
fhandle.close()

fhandle = open(path + '/wiki_kalender_public.ics', "w+")
fhandle.write(cal_public.to_ical())
fhandle.close()

# Export next event to JSON file
for entry in accumulate(dates):
    if entry['event_occurence'] > 1:
        datestring = '{day}.{month}.{year} 00:00'.format(**entry)
        testdate = datetime.datetime.strptime(datestring, "%d.%m.%Y %H:%M")
    else:
        datestring = '{day}.{month}.{year} {time}'.format(**entry)
        testdate = datetime.datetime.strptime(datestring, "%d.%m.%Y %H:%M")

    if testdate > now:
        eventname = entry['name'].replace(u'ü', 'ue')
        eventname = eventname.replace(u'ä', 'ae')
        eventname = eventname.replace(u'ö', 'oe')

        if entry['event_occurence'] > 1:
            entry['end_day'] = entry['day'] + entry['event_occurence'] - 1
            jsonstring = json.dumps({'date': '{day}.-{end_day}.{month}.'.format(**entry),
                                     'time': '10:00',
                                     'weekday': DayL[testdate.weekday()],
                                     'name': eventname,
                                     'public': entry['public']})

        else:
            jsonstring = json.dumps({'date': '{day}.{month}.'.format(**entry),
                                     'time': entry['time'],
                                     'weekday': DayL[testdate.weekday()],
                                     'name': eventname,
                                     'public': entry['public']})

        path = os.path.dirname(os.path.realpath(__file__))
        fhandle = open(path + '/nextevent.json', "w+")
        print >> fhandle, jsonstring
        fhandle.close()
        break
