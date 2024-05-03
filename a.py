import requests
import datetime
import json

headers = {
    "Accept": "text/javascript, application/javascript, application/ecmascript, application/x-ecmascript",
    "X-Requested-With": "XMLHttpRequest",
}
try:
    with open("token.txt") as f:
        token = f.read().strip()
except FileNotFoundError:
    token = ""

cookies = {
    "_strava4_session": token,
}
# KSAT: 471480
# ORBIT: 1131791

# TODO: adjust.
MEMBERS_ORBIT = 107
MEMBERS_KSAT = 450

KSAT_LOGO = "ksat.png"
ORBIT_LOGO = "orbit.png"

time = datetime.datetime.now()
week_num = int(
    (time - datetime.datetime(2024, 4, 29)).total_seconds() // (3600 * 24 * 7)
)

use_cache = True
if not use_cache:
    ksat_w1 = requests.get(
        "https://strava.com/clubs/471480/leaderboard?week_offset=1",
        headers=headers,
        cookies=cookies,
    ).json()["data"]
    ksat = requests.get(
        "https://strava.com/clubs/471480/leaderboard", headers=headers, cookies=cookies
    ).json()["data"]

    orbit_w1 = requests.get(
        "https://strava.com/clubs/1131791/leaderboard?week_offset=1",
        headers=headers,
        cookies=cookies,
    ).json()["data"]
    orbit = requests.get(
        "https://strava.com/clubs/1131791/leaderboard", headers=headers, cookies=cookies
    ).json()["data"]

    with open(f"data/{week_num}.json", "w") as f:
        json.dump({"ksat": ksat, "orbit": orbit}, f)

    with open(f"data/{week_num - 1}.json", "w") as f:
        json.dump({"ksat": ksat_w1, "orbit": orbit_w1}, f)


# read data
orbit_banned = [
    53367167,  # Erlend Nesse
    134535626,  # Dennis Langer
    118959474,  # Hans Kristian
    58732624,  # Nora Trohaug
    55631939,  # Olivia Skibelid
    80290094,  # Oscar Langfoss
    92922838,  # Sumeyo Sharif
    117191735,  # Tim Matras
    8804086,  # Ulrik Falk-Petersen
]
ksat_banned = [
    47158881,  # Freider Engstrøm Fløan
    56894134,  # Aslak Strand
    34927378,  # Astrid Fossum
    67451048,  # Markus A. Stokkenes
    117676646,  # Dabrowka Knach
    1270026,  # Roy Sorensen
    34235219,  # Carl H Jonsson
    23605581,  # Rasmus Nordahl
]

orbit = []
ksat = []

ksat_weeks = {
    "height": [0, 0, 0, 0, 0],
    "distance": [0, 0, 0, 0, 0],
    "improved_distance": [0, 0, 0, 0, 0],
    "improved_height": [0, 0, 0, 0, 0],
}
orbit_weeks = {
    "height": [0, 0, 0, 0, 0],
    "distance": [0, 0, 0, 0, 0],
    "improved_distance": [0, 0, 0, 0, 0],
    "improved_height": [0, 0, 0, 0, 0],
}
for i in range(-1, week_num + 1):
    with open(f"data/{i}.json", "r") as f:
        data = json.load(f)
    # jada duplikat men who cares
    for member in data["orbit"]:
        if member["athlete_id"] in orbit_banned:
            continue
        orbit_weeks["distance"][i] += member["distance"]
        orbit_weeks["height"][i] += member["elev_gain"]
        if i < 0:
            continue
        for member2 in orbit:
            if member2["athlete_id"] == member["athlete_id"]:
                member2["duration"] += member["duration"]
                member2["num_activities"] += member["num_activities"]
                member2["elev_gain"] += member["elev_gain"]
                member2["moving_time"] += member["moving_time"]
                member2["distance"] += member["distance"]
                member2["best_activities_distance"] = max(
                    member2["best_activities_distance"],
                    member["best_activities_distance"],
                )
                break
        else:  # add to list if not present already
            member["org"] = "orbit"
            orbit.append(member)

    for member in data["ksat"]:
        if member["athlete_id"] in ksat_banned:
            continue
        ksat_weeks["distance"][i] += member["distance"]
        ksat_weeks["height"][i] += member["elev_gain"]
        if i < 0:
            continue
        for member2 in ksat:
            if member2["athlete_id"] == member["athlete_id"]:
                member2["duration"] += member["duration"]
                member2["num_activities"] += member["num_activities"]
                member2["elev_gain"] += member["elev_gain"]
                member2["moving_time"] += member["moving_time"]
                member2["distance"] += member["distance"]
                member2["best_activities_distance"] = max(
                    member2["best_activities_distance"],
                    member["best_activities_distance"],
                )
                break
        else:  # add to list if not present already
            member["org"] = "ksat"
            ksat.append(member)
    if i >= 0:
        orbit_weeks["improved_distance"][i] = round(
            100 * (orbit_weeks["distance"][i] / orbit_weeks["distance"][i - 1] - 1),
            1,
        )
        ksat_weeks["improved_distance"][i] = round(
            100 * (ksat_weeks["distance"][i] / ksat_weeks["distance"][i - 1] - 1),
            1,
        )
        orbit_weeks["improved_height"][i] = round(
            100 * (orbit_weeks["height"][i] / orbit_weeks["height"][i - 1] - 1),
            1,
        )
        ksat_weeks["improved_height"][i] = round(
            100 * (ksat_weeks["height"][i] / ksat_weeks["height"][i - 1] - 1),
            1,
        )

ksat_weeks_strings = []
orbit_weeks_strings = []
for i in range(-1, week_num + 1):
    orbit_weeks["distance"][i] = round(orbit_weeks["distance"][i] / 1000, 1)
    orbit_weeks["height"][i] = int(orbit_weeks["height"][i])
    orbit_weeks["improved_distance"][i] = round(orbit_weeks["improved_distance"][i], 1)
    orbit_weeks["improved_height"][i] = round(orbit_weeks["improved_height"][i], 1)

    ksat_weeks["distance"][i] = round(ksat_weeks["distance"][i] / 1000, 1)
    ksat_weeks["height"][i] = int(ksat_weeks["height"][i])
    ksat_weeks["improved_distance"][i] = round(ksat_weeks["improved_distance"][i], 1)
    ksat_weeks["improved_height"][i] = round(ksat_weeks["improved_height"][i], 1)
    ksat_weeks_strings.append(
        f"Week {i+1}: {ksat_weeks['distance'][i]:>6}km ({('+' if ksat_weeks['improved_distance'][i] >= 0 else '-') + str(ksat_weeks['improved_distance'][i]):>5}%), {ksat_weeks['height'][i]:>5}m ({('+' if ksat_weeks['improved_height'][i] >= 0 else '-') + str(ksat_weeks['improved_height'][i]):>5}%)"
    )
    orbit_weeks_strings.append(
        f"Week {i+1}: {orbit_weeks['distance'][i]:>6}km ({('+' if orbit_weeks['improved_distance'][i] >= 0 else '-') + str(orbit_weeks['improved_distance'][i]):>5}%), {orbit_weeks['height'][i]:>5}m ({('+' if orbit_weeks['improved_height'][i] >= 0 else '-') + str(orbit_weeks['improved_height'][i]):>5}%)"
    )

ksat_length = sum(x["distance"] for x in ksat)
ksat_height = sum(x["elev_gain"] for x in ksat)

orbit_length = sum(x["distance"] for x in orbit)
orbit_height = sum(x["elev_gain"] for x in orbit)
longest = sorted(ksat + orbit, key=lambda x: x["distance"], reverse=True)
highest = sorted(ksat + orbit, key=lambda x: x["elev_gain"], reverse=True)

i = 0
for athlete in longest:
    i += 1
    athlete["length_rank"] = i

i = 0
for athlete in highest:
    i += 1
    athlete["height_rank"] = i


with open("data/history.json", "r") as f:
    history = json.load(f)

if "marathon" not in history:
    history["marathon"] = []

if "tshirt" not in history:
    history["tshirt"] = []

for member in ksat + orbit:
    if member["distance"] < 16000:
        continue  # not qualified
    for member2 in history["tshirt"]:
        if member2["athlete"]["athlete_id"] == member["athlete_id"]:
            if member["athlete_picture_url"] != "/assets/avatar/athlete/medium.png":
                member2["athlete"]["athlete_picture_url"] = member[
                    "athlete_picture_url"
                ]
                member2["athlete"]["athlete_lastname"] = member["athlete_lastname"]
            break
    else:
        history["tshirt"].append({"athlete": member, "time": time.isoformat()})

for member in ksat + orbit:
    if member["distance"] < 100000:
        continue  # not qualified
    for member2 in history["marathon"]:
        if member2["athlete"]["athlete_id"] == member["athlete_id"]:
            if member["athlete_picture_url"] != "/assets/avatar/athlete/medium.png":
                member2["athlete_picture_url"] = member["athlete_picture_url"]
                member2["athlete_lastname"] = member["athlete_lastname"]
            break
    else:
        history["marathon"].append({"athlete": member, "time": time.isoformat()})

for athlete in ksat + orbit:
    id = str(athlete["athlete_id"])

    if id not in history["athletes"]:
        history["athletes"][id] = {
            "firstname": athlete["athlete_firstname"],
            "lastname": athlete["athlete_lastname"],
            "picture": athlete["athlete_picture_url"],
            "history": [],
        }
    else:
        if athlete["athlete_picture_url"] != "/assets/avatar/athlete/medium.png":
            history["athletes"][id]["picture"] = member["athlete_picture_url"]
            history["athletes"][id]["lastname"] = member["athlete_lastname"]

    athlete2 = history["athletes"][id]
    athlete2["history"].append(
        {
            "time": time.isoformat(),
            "distance": athlete["distance"],
            "height": athlete["elev_gain"],
            "moving_time": athlete["moving_time"],
            "num_activities": athlete["num_activities"],
            "velocity": athlete["velocity"],
            "height_rank": athlete["height_rank"],
            "length_rank": athlete["length_rank"],
        }
    )

history["orbit"].append(
    {
        "time": time.isoformat(),
        "distance": orbit_length,
        "height": orbit_height,
        "height_rank": 1 if ksat_height >= orbit_height else 2,
        "length_rank": 1 if ksat_length >= orbit_length else 2,
    }
)

history["ksat"].append(
    {
        "time": time.isoformat(),
        "distance": ksat_length,
        "height": ksat_height,
        "height_rank": 1 if orbit_height >= ksat_height else 2,
        "length_rank": 1 if orbit_length >= ksat_length else 2,
    }
)

with open("data/history.json", "w") as f:
    json.dump(history, f, indent=2)


def pretty(num, div=1000):
    return round(num / div, 1)


with open("data/latest.json", "w") as f:
    for athlete in longest:
        athlete["distance"] = pretty(athlete["distance"])
        athlete["org_pic"] = KSAT_LOGO if athlete["org"] == "ksat" else ORBIT_LOGO
    for athlete in highest:
        athlete["elev_gain"] = int(athlete["elev_gain"])
        athlete["org_pic"] = KSAT_LOGO if athlete["org"] == "ksat" else ORBIT_LOGO

    longest_athlete = sorted(
        ksat + orbit, key=lambda x: x["best_activities_distance"], reverse=True
    )[0]
    longest_athlete["best_activities_distance"] = pretty(
        longest_athlete["best_activities_distance"]
    )
    for athlete in history["tshirt"]:
        athlete["time"] = datetime.datetime.fromisoformat(athlete["time"]).strftime(
            "%d-%m-%Y %H:%M"
        )
        athlete["athlete"]["org_pic"] = (
            KSAT_LOGO if athlete["athlete"]["org"] == "ksat" else ORBIT_LOGO
        )
    for athlete in history["marathon"]:
        athlete["athlete"]["org_pic"] = (
            KSAT_LOGO if athlete["athlete"]["org"] == "ksat" else ORBIT_LOGO
        )
        athlete["time"] = datetime.datetime.fromisoformat(athlete["time"]).strftime(
            "%d-%m-%Y %H:%M"
        )

    ksat_dpm = pretty(sum(x["distance"] * 1000 for x in orbit) / MEMBERS_KSAT)
    orbit_dpm = pretty(sum(x["distance"] * 1000 for x in ksat) / MEMBERS_ORBIT)

    total_time = (
        datetime.datetime(2024, 5, 27) - datetime.datetime(2024, 4, 29)
    ).total_seconds()
    since_start = (
        datetime.datetime.now() - datetime.datetime(2024, 4, 29)
    ).total_seconds()
    percentage_done = since_start / total_time
    orbit_progress = percentage_done * min(orbit_dpm / ksat_dpm, 1) * 80
    ksat_progress = (
        percentage_done * min(ksat_dpm / orbit_dpm, 1) * 80
    )  # this 80 is to make stuff align on the webpage lol

    json.dump(
        {
            "orbit_height": int(orbit_height),
            "ksat_height": int(ksat_height),
            "orbit_length": pretty(orbit_length),
            "ksat_length": pretty(ksat_length),
            "longest": longest[:10],
            "highest": highest[:10],
            "total_length": pretty(orbit_length + ksat_length),
            "total_height": int(orbit_height + ksat_height),
            "tshirt": history["tshirt"],
            "marathon": history["marathon"],
            "ksat_distance_per_member": ksat_dpm,
            "orbit_distance_per_member": orbit_dpm,
            "longest_single_distance": longest_athlete,
            "orbit_progress": orbit_progress,
            "ksat_progress": ksat_progress,
            "tshirt_count": len(history["tshirt"]),
            "marathon_count": len(history["marathon"]),
            "ksat_weeks": ksat_weeks_strings,
            "orbit_weeks": orbit_weeks_strings,
        },
        f,
        indent=2,
    )

for s in ksat_weeks_strings:
    print(s)
