import os
from flask import Flask, jsonify, render_template
from flask_cors import CORS

from collections import namedtuple
import pandas as pd
import requests

APP = Flask(__name__)
CORS(APP)

ICAO_LOOKUP = pd.read_pickle("icao-explanations.pickle")

ALTITUDE_OF_INTEREST = 1000
EPSILON = 0.09


def root_dir():  # pragma: no cover
    return os.path.abspath(os.path.dirname(__file__))


def get_file(filename):  # pragma: no cover
    try:
        src = os.path.join(root_dir(), filename)
        # Figure out how flask returns static files
        # Tried:
        # - render_template
        # - send_file
        # This should not be so non-obvious
        return open(src).read()
    except IOError as exc:
        return '' # str(exc)


State = namedtuple(
    "State", [
        "icao24",
        "callsign",
        "origin_country",
        "time_position",
        "last_contact",
        "longitude",
        "latitude",
        "baro_altitude",
        "on_ground",
        "velocity",
        "true_track",
        "vertical_rate",
        "sensors",
        "geo_altitude",
        "squawk",
        "spi",
        "position_source",
    ]
)


def get_aircraft_around(lat, lng):
    lamin = lat - EPSILON
    lamax = lat + EPSILON
    lomin = lng - EPSILON
    lomax = lng + EPSILON
    result = requests.get(
        f"https://opensky-network.org/api/states/all?lamin={lamin}&lomin={lomin}&lamax={lamax}&lomax={lomax}"
    ).json()

    # states = [
    #     State(*state)
    #     for state in
    #     result['states']
    # ]

    df = pd.DataFrame(result['states'], columns = [
        "icao24",
        "callsign",
        "origin_country",
        "time_position",
        "last_contact",
        "longitude",
        "latitude",
        "baro_altitude",
        "on_ground",
        "velocity",
        "true_track",
        "vertical_rate",
        "sensors",
        "geo_altitude",
        "squawk",
        "spi",
        "position_source",
    ])
    return df


def get_info_for_icao(icao):
    return requests.get(f"https://opensky-network.org/api/metadata/aircraft/icao/{icao}").json()


@APP.route("/near/<lat>/<lng>")
def get_near_lat_lng(lat, lng):
    lat = float(lat)
    lng = float(lng)
    candidates = get_aircraft_around(lat, lng)
    total_count = len(candidates)
    candidates = candidates[(candidates.geo_altitude < ALTITUDE_OF_INTEREST) & (~candidates.on_ground)]

    # enrich with wikipedia affiliations:
    newdf = pd.DataFrame([
        i.iloc[0] if len(i) else {}
        for i in candidates.callsign.str.slice(0, 3).map(
            lambda callpre: ICAO_LOOKUP[ICAO_LOOKUP.ICAO.str.slice(0, 3) == callpre.upper()]
        )
    ])
    candidates = pd.concat([
        candidates.reset_index(drop=True),
        newdf.reset_index(drop=True)
    ], axis='columns')


    # enrich with opensky info:
    candidates['owner'] = [None] * len(candidates.index)
    candidates['manufacturerName'] = [None] * len(candidates.index)
    candidates['model'] = [None] * len(candidates.index)
    for i, c in candidates.iterrows():
        try:
            info = get_info_for_icao(c.icao24)
            candidates._set_value(i, "owner", info['owner'])
            candidates._set_value(i, "manufacturerName", info['manufacturerName'])
            candidates._set_value(i, "model", info['model'])
        except Exception as e:
            print(e)

    return jsonify({
        "aircraft": candidates.T.to_json(),
        "total_count": total_count
    })

@APP.route("/")
def home():
    return get_file("templates/index.html")

if __name__ == "__main__":
    APP.run(host="0.0.0.0", debug=True)

"""
0 	icao24 	string 	Unique ICAO 24-bit address of the transponder in hex string representation.
1 	callsign 	string 	Callsign of the vehicle (8 chars). Can be null if no callsign has been received.
2 	origin_country 	string 	Country name inferred from the ICAO 24-bit address.
3 	time_position 	int 	Unix timestamp (seconds) for the last position update. Can be null if no position report was received by OpenSky within the past 15s.
4 	last_contact 	int 	Unix timestamp (seconds) for the last update in general. This field is updated for any new, valid message received from the transponder.
5 	longitude 	float 	WGS-84 longitude in decimal degrees. Can be null.
6 	latitude 	float 	WGS-84 latitude in decimal degrees. Can be null.
7 	baro_altitude 	float 	Barometric altitude in meters. Can be null.
8 	on_ground 	boolean 	Boolean value which indicates if the position was retrieved from a surface position report.
9 	velocity 	float 	Velocity over ground in m/s. Can be null.
10 	true_track 	float 	True track in decimal degrees clockwise from north (north=0°). Can be null.
11 	vertical_rate 	float 	Vertical rate in m/s. A positive value indicates that the airplane is climbing, a negative value indicates that it descends. Can be null.
12 	sensors 	int[] 	IDs of the receivers which contributed to this state vector. Is null if no filtering for sensor was used in the request.
13 	geo_altitude 	float 	Geometric altitude in meters. Can be null.
14 	squawk 	string 	The transponder code aka Squawk. Can be null.
15 	spi 	boolean 	Whether flight status indicates special purpose indicator.
16 	position_source 	int 	Origin of this state’s position: 0 = ADS-B, 1 = ASTERIX, 2 = MLAT"""