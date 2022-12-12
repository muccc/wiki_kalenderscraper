#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Kalenderscraper
# c007, 10.06.14
# andi, 2017+2018
# max, 2022

import json
import os
import re
from datetime import datetime, timedelta
from itertools import groupby

import pytz
import requests
from bs4 import BeautifulSoup
from icalendar import Calendar, Event


class KalenderScraper:
    def __init__(self, tz: str = "Europe/Berlin"):
        """
        tz: timezone as a string (e.g. 'Europe/Berlin') via pytz


        On init, KalenderScraper scrapes the calendar data from the wiki automatically.
        """
        self.tz = pytz.timezone(tz)
        self.scrape()

    @classmethod
    def _match_class(cls, target):
        def do_match(tag):
            classes = tag.get("class", [])
            return all(c in classes for c in target)

        return do_match

    # merge entries with same date and time together aka merge multi-day events
    @classmethod
    def _accumulate(cls, l):
        for key, group in groupby(l, key=lambda x: "%s:%s" % (x["name"], x["time"])):
            event_occurence = 0
            date_occurence = None
            for i, data in enumerate(group):
                if i == 0:
                    first_day = data["day"]
                event_occurence += 1

            data["day"] = first_day
            data["event_occurence"] = event_occurence

            yield (data)

            # yield (date_occurence, data[1], data[2], key.split(':')[0], data[4],
            #       data[5], data[6], data[7], event_occurence, data[8])

    def scrape(self):
        self.dates = self._parse()
        (self.cal, self.cal_public) = self._calendars()

    def _parse(self):
        # Scrape calender data from wiki
        now = datetime.now()
        soup = BeautifulSoup(
            requests.get("https://wiki.muc.ccc.de/kalender:start").text, "html5lib"
        )
        table = soup.find("table", attrs={"class": "inline"})
        table_body = table.find("tbody")
        rows = table_body.find_all("tr")

        pttrn_date = re.compile(r"[\d]{1,2}.[\d]{1,2}.")
        pttrn_time = re.compile(r"[\d]{1,2}:[\d]{1,2}")

        dates = []

        for row in rows:
            data = row.find_all("td")

            # If there is no valid date found, we skip this entry
            d_date = re.findall(pttrn_date, data[0].get_text().strip(" "))
            if len(d_date) == 1:
                d_date = d_date[0]
            else:
                continue

            # If there is no valid time given, we assume a whole-day event
            cell_time = data[1].get_text().strip(" ")
            d_time = re.findall(pttrn_time, cell_time)

            if len(d_time) == 1:
                d_time = d_time[0]
                d_duration_h = 2
            elif len(d_time) == 2:
                time1 = datetime.strptime(d_time[0], "%H:%M")
                time2 = datetime.strptime(d_time[1], "%H:%M")
                diff = time2 - time1
                d_duration_h = int(diff.total_seconds() / 3600)
                if d_duration_h < 1:
                    d_duration_h = 1
                d_time = d_time[0]
            else:
                d_time = "00:00"
                d_duration_h = 24

            d_link_raw = data[2].find(self._match_class(["urlextern"]))
            d_link = ""
            if d_link_raw:
                d_link = d_link_raw.get("href")
            d_link_raw = data[2].find(self._match_class(["wikilink1"]))
            if d_link_raw:
                d_link = "https://wiki.muc.ccc.de" + d_link_raw.get("href")

            entry = {
                "day": int(d_date.split(".")[0]),
                "month": int(d_date.split(".")[1]),
                "year": now.year,
                "time": d_time,
                "duration": d_duration_h,
                "name": data[2].get_text().strip(" "),
                "public": int(data[3].get_text().strip(" ")),
                "room": data[4].get_text().strip(" "),
                "keyholder": data[5].get_text().strip(" "),
                "url": d_link,
            }

            dates.append(entry)
            # dates.append((d_day, d_month, d_time, d_name, d_public, d_anzahl, d_keyholder, d_link, d_duration_h))

        return dates

    def _calendars(self):
        # Export ics file with all dates
        cal = Calendar()
        cal.add("prodid", "-//wiki.muc.ccc.de Kalenderexport//")
        cal.add("version", "2.0")

        # Separate calendar for public events
        cal_public = Calendar()
        cal_public.add("prodid", "-//wiki.muc.ccc.de Kalenderexport Public//")
        cal_public.add("version", "2.0")

        # Add generation time to the calendar
        cal.add("comment", f"last updated at {datetime.now()}")
        cal_public.add("comment", f"last updated at {datetime.now()}")

        for entry in self._accumulate(self.dates):

            event = Event()
            event.add("summary", entry["name"])

            # first classic events, taking place on one single day
            if entry["event_occurence"] == 1 and entry["duration"] < 24:
                datestring = "{day}.{month}.{year} {time}".format(**entry)
                entry["dtstart"] = datetime.strptime(datestring, "%d.%m.%Y %H:%M")
                entry["dtend"] = entry["dtstart"] + timedelta(hours=entry["duration"])

                # Add timezone information to datetimes: Europe/Berlin
                entry["dtstart"] = entry["dtstart"].replace(tzinfo=self.tz)
                entry["dtend"] = entry["dtend"].replace(tzinfo=self.tz)

                # Add dtstart and dtend to event
                event.add("dtstart", entry["dtstart"])
                event.add("dtend", entry["dtend"])
            else:
                # It's an whole-day or multi-day event
                # Lightning compatible format: VALUE=DATE
                # entry['dtstart'] = datetime.date(entry['year'], entry['month'], entry['day'])
                datestring = "{day}.{month}.{year} {time}".format(**entry)
                entry["dtstart"] = datetime.strptime(datestring, "%d.%m.%Y %H:%M")
                entry["dtend"] = entry["dtstart"] + timedelta(
                    days=int(entry["event_occurence"])
                )
                event.add("dtstart", entry["dtstart"].date())
                event.add("dtend", entry["dtend"].date())

            if entry["public"]:
                if entry["public"] == 1:
                    event.add("description", "Public")
                else:
                    event.add("description", "Members")

            if entry["room"]:
                event.add("location", entry["room"])

            if entry["url"]:
                event.add("url", entry["url"])

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
            entry["name_"] = entry["name"].replace(" ", "")
            uid = "wikical{day}.{month}.{name_}.{time}@api.muc.ccc.de".format(**entry)
            uid = uid.replace(":", ".")

            event.add("uid", uid)

            cal.add_component(event)

            if entry["public"] == 1:
                cal_public.add_component(event)

        return (cal, cal_public)

    def next_event_json(self):
        now = datetime.now()
        # Add timezone information: Europe/Berlin
        now = now.replace(tzinfo=self.tz)
        DayL = [
            "Montag",
            "Dienstag",
            "Mittwoch",
            "Donnerstag",
            "Freitag",
            "Samstag",
            "Sonntag",
        ]
        DayS = ["Mo", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

        # Export next event to JSON
        for entry in self._accumulate(self.dates):
            # print("type dtend: %s" % entry['dtend'])
            # print("type dtend: %s" % type(entry['dtend']))
            # print("type now: %s" %now)
            # print("type now: %s" % type(now))
            if entry["dtend"] > now:
                eventname = entry["name"].replace("ü", "ue")
                eventname = eventname.replace("ä", "ae")
                eventname = eventname.replace("ö", "oe")
                weekday = entry["dtstart"].weekday()
                if entry["event_occurence"] > 1:
                    entry["end_day"] = entry["day"] + entry["event_occurence"] - 1
                    date = "{day}.-{end_day}.{month}.".format(**entry)
                    if len(entry["time"]) == 0:
                        entry["time"] = "10:00"
                else:
                    date = "{day}.{month}.".format(**entry)

                return {
                    "date": date,
                    "time": entry["time"],
                    "weekday": DayS[weekday],
                    "weekday_long": DayL[weekday],
                    "name": eventname,
                    "public": entry["public"],
                }

    def write_files(self, path):
        with open(path + "/wiki_kalender.ics", "wb+") as f:
            f.write(self.cal.to_ical())

        fhandle = open(path + "/wiki_kalender_public.ics", "wb+")
        fhandle.write(self.cal_public.to_ical())
        fhandle.close()

        with open(path + "/nextevent.json", "w+") as f:
            json.dump(self.next_event_json(), f)


def main():
    scraper = KalenderScraper()
    scraper.write_files(os.getcwd())


if __name__ == "__main__":
    main()
