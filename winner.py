import json
import random

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


# choose weekly gift-card winners
WEEK_NUM = 2
NUM_WINNERS = 2
WINNING_TEAM = "orbit"
#WINNING_TEAM = "ksat"

with open(f"data/{WEEK_NUM}.json") as f:
    data = json.load(f)

with open("data/compensation.json") as f:
    compensation = json.load(f)

total_tickets = 0
entries = []
for athlete in data[WINNING_TEAM]:
    if athlete["athlete_id"] in orbit_banned and WINNING_TEAM == "orbit":
        continue
    if athlete["athlete_id"] in ksat_banned and WINNING_TEAM == "ksat":
        continue

    for activity in compensation[WINNING_TEAM]:
        if activity["athlete_id"] == athlete["athlete_id"]:
            athlete["distance"] += activity["distance"]

    tickets = int(round(athlete["distance"], 0))
    total_tickets += tickets
    name = f"{athlete['athlete_firstname']} {athlete['athlete_lastname']}"
    entries.append((total_tickets, tickets, athlete["athlete_id"], name))

winners = []
while len(winners) < NUM_WINNERS:
    winner = random.randint(1, total_tickets)

    for entry in entries:
        if entry[0] >= winner:
            if entry in winners:
                break # cannot win twice.
            winners.append(entry)
            break


print(" ---- ENTRIES ---- ")
for entry in entries:
    print(f"{entry[3]} - {100*entry[1]/total_tickets:.1f}%")

print("\n ---- WINNERS ---- ")
for winner in winners:
    print(f"{winner[3]} - {100*winner[1]/total_tickets:.1f}%")
