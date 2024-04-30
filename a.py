import requests
import datetime
import json

headers = {
    "Accept": "text/javascript, application/javascript, application/ecmascript, application/x-ecmascript",
    "X-Requested-With": "XMLHttpRequest",
}
# KSAT: 471480
# ORBIT: 1131791
time = datetime.datetime.now()
week_num = int(
    (time - datetime.datetime(2024, 4, 29)).total_seconds() // (3600 * 24 * 7)
)

use_cache = False
if not use_cache:
    ksat_w1 = requests.get(
        "https://strava.com/clubs/471480/leaderboard?week_offset=1", headers=headers
    ).json()["data"]
    ksat = requests.get(
        "https://strava.com/clubs/471480/leaderboard", headers=headers
    ).json()["data"]

    orbit_w1 = requests.get(
        "https://strava.com/clubs/1131791/leaderboard?week_offset=1", headers=headers
    ).json()["data"]
    orbit = requests.get(
        "https://strava.com/clubs/1131791/leaderboard", headers=headers
    ).json()["data"]

    with open(f"data/{week_num}.json", "w") as f:
        json.dump({"ksat": ksat, "orbit": orbit}, f)

    if week_num > 0:
        with open(f"data/{week_num}.json", "w") as f:
            json.dump({"ksat": ksat_w1, "orbit": orbit_w1}, f)


# read data
orbit_banned = []
ksat_banned = [
    47158881,  # Freider
]

orbit = []
ksat = []
for i in range(week_num + 1):
    with open(f"data/{i}.json", "r") as f:
        data = json.load(f)

    # jada duplikat men who cares
    for member in data["orbit"]:
        if member["athlete_id"] in orbit_banned:
            continue
        for member2 in orbit:
            if member2["athlete_id"] == member["athlete_id"]:
                member2["duration"] += member["duration"]
                member2["num_activities"] += member["num_activities"]
                member2["elev_gain"] += member["elev_gain"]
                member2["moving_time"] += member["moving_time"]
                member2["distance"] += member["distance"]
                member2["best_activities_distance"] = max(member2["best_activities_distance"], member["best_activities_distance"])
                break
        else:  # add to list if not present already
            member["org"] = "orbit"
            orbit.append(member)

    for member in data["ksat"]:
        if member["athlete_id"] in ksat_banned:
            continue
        for member2 in ksat:
            if member2["athlete_id"] == member["athlete_id"]:
                member2["duration"] += member["duration"]
                member2["num_activities"] += member["num_activities"]
                member2["elev_gain"] += member["elev_gain"]
                member2["moving_time"] += member["moving_time"]
                member2["distance"] += member["distance"]
                member2["best_activities_distance"] = max(member2["best_activities_distance"], member["best_activities_distance"])
                break
        else:  # add to list if not present already
            member["org"] = "ksat"
            ksat.append(member)


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

for athlete in ksat + orbit:
    id = str(athlete["athlete_id"])
    
    if id not in history["athletes"]:
        history["athletes"][id] = {
            "firstname": athlete["athlete_firstname"], 
            "lastname": athlete["athlete_lastname"],
            "picture": athlete["athlete_picture_url"],
            "history": []
        }
    
    athlete2 = history["athletes"][id]
    athlete2["history"].append({
        "time": time.isoformat(),
        "distance": athlete["distance"],
        "height": athlete["elev_gain"],
        "moving_time": athlete["moving_time"],
        "num_activities": athlete["num_activities"],
        "velocity": athlete["velocity"],
        "height_rank": athlete["height_rank"],
        "length_rank": athlete["length_rank"],
    })

history["orbit"].append({
    "time": time.isoformat(),
    "distance": orbit_length,
    "height": orbit_height,
    "height_rank": 1 if ksat_height >= orbit_height else 2,
    "length_rank": 1 if ksat_length >= orbit_length else 2,
})

history["ksat"].append({
    "time": time.isoformat(),
    "distance": ksat_length,
    "height": ksat_height,
    "height_rank": 1 if orbit_height >= ksat_height else 2,
    "length_rank": 1 if orbit_length >= ksat_length else 2,
})

with open("data/history.json", "w") as f:
    json.dump(history, f, indent=2)

with open("data/latest.json", "w") as f:
    json.dump(
        {
            "orbit_height": orbit_height,
            "ksat_height": ksat_height,
            "orbit_length": orbit_length,
            "ksat_length": ksat_length,
            "longest": longest[:10],
            "highest": highest[:10],
            "total_length": orbit_length + ksat_length,
            "total_height": orbit_height + ksat_height,
        },
        f,
        indent=2,
    )
