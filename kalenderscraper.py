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


def accumulate(l):
    for key, group in groupby(l, key=lambda x: '%s:%s' % (x[3], x[2])):
        event_occurence = 0
        date_occurence = None
        for i, data in enumerate(group):
            if i == 0:
                date_occurence = data[0]
            event_occurence+=1
        yield (date_occurence, data[1], data[2], key.split(':')[0], data[4], data[5], data[6], data[7], event_occurence)


def match_class(target):
    def do_match(tag):
        classes = tag.get('class', [])
        return all(c in classes for c in target)
    return do_match


DayL = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']

now = datetime.datetime.now()

# Scrape calender data from wiki
soup = BeautifulSoup(requests.get('https://wiki.muc.ccc.de/kalender', verify=False).text, 'html5lib')
table = soup.find('table', attrs={'class': 'inline'})
table_body = table.find('tbody')
rows = table_body.find_all('tr')

dates = []

pttrn = re.compile(ur'[\d]{1,2}.[\d]{1,2}.')

for row in rows:
    data = row.find_all("td")

    d_date  = re.findall(pttrn, data[0].get_text())[0]
    d_day   = d_date.split('.')[0]
    d_month = d_date.split('.')[1]
    d_time  = data[1].get_text().strip(' ')
    d_name  = data[2].get_text().strip(' ')
    d_link_raw = data[2].find(match_class(["urlextern"]))
    if d_link_raw:
        d_link = d_link_raw.get('href')
    d_link_raw = data[2].find(match_class(["wikilink1"]))
    if d_link_raw:
        d_link = 'https://wiki.muc.ccc.de' + d_link_raw.get('href')
    d_public= data[3].get_text().strip(' ')
    d_anzahl= data[4].get_text().strip(' ')
    d_keyholder = data[5].get_text().strip(' ')

    dates.append((d_day, d_month, d_time, d_name,
                d_public, d_anzahl, d_keyholder, d_link))
    d_link = u''


# Export ics file with all dates
cal = Calendar()
cal.add('prodid', '-//wiki.muc.ccc.de Kalenderexport//')
cal.add('version', '2.0')

for date in accumulate(dates):

    event = Event()
    event.add('summary', date[3])

    if date[2]:
        dtstart = datetime.datetime.strptime(date[0] + "." + date[1] + "." +
                    str(now.year) + " " + date[2], "%d.%m.%Y %H:%M")
        event.add('dtstart', dtstart)
        # just default duration of x hours for the each event
        event.add('dtend',   dtstart+datetime.timedelta(hours=2))
    else:
        # If no time given, assume an all-day event
        # Lightning compatible format: VALUE=DATE
        dtstart = datetime.date(now.year, int(date[1]), int(date[0]))
        event.add('dtstart', dtstart)
        event.add('dtend', dtstart + datetime.timedelta(days=(int(date[8]))))

    if date[4]:
        if int(date[4]) == 1:
            event.add('description', 'Public')
        else:
            event.add('description', 'Members')

    if date[5]:
        event.add('location', date[5])

    if date[7]:
        event.add('url', date[7])

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
    uid = 'wikical' + date[0] + '.' + date[1] + '.' \
            + date[3].replace(" ","") + '.' \
            + date[2] + '@api.muc.ccc.de' 
    uid = uid.replace(':', '.')

    event.add('uid', uid)

    cal.add_component(event)


path = os.path.dirname(os.path.realpath(__file__))
fhandle = open(path + '/wiki_kalender.ics', "w+")
fhandle.write(cal.to_ical())
fhandle.close()


# Export next event to JSON file
for date in accumulate(dates):
    if date[8] > 1:
        testdate = datetime.datetime.strptime(date[0] + "." + date[1] + "." + \
                    str(now.year) + " 00:00" , "%d.%m.%Y %H:%M")
    else:
        testdate = datetime.datetime.strptime(date[0] + "." + date[1] + "." + \
                    str(now.year) + " " + date[2], "%d.%m.%Y %H:%M")

    if testdate > now:
        eventname = date[3].replace(u'ü', 'ue').replace(u'ä', 'ae').replace(u'ö', 'oe')
        if date[8] > 1:
            event_end = int(date[0]) + int((int(date[8]) - 1))
            jsonstring = json.dumps({'date': date[0] + "." + date[1] + ".-" + str(event_end) + "." + date[1] + "." , \
                                     'time': '10:00', \
                                     'weekday': DayL[testdate.weekday()], \
                                     'name': eventname, \
                                     'public': date[4]})

        else:
            jsonstring = json.dumps({'date': date[0] + "." + date[1] + ".", \
                                     'time': date[2], \
                                     'weekday': DayL[testdate.weekday()], \
                                     'name': eventname, \
                                     'public': date[4]})

        path = os.path.dirname(os.path.realpath(__file__))
        fhandle = open(path + '/nextevent.json', "w+")
        print >> fhandle, jsonstring
        fhandle.close()
        break