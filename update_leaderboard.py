import requests
import datetime
import os
import json
from typing import TypedDict
import copy
from dataclasses import dataclass
import math
import traceback
import warnings
import bs4

UPDATE_FREQUENCY_S = 94 * 60 * 60 # check last 24 hours

read_time = datetime.datetime.now()
if read_time.weekday() == 0 and read_time.hour == 0 and read_time.minute < 20:
    # seemed like something really weird happened on the week-change,
    # so make sure to not check immediately after a new week has started.
    # 20 mins is probably way too much but better safe.
    quit(0)

os.makedirs("data", exist_ok=True)
try:
    with open("token.txt") as f:
        token = f.read().strip()
except FileNotFoundError:
    token = ""

class StravaError(Exception): ...

def log_err(message: str):
    time = datetime.datetime.now().isoformat() + ": "
    with open("error_log", "a") as f:
        f.write(time + message + "\n")

@dataclass
class StravaActivity:
    id: int
    type: str
    visibility: str
    start_time: datetime.datetime
    elapsed_time: int
    athlete_id: int
    elapsed_time_list: list[int]
    latlng_list: list[int]
    altitude: list[float]
    elevation_gain: int
    gender: str

    def get_elevation(self):
        return self.elevation_gain

    def calculate_fastest_nk(self, n):
        # Convert to list of distance traveled
        if self.elapsed_time_list == None or self.latlng_list == None or len(self.latlng_list) == 0:
            return float("inf")
        distance = []
        prev_loc = self.latlng_list[0]
        for loc in self.latlng_list:
            distance.append(self._point_distance(loc[0], loc[1], prev_loc[0], prev_loc[1]))
            prev_loc = loc

        target_distance = n * 1000 - 10*n # leave a 1% margin on distance
        dist = 0
        index_end = -1
        while dist < target_distance and (index_end+1) < len(distance):
            index_end += 1
            dist += distance[index_end]
    
        if (dist < target_distance):
            return None

        elapsed_time = self.elapsed_time_list[index_end] - self.elapsed_time_list[0]
        fastest_time = n*1000/(dist/elapsed_time) # distance / avg speed
        for index_start, point in enumerate(distance):
            dist -= point
            while dist < target_distance and (index_end+1) < len(distance):
                index_end += 1
                dist += distance[index_end]
            if dist < target_distance:
                break # Not enough activity left
            elapsed_time = self.elapsed_time_list[index_end] - self.elapsed_time_list[index_start]
            nk_time = n*1000/(dist/elapsed_time) # distance / avg speed
            if nk_time < fastest_time:
                fastest_time = nk_time
        return fastest_time

    def _point_distance(self, lat1, lon1, lat2, lon2):
        earth_radius = 6371000
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        lambda1 = math.radians(lon1)
        lambda2 = math.radians(lon2)
        
        delta_phi = phi2 - phi1
        delta_lambda = lambda2 - lambda1
        some_char = (phi1 + phi2) / 2
        
        x = delta_lambda * math.cos(some_char)
        y = delta_phi
        return earth_radius * math.sqrt(x * x + y * y)




class Strava:
    def __init__(self, token: str):
        self._token = token
    
    def _get_headers(self):
        return {
            "Accept": "text/javascript, application/javascript, application/ecmascript, application/x-ecmascript",
            "X-Requested-With": "XMLHttpRequest",
            "Host": "www.strava.com",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:137.0) Gecko/20100101 Firefox/137.0" 
        }

    def _get_auth(self):
        return {
            "_strava4_session": self._token,
        }

    def get_leaderboard(self, club: int, week_offset: int):
        params = {
            "week_offset": week_offset,
        }
        cookies = self._get_auth()
        res = requests.get(f"https://strava.com/clubs/{club}/leaderboard", params=params, headers=self._get_headers(), cookies=cookies)

        if res.ok:
            pass
        else:
            raise StravaError(f"Could not fetch data from strava ({res.status_code}): {res.content}")

        data = res.json()["data"]
        return data
    
    def get_elevation_gain(self, activity_id):
        res = requests.get(f"https://strava.com/activities/{activity_id}", headers=self._get_headers(), cookies=self._get_auth())
        
        soup = bs4.BeautifulSoup(res.content, features="html.parser")
        div = soup.find("div", class_="spans5", string="Elevation")
        if div:
            val_div = div.find_next_sibling("div")
            elevation_text = val_div.get_text(strip=True)
            elevation_value = int(''.join(filter(str.isdigit, elevation_text)))
        else:
            return 0
        return elevation_value

    def _create_activity_cache(self):
        if not os.path.exists("data/activity_cache.json"):
            with open("data/activity_cache.json", "w") as f:
                json.dump([], f)

    def _has_cached_activity(self, activity_id: int):
        return str(activity_id) in self._get_cached_activity()

    def _get_cached_activity(self):
        self._create_activity_cache()
        with open("data/activity_cache.json", "r") as f:
            return json.load(f)
    
    def _add_cached_activity(self, activity_id: int):
        self._create_activity_cache()
        data = self._get_cached_activity()
        data.append(str(activity_id))
        with open("data/activity_cache.json", "w") as f:
            json.dump(data, f)
    
    def get_club_activities(self, club_id: int, activities: list = [], page: int | None = None):
        if page is None:
            page = int(datetime.datetime.now().timestamp())
        params = {
            "cursor": page
        }
        res = requests.get(f"https://strava.com/clubs/{club_id}/feed", params=params, headers=self._get_headers(), cookies=self._get_auth())
        activities_json = res.json()["entries"]
        get_next_page = True
        for activity in activities_json:
            try:
                is_group = False
                publish_time = datetime.datetime.fromtimestamp(activity["cursorData"]["updated_at"], tz=datetime.timezone.utc)
                now = datetime.datetime.now(tz=datetime.timezone.utc)
                if (now - publish_time).total_seconds() > UPDATE_FREQUENCY_S:
                    get_next_page = False
                    continue
                if activity["entity"] == "Activity":
                    acts = [activity["activity"]]
                else: # Assume GroupActivity so we get errors in the log
                    acts = activity["rowData"]["activities"]
                    is_group = True
                for activity in acts:
                    if is_group:
                        start_time = datetime.datetime.fromisoformat(activity["start_date"])
                    else:
                        start_time = datetime.datetime.fromisoformat(activity["startDate"])
                    start_time = publish_time
                    activity_id = activity["id"] if not is_group else activity["entity_id"]
                    if self._has_cached_activity(activity_id):
                        continue
                    times, locations, altitude = self.get_activity_info(int(activity_id))
                    elevation_gain = self.get_elevation_gain(activity_id)
                    if is_group:
                        activity = StravaActivity(
                            int(activity_id),
                            activity["activity_class_name"],
                            activity["visibility"],
                            start_time,
                            activity["elapsed_time"],
                            int(activity["athlete_id"]),
                            times,
                            locations,
                            altitude,
                            elevation_gain,
                            activity["athlete"]["sex"],
                        )
                    else:
                        activity = StravaActivity(
                            int(activity_id),
                            activity["type"],
                            activity["visibility"],
                            start_time,
                            activity["elapsedTime"],
                            int(activity["athlete"]["athleteId"]),
                            times,
                            locations,
                            altitude,
                            elevation_gain,
                            activity["athlete"]["sex"],
                        )
                    activities.append(activity)
                    self._add_cached_activity(activity_id)
            except Exception as e:
                stacktrace = "\n".join(traceback.format_exception(e))
                warnings.warn(f"Could not parse activity: {str(e)}")
                log_err(f"Could not parse activity: {str(e)}\n" + stacktrace)

        if get_next_page:
            if len(activities_json) >= 1:
                self.get_club_activities(club_id, activities, activities_json[-1]["cursorData"]["updated_at"])
        return activities

    def get_activity_info(self, activity_id: int):
        res = requests.get(f"https://www.strava.com/activities/{activity_id}/streams?stream_types[]=time&stream_types[]=latlng&stream_types[]=altitude", headers=self._get_headers(), cookies=self._get_auth())
        if not res.ok:
            self._add_cached_activity(activity_id)
            raise StravaError(f"Error when fetching activity: {res.content}. Activity id: {activity_id}")
        location_info = res.json()
        time = location_info["time"] if "time" in location_info else None
        latlng = location_info["latlng"] if "latlng" in location_info else None
        altitude = location_info["altitude"] if "altitude" in location_info else None
        return time, latlng, altitude


def save_data(org: str, data: list, week: int):
    filename = f"{org}.json"
    if not os.path.exists(filename):
        with open(filename, "w") as f:
            json.dump({}, f)

    week = str(week) # json does not support integer keys
    with open(filename, "r") as f:
        old_data = json.load(f)
    old_data[week] = data
    with open(filename, "w") as f:
        json.dump(old_data, f)

def remove_banned_athletes(athletes: list[int], data: list):
    return list(filter(lambda x: x["athlete_id"] not in athletes, data))


class Athlete(TypedDict):
    distance: int
    height: int
    org: str
    name: str
    id: int
    best_distance: int
    best_distance_activity_id: int
    picture: str
    org_pic: str
    best_height: int

class Activity(TypedDict):
    distance: int
    height: int
    athlete_id: int
    time: str

KSAT_CLUB_ID = 471480
ORBIT_CLUB_ID = 1131791

COMPETITION_START = datetime.datetime(2025, 5, 5, 0, 0, 0)
COMPETITION_END = datetime.datetime(2025, 6, 1, 0, 0, 0)
WEEK_LENGTH_SEC = 24*7*3600
MAX_MARATHON_WINNERS = 10
MAX_CUP_WINNERS = 40
MAX_HEIGHT_LIST_LENGTH = 50
MAX_DISTANCE_LIST_LENGTH = MAX_HEIGHT_LIST_LENGTH
MAX_RECENT_ACTIVITY_LIST_LENGTH = 10
MAX_LONGEST_ACTIVITY_LIST_LENGTH = 10
MAX_HIGHEST_ACTIVITY_LIST_LENGTH = 10
MIN_DISTANCE_MARATHON = 100_000 # 100km
MIN_DISTANCE_CUP = 15_000 # 15km

MAX_SINGLE_HEIGHT_LIST_LENGTH = 10
MAX_FASTEST_3K_LIST_LENGTH = 10
MAX_FASTEST_10K_LIST_LENGTH = 10

week_num = int((read_time - COMPETITION_START).total_seconds() // WEEK_LENGTH_SEC)
strava = Strava(token)

def add_org(data: list, org: str):
    for x in data:
        x["org"] = org

def update_data(banned_athletes: list[int], club_id: int, week_offset: int, org: str):
    data = strava.get_leaderboard(club_id, week_offset)
    # week_offset = 0 if week_offset else 1
    data = remove_banned_athletes(banned_athletes, data)
    add_org(data, org)
    save_data(f"data/{org}", data, week_num - week_offset)


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
    120238774, # Miriam Simers Mehus
    106271302, # Patric Andre Berthelsen
    136086572, # Mats Kvanvik
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
    25970800, # Truls Pedersen
    7585408, # Ola Ørjavik
]
org_pictures = {
    "ksat": "ksat.png",
    "orbit": "orbit.png",
}
update_leaderboard = True
if update_leaderboard:
    update_data(ksat_banned, KSAT_CLUB_ID, 0, "ksat")
    update_data(ksat_banned, KSAT_CLUB_ID, 1, "ksat")
    update_data(orbit_banned, ORBIT_CLUB_ID, 0, "orbit")
    update_data(orbit_banned, ORBIT_CLUB_ID, 1, "orbit")


def iterate_field(data, field: str):
    for x in data:
        yield x[field]

def get_stats(data: list):
    total_height = sum(iterate_field(data, "elev_gain"))
    total_distance = sum(iterate_field(data, "distance"))
    return (total_height, total_distance)

def round_list(totals: list[Athlete]):
    totals = copy.deepcopy(totals)
    for athlete in totals:
        athlete["best_distance"] = round(athlete["best_distance"] / 1000, 1)
        athlete["distance"] = round(athlete["distance"] / 1000, 1)
        athlete["height"] = int(athlete["height"])
    return totals

def finish_latest_activity(activities: list[Activity], athletes: dict[int, Athlete]):
    activities = copy.deepcopy(activities)
    for activity in activities:
        activity["distance"] = round(activity["distance"] / 1000, 1)
        activity["height"] = int(activity["height"])
        activity["athlete"] = athletes[activity["athlete_id"]]
        activity["time"] = datetime.datetime.fromisoformat(activity["time"]).strftime("%d %B %H:%M")
    return activities

def get_athlete_totals(totals: dict[int, Athlete], data: list):
    for x in data:
        athlete_id = x["athlete_id"]
        if athlete_id not in totals:
            totals[athlete_id] = {
                "distance": 0,
                "height": 0,
                "name": f'{x["athlete_firstname"]} {x["athlete_lastname"]}',
                "org": x["org"],
                "id": athlete_id,
                "best_distance": x["best_activities_distance"],
                "best_distance_activity_id": x["best_activities_distance_activity_id"],
                "picture": x["athlete_picture_url"],
                "org_pic": org_pictures[x["org"]],
            }
        athlete = totals[athlete_id]

        athlete["distance"] += x["distance"]
        athlete["height"] += x["elev_gain"]

        new_bd = x["best_activities_distance"] # bd = best distance
        old_bd = athlete["best_distance"]
        if new_bd > old_bd:
            athlete["best_distance"] = new_bd
            athlete["best_distance_activity_id"] = x["best_activities_distance_activity_id"]

def sort_by(totals: list[Athlete], field: str, reverse=False):
    longest_runs = sorted(totals, key=lambda x: x[field], reverse=not reverse)
    return longest_runs

def create_week_string(week: int, distance: float, height: float, improvement_distance: float, improvement_height: float):
    percent_distance = round(100 * (improvement_distance - 1), 1)
    percent_height = round(100 * (improvement_height - 1), 1)
    height = int(height)
    distance = round(distance / 1000, 1)
    return f"Week {week}: {distance}km ({percent_distance}%), {height}m ({percent_height}%)"

def get_stats_total(totals: list[Athlete], org: str):
    height = 0
    distance = 0
    for x in totals:
        if x["org"] != org:
            continue
        height += x["height"]
        distance += x["distance"]
    return height, distance

def calculate_new_activities(totals: dict[int, Athlete], old_totals: dict[int, Athlete]) -> list[Activity]:
    activities: list[Activity] = []
    for x in totals.values():
        if x["id"] not in old_totals:
            activities.append({
                "distance": x["distance"],
                "height": x["height"],
                "athlete_id": x["id"],
                "time": datetime.datetime.now().isoformat()
            })
            continue
        athlete = old_totals[x["id"]]
        if abs(x["distance"] - old_totals[x["id"]]["distance"]) >= 0.1:
            activities.append({
                "distance": -athlete["distance"] + x["distance"],
                "height": -athlete["height"] + x["height"],
                "athlete_id": x["id"],
                "time": datetime.datetime.now().isoformat(),
            })
    return activities

def swap_totals(totals: dict[int, Athlete]):
    totals_file = "data/totals.json"
    if not os.path.exists(totals_file):
        with open(totals_file, "w") as f:
            f.write("{}")

    with open(totals_file, "r") as f:
        old_totals = json.load(f)
    old_totals2 = {}
    for x, y in old_totals.items():
        old_totals2[int(x)] = y

    with open(totals_file, "w") as f:
        json.dump(totals, f)
    return old_totals2

def sort_date(activities: list[Activity]):
    for activity in activities:
        activity["time"] = datetime.datetime.fromisoformat(activity["time"])
    
    activities = sorted(activities, key=lambda x: x["time"], reverse=True)

    for activity in activities:
        activity["time"] = activity["time"].isoformat()
    return activities

def to_hms(time: float) -> tuple[int, int, float]:
    seconds = time % 60
    tmp = time // 60
    hours = tmp // 60
    minutes = tmp % 60
    return int(hours), int(minutes), seconds

def round_leaderboard_list(athletes):
    athletes = copy.deepcopy(athletes)
    for athlete in athletes:
        athlete["most_elevation_gain"] = int(athlete["most_elevation_gain"])

        hour, minute, second = to_hms(athlete["fastest_3k"])
        athlete["fastest_3k"] = f"{hour:02}:{minute:02}:{round(second, 1):04}"

        hour, minute, second = to_hms(athlete["fastest_10k"])
        athlete["fastest_10k"] = f"{hour:02}:{minute:02}:{round(second, 1):04}"
    return athletes


statistics = {"orbit": {}, "ksat": {}}
orbit = statistics["orbit"]
ksat = statistics["ksat"]

with open("data/orbit.json") as f:
    data_orbit = json.load(f)

with open("data/ksat.json") as f:
    data_ksat = json.load(f)

totals = {}
weeks = range(0, week_num+1)
for week in weeks:
    get_athlete_totals(totals, data_orbit[str(week)])
    get_athlete_totals(totals, data_ksat[str(week)])

# Calculate fastest 3k, 10k, most elevation in single activity
if not os.path.exists("data/leaderboard_single_activity.json"):
    with open("data/leaderboard_single_activity.json", "w") as f:
        json.dump({}, f)

with open("data/leaderboard_single_activity.json", "r") as f:
    leaderboard = json.load(f)

latest_strava_activities = strava.get_club_activities(KSAT_CLUB_ID)
latest_strava_activities += strava.get_club_activities(ORBIT_CLUB_ID)
activity: StravaActivity
for activity in latest_strava_activities:
    athlete_id = int(activity.athlete_id)
    if athlete_id not in totals:
        log_err(f"Athlete not found in totals: {athlete_id}")
        continue # Likely not in either ksat/orbit club
    if str(athlete_id) not in leaderboard:
        athlete = totals[athlete_id]
        leaderboard[str(athlete_id)] = {
            "name": athlete["name"],
            "org": athlete["org"],
            "id": athlete_id,
            "picture": athlete["picture"],
            "org_pic": athlete["org_pic"],
            "most_elevation_gain": 0,
            "most_elevation_gain_activity_id": None,
            "fastest_3k": 100000,
            "fastest_3k_activity_id": None,
            "fastest_10k": 100000,
            "fastest_10_activity_id": None,
            "time_elevation_gain": activity.start_time.strftime("%d %B %H:%M"),#datetime.datetime.now().strftime("%d %B %H:%M"),
            "time_fastest_3k": activity.start_time.strftime("%d %B %H:%M"),
            "time_fastest_10k": activity.start_time.strftime("%d %B %H:%M"),
            "gender": activity.gender,
        }
    athlete = leaderboard[str(athlete_id)]
    leaderboard[str(athlete_id)]["gender"] = activity.gender

    # Elevation
    elevation_gain = activity.get_elevation()
    if elevation_gain > athlete["most_elevation_gain"]:
        athlete["most_elevation_gain"] = elevation_gain
        athlete["most_elevation_gain_activity_id"] = activity.id
        athlete["time_elevation_gain"] = activity.start_time.strftime("%d %B %H:%M")
    
    # Fastest 3k
    fastest_3k = activity.calculate_fastest_nk(3)
    if fastest_3k is not None and fastest_3k < athlete["fastest_3k"]:
        athlete["fastest_3k"] = fastest_3k
        athlete["fastest_3k_activity_id"] = activity.id
        athlete["time_fastest_3k"] = activity.start_time.strftime("%d %B %H:%M")
    
    fastest_10k = activity.calculate_fastest_nk(10)
    if fastest_10k is not None and fastest_10k < athlete["fastest_10k"]:
        athlete["fastest_10k"] = fastest_10k
        athlete["fastest_10k_activity_id"] = activity.id
        athlete["time_fastest_10k"] = activity.start_time.strftime("%d %B %H:%M")

# Save leaderboard
with open("data/leaderboard_single_activity.json", "w") as f:
    json.dump(leaderboard, f, indent=2)


# Store activities
old_totals = swap_totals(totals)
activities = calculate_new_activities(totals, old_totals)

activities_file = "data/activities.json"
if not os.path.exists(activities_file):
    with open(activities_file, "w") as f:
        f.write("[]")

with open(activities_file, "r") as f:
    old_activities = json.load(f)

old_activities += activities

with open(activities_file, "w") as f:
    json.dump(old_activities, f)

statistics["longest_distance"] = round_list(sort_by(totals.values(), "distance")[:MAX_DISTANCE_LIST_LENGTH])
statistics["most_height"] = round_list(sort_by(totals.values(), "height")[:MAX_HEIGHT_LIST_LENGTH])
statistics["longest_single_distance"] = round_list(sort_by(totals.values(), "best_distance")[:MAX_LONGEST_ACTIVITY_LIST_LENGTH])
statistics["latest_activity"] = finish_latest_activity(sort_date(old_activities)[:10], totals)
statistics["most_single_height"] = round_leaderboard_list(sort_by(leaderboard.values(), "most_elevation_gain")[:MAX_SINGLE_HEIGHT_LIST_LENGTH])

leaderboard1 = copy.deepcopy(leaderboard)
statistics["fastest_3k"] = round_leaderboard_list(list(filter(lambda x: x["fastest_3k"] != 100000, sort_by(leaderboard1.values(), "fastest_3k", reverse=True)))[:MAX_FASTEST_3K_LIST_LENGTH])
statistics["fastest_10k"] = round_leaderboard_list(list(filter(lambda x: x["fastest_10k"] != 100000, sort_by(leaderboard1.values(), "fastest_10k", reverse=True)))[:MAX_FASTEST_10K_LIST_LENGTH])

leaderboard2 = copy.deepcopy(leaderboard)
statistics["fastest_3k_female"] = round_leaderboard_list(list(filter(lambda x: x["fastest_3k"] != 100000 and x["gender"] == "F", sort_by(leaderboard2.values(), "fastest_3k", reverse=True)))[:MAX_FASTEST_3K_LIST_LENGTH])
statistics["fastest_10k_female"] = round_leaderboard_list(list(filter(lambda x: x["fastest_10k"] != 100000 and x["gender"] == "F", sort_by(leaderboard2.values(), "fastest_10k", reverse=True)))[:MAX_FASTEST_10K_LIST_LENGTH])

leaderboard3 = copy.deepcopy(leaderboard)
statistics["fastest_3k_male"] = round_leaderboard_list(list(filter(lambda x: x["fastest_3k"] != 100000 and x["gender"] == "M", sort_by(leaderboard3.values(), "fastest_3k", reverse=True)))[:MAX_FASTEST_3K_LIST_LENGTH])
statistics["fastest_10k_male"] = round_leaderboard_list(list(filter(lambda x: x["fastest_10k"] != 100000 and x["gender"] == "M", sort_by(leaderboard3.values(), "fastest_10k", reverse=True)))[:MAX_FASTEST_10K_LIST_LENGTH])

for week0, week1 in zip(range(-1, week_num), range(0, week_num+1)):
    ksat[week1] = {"distance": {}, "height": {}}
    height0, distance0 = get_stats(data_ksat[str(week0)])
    height1, distance1 = get_stats(data_ksat[str(week1)])
    ksat[week1]["distance"]["improvement"] = distance1 / distance0
    ksat[week1]["height"]["improvement"] = height1 / height0
    ksat[week1]["distance"]["total"] = round(distance1/1000, 1)
    ksat[week1]["height"]["total"] = int(height1)
    ksat[week1]["week_string"] = create_week_string(week1, distance1, height1, distance1/distance0, height1/height0)
    ksat["distance_week"] = round(distance1/1000, 1)
    ksat["height_week"] = int(height1)

    orbit[week1] = {"distance": {}, "height": {}}
    height0, distance0 = get_stats(data_orbit[str(week0)])
    height1, distance1 = get_stats(data_orbit[str(week1)])
    orbit[week1]["distance"]["improvement"] = distance1 / distance0
    orbit[week1]["height"]["improvement"] = height1 / height0
    orbit[week1]["distance"]["total"] = round(distance1/1000, 1)
    orbit[week1]["height"]["total"] = int(height1)
    orbit[week1]["week_string"] = create_week_string(week1, distance1, height1, distance1/distance0, height1/height0)
    orbit["distance_week"] = round(distance1/1000, 1)
    orbit["height_week"] = int(height1)

height, orbit_distance = get_stats_total(totals.values(), "orbit")
orbit["distance"] = round(orbit_distance/1000, 1)
orbit["height"] = int(height)
height, ksat_distance = get_stats_total(totals.values(), "ksat")
ksat["distance"] = round(ksat_distance/1000, 1)
ksat["height"] = int(height)

# Calculate progess bar
longest = ksat_distance if ksat_distance > orbit_distance else orbit_distance
if longest == 0:
    longest = 1 # preved zero div

leading_org = "ksat" if ksat_distance > orbit_distance else "orbit"

comp_progress = (read_time - COMPETITION_START).total_seconds() / (COMPETITION_END - COMPETITION_START).total_seconds()
ksat["progress"] = (ksat_distance / longest) * comp_progress * 100
orbit["progress"] = (orbit_distance / longest) * comp_progress * 100

statistics["weeks"] = [str(x) for x in range(0, week_num + 1)]

with open("data/stats.json", "w") as f:
    json.dump(statistics, f, indent=2)
