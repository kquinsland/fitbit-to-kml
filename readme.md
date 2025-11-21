<!-- omit from toc -->
# Fitbit To KML

A small collection of tools for exporting FitBit workout data and converting it to KML format.
These tools were [vibe-coded](https://simonwillison.net/2025/Oct/7/vibe-engineering/) over a few evenings to scratch a personal itch.
They work for me on my machine but are provided as-is without warranty or support.

- [Overview](#overview)
  - [A word on authentication](#a-word-on-authentication)
  - [Set up Python](#set-up-python)
- [`get-auth.py`](#get-authpy)
- [`dump-activities.py`](#dump-activitiespy)
- [`download-tcx.py`](#download-tcxpy)
- [`tcx-to-kml.py`](#tcx-to-kmlpy)
- [`merge-kml.py`](#merge-kmlpy)

## Overview

There are a few tools in this repo.
Listed in general order of use:

1. `get-auth.py` - OAuth2 authentication helper to get access tokens for the FitBit API
2. `dump-activities.py` - Download all recorded activities from the FitBit API as JSON files
3. `download-tcx.py` - Download TCX files for activities that have GPS data
4. `tcx-to-kml.py` - Convert TCX files to KML format
5. `merge-kml.py` - Combine many KML exports into a single file

Most tools feature a `--help` flag to show usage information but ship with sane defaults.

But before you can use any of these tools you'll need to set up authentication and a python environment.

### A word on authentication

All of the tools that access the FitBit API require OAuth2 authentication.
See [docs/auth.md](docs/auth.md) for instructions on setting up a FitBit personal application and obtaining API credentials.
You will not be able to use these tools without going through that process first.

> [!WARNING]
> The API credentials you obtain are sensitive and should be kept secret.
> Anyone with access to these credentials can access your Fitbit data.
> The tools in this repo are intended for personal use only do not take extreme care to protect your credentials; they are stored in a `tokens.json` file in plain text.
> Do not share this file or commit it to version control.
> Delete the file when you are done using these tools.

### Set up Python

These tools are written to target python 3.14. They may work with earlier versions but have not been tested.
They were written and run on Linux and macOS; not tested on Windows.

It's recommended to use [`uv`](https://docs.astral.sh/uv/) or any other virtual environment manager to create an isolated environment.

Assuming your venv manager of choice knows how to parse the [`pyproject.toml`](pyproject.toml) file all you'll need to do is:

```shell
# Make a new virtual environment and activate it
❯ uv venv
Using CPython 3.14.0
Creating virtual environment at: .venv
Activate with: source .venv/bin/activate
❯ source .venv/bin/activate
# Then install dependencies:
❯ uv sync
Resolved 28 packages in 0.59ms
Installed 26 packages in 44ms
 + attrs==25.4.0
 + binapy==0.8.0
 + certifi==2025.10.5
 + cffi==2.0.0
 + charset-normalizer==3.4.4
 + cryptography==46.0.3
 + furl==2.1.4
 + idna==3.11
 + iniconfig==2.3.0
 + jwskate==0.12.2
 + lxml==6.0.2
 + orderedmultidict==1.0.1
 + packaging==25.0
 + pluggy==1.6.0
 + pycparser==2.23
 + pygments==2.19.2
 + pytest==9.0.0
 + python-dateutil==2.9.0.post0
 + python-tcxparser==2.4.0
 + requests==2.32.5
 + requests-oauth2client==1.7.0
 + simplekml==1.3.6
 + six==1.17.0
 + structlog==25.5.0
 + typing-extensions==4.15.0
 + urllib3==2.5.0
```

## `get-auth.py`

_After_ [obtaining your FitBit API credentials](#a-word-on-authentication), you can use the `get-auth.py` script to perform the OAuth2 flow and obtain access tokens.

The credentials should be passed to the script via environment variables either with a tool like [`direnv`](https://direnv.net/) or manually:

```shell
export FB_CLIENT_ID="your_client_id"
export FB_CLIENT_SECRET="your_client_secret"
```

Then run the script to facilitate the OAuth2 flow.
It will prompt you to visit a URL to authorize the application, then paste back the redirected URL to complete the process.

```shell
❯ ./get-auth.py --help
2025-11-15T18:05:28.110025Z [info     ] Starting FitBit OAuth2 Flow Helper
2025-11-15T18:05:28.110091Z [info     ] Using configuration            client_id=23TNWP... redirect_uri=https://localhost:8080/callback scopes=['activity', 'location', 'profile']
2025-11-15T18:05:28.110126Z [info     ] Creating FitBit OAuth2 client  authorization_endpoint=https://www.fitbit.com/oauth2/authorize token_endpoint=https://api.fitbit.com/oauth2/token
2025-11-15T18:05:28.110595Z [info     ] Generating authorization request

================================================================================
STEP 1: Visit the following URL to authorize the application:
================================================================================

https://www.fitbit.com/oauth2/authorize?client_id=23TNWP&redirect_uri=https%3A%2F%2Flocalhost%3A8080%2Fcallback&scope=activity+location+profile&response_type=code&state=Bi995-UNM-CMDdTXPX2iCyiaDhaoU2PvRFj1JSfonmU&code_challenge_method=S256&code_challenge=xSs0xsSBtbzWtGtt0r3mBdtU6FSAyelAVtRUa_Ymg_8

================================================================================

STEP 2: After authorizing, you'll be redirected to a URL which may display an error in the browser.
Copy the entire URL from your browser and paste it here.

Paste the callback URL here: https://localhost:8080/callback?code=d39920b62838a25c938917ad43d549bd8880bad5&state=Bi995-UNM-CMDdTXPX2iCyiaDhaoU2PvRFj1JSfonmU#_=_
2025-11-15T18:06:09.294097Z [info     ] Parsing callback URL
2025-11-15T18:06:09.294242Z [info     ] Authorization code received    code=d39920b628...
2025-11-15T18:06:09.294285Z [info     ] Exchanging authorization code for access token
2025-11-15T18:06:09.294309Z [debug    ] Exchanging code                code=d39920b62838a25c938917ad43d549bd8880bad5 redirect_uri=https://localhost:8080/callback verify=IY_th-oUHzuP4ya6VZ6svqPGBb2xAgAPC3CSOholsJLBwrmwqZN_LGYE9_J2XPupVEL5pT5L5LZgpBxeCyi-KXMvwpYxEXejzhFLIfQcf_zdDbiYkz4hYV25HGBHG8h0
2025-11-15T18:06:09.515247Z [info     ] Access token received successfully expires_in=28800 scope='location profile activity' token_type=Bearer

================================================================================
SUCCESS! Access token received:
================================================================================

Access Token: eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiIyM1ROV1AiLCJzdWIiOiI1M1M5R1kiLCJpc3MiOiJGaXRiaXQiLCJ0eXAiOiJhY2Nlc3NfdG9rZW4iLCJzY29wZXMiOiJybG9jIHJhY3QgcnBybyIsImV4cCI6MTc2MzI1ODc2OSwiaWF0IjoxNzYzMjI5OTY5fQ._N6G8GhcfnZBCSGUnCYr8svvgAgdDsIE1nesOWqWbko
Token Type: Bearer
Expires In: 28800 seconds
Scope: location profile activity
Refresh Token: 546dc920b0578459d06e3f9f93e25a579277048bfa2a4c6ab2690b15139afc3e

================================================================================
2025-11-15T18:06:09.515645Z [info     ] Saved token response to disk   path=tokens.json
```

At this point, you will have a `tokens.json` file containing the access and refresh tokens needed to access the FitBit API.

## `dump-activities.py`

With tokens obtained, the next step is to download all recorded activities from the FitBit API as JSON files.

> [!NOTE]
>This may take a while if you have a large number of activities recorded.
> Do not interrupt the process unless necessary.
> After everything has been fetched, it will write out the individual activities into monthly buckets.

```shell
❯ ./dump-activities.py
2025-11-15 10:33:13 [info     ] loading_tokens                 path=tokens.json
2025-11-15 10:33:15 [info     ] fetched_activities_page        fetched=100 page=1
<...>
2025-11-15 10:35:20 [info     ] fetched_activities_page        fetched=15 page=69
2025-11-15 10:35:20 [info     ] dump_complete                  months=420 output=data/fitbit_activities requests=69 skipped=0 total=69420
```

Next, get the individual TCX files for activities that have GPS data.

## `download-tcx.py`

It seems that FitBit has _aggressive_ rate limiting on TCX downloads, so this script is designed to be interruptible and resumable.
Be prepared to leave it running for a while to get all your data.

```shell
❯ ./download-tcx.py
2025-11-15 10:40:20 [info     ] tcx_plan_created               entries=69420 path=data/tcx-files.json
2025-11-15 10:40:20 [info     ] tcx_downloaded                 link=https://api.fitbit.com/1/user/-/activities/01234567890123456789.tcx target=data/fitbit_activities/1984/04_01234567890123456789.tcx
<...>
2025-11-15 10:40:32 [warning  ] fitbit_rate_limited            attempt=1 url=https://api.fitbit.com/1/user/-/activities/987654321987654321.tcx wait_hhmm=00:28:27 wait_seconds=1707.0
```

If interrupted, there is a "plan file" that records which TCX files have been downloaded and which are still pending. This allows you to resume the download later without starting over if you can't leave the script running for an extended period.

```shell
❯ ./download-tcx.py
2025-11-15 10:47:08 [info     ] tcx_plan_loaded                entries=69420 path=data/tcx-files.json
2025-11-15 10:47:08 [info     ] tcx_resume_progress            on_disk=15 remaining=69405 total=69420
2025-11-15 10:47:09 [info     ] tcx_downloaded                 link=https://api.fitbit.com/1/user/-/activities/1234567890987654321.tcx target=data/fitbit_activities/1984/02_1234567890987654321.tcx
2025-11-15 10:47:09 [warning  ] fitbit_rate_limited            attempt=1 url=https://api.fitbit.com/1/user/-/activities/09876543212345678901.tcx wait_hhmm=00:21:50 wait_seconds=1310.0
```

Eventually, you'll have all your non-empty TCX files downloaded.

## `tcx-to-kml.py`

Finally, you can convert the downloaded TCX files to KML format for use in mapping applications.

```shell
❯ ./tcx-to-kml.py --in-dir ./data/fitbit_activities --out-dir ./data/kml
<....>
2025-11-15 11:22:55 [info     ] Successfully converted TCX to KML input_file=data/fitbit_activities/2025/11_1234567890987654321.tcx laps=0 output_file=data/kml/2025/11_1234567890987654321.kml points=7934
✓ Converted 2025/11_1234567890987654321.tcx -> 2025/11_1234567890987654321.kml

==================================================
Conversion Statistics
==================================================
Total files processed: 69420
Successful conversions: 69420
Failed conversions: 0
Total GPS points: 69420000
Total laps: 0
Average points per file: 255.0
Average laps per file: 0.0
```

## `merge-kml.py`

After generating plenty of KML tracks with `tcx-to-kml.py`, you can consolidate them into a single if needed.

```shell
❯ ./merge-kml.py --in-dir ./data/kml/2021
2025-11-18 20:01:24 [info     ] Merged KML files               files=45 output=data/kml/2021/MERGED.kml placemarks=69 points=123456
Merged 69 files into data/kml/2021/MERGED.kml
  Placemarks: 45
  Points: 123456

```
