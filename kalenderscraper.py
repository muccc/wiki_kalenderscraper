# -*- coding: utf-8 -*-
# Kalenderscraper
# c007, 10.06.14

import os
import datetime
import urllib2
from bs4 import BeautifulSoup
from icalendar import Calendar, Event
import json
import re

DayL = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']

now = datetime.datetime.now()

# Scrape calender data from wiki
soup = BeautifulSoup(urllib2.urlopen('http://wiki.muc.ccc.de/kalender').read())
rows = soup.find("table").find_all('tr')

dates = []

pttrn = re.compile(ur'[\d]{1,2}.[\d]{1,2}.')

for row in rows:
    try:
        data = row.find_all("td")

        d_date  = re.findall(pttrn, data[0].get_text())[0]
        d_day   = d_date.split('.')[0]
        d_month = d_date.split('.')[1]
        d_time  = data[1].get_text().strip(' ')
        d_name  = data[2].get_text().strip(' ')
        d_public= data[3].get_text().strip(' ')
        d_anzahl= data[4].get_text().strip(' ')
        d_keyholder = data[5].get_text().strip(' ')

        dates.append((d_day, d_month, d_time, d_name,
                    d_public, d_anzahl, d_keyholder))

    except:
        pass


# Export ics file with all dates
cal = Calendar()
cal.add('prodid', '-//wiki.muc.ccc.de Kalenderexport//')
cal.add('version', '2.0')

for date in dates:

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
        event.add('dtend', dtstart + datetime.timedelta(days=1))

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
for date in dates:
    testdate = datetime.datetime.strptime(date[0] + "." + date[1] + "." + \
                str(now.year) + " " + date[2], "%d.%m.%Y %H:%M")    

    if testdate > now:   
        eventname = date[3].replace(u'ü', 'ue').replace(u'ä','ae').replace(u'ö','oe')
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
