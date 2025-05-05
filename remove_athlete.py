import sys
import json

athlete_id = sys.argv[1]

def read(name: str):
    with open(f"data2/{name}.json", "r") as f:
        return json.load(f)

def remove_from_list(val, key: str, it):
    to_remove = []
    for i, item in enumerate(it):
        if str(item[key]) == str(val):
            to_remove.append(i)
    for i in to_remove[::-1]:
        it.pop(i)

def save(name: str, data):
    with open(f"data2/{name}.json", "w") as f:
        json.dump(data, f)

data: list = read("activities")
remove_from_list(athlete_id, "athlete_id", data)
save("activities", data)

data: list = read("ksat")
for key, value in data.items():
    remove_from_list(athlete_id, "athlete_id", value)
save("ksat", data)

data: list = read("orbit")
for key, value in data.items():
    remove_from_list(athlete_id, "athlete_id", value)
save("orbit", data)

data: list = read("leaderboard_single_activity")
if athlete_id in data:
    del data[athlete_id]
save("leaderboard_single_activity", data)

data: dict = read("totals")
if athlete_id in data:
    del data[athlete_id]
save("totals", data)

