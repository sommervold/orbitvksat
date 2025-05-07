This page is a quick and dirty webpage for showing statistics for the 2025 Orbit VS KSAT running competition.

The script "update_leaderboard.py" fetches data from the two clubs, and generates top-lists in various categories.

It is currently hosted on https://strava.orbitntnu.com/, and is updated every 10 minutes.

To run the script yourself, you need to create a file called "token.txt", and insert the _strava4_token cookie from strava's webpage.
It runs on scraping instead of the API because the API lacks essential information without athlete consent, making the project unfeasable.
