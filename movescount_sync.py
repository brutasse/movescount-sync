import argparse
import getpass
import http.client
import json
import logging
import os
import pickle
import time

import requests

CFG = os.path.join(os.path.expanduser('~'), '.config', 'movescount-sync')
SESSION_PATH = os.path.join(CFG, 'session.pickle')
FORMATS = {'kml', 'gpx', 'xlsx', 'fit', 'tcx'}
CONFIG_FILE = os.path.join(CFG, 'movescount.json')

# https://techblog.willshouse.com/2012/01/03/most-common-user-agents/
MOST_COMMON_UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                  'AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/55.0.2883.87 Safari/537.36')


class Urls:
    overview = 'http://www.movescount.com/overview'
    login = 'https://servicegate.suunto.com/UserAuthorityService/'
    token = 'https://www.movescount.com/services/UserAuthenticated'
    login_referer = 'https://www.movescount.com/auth?redirect_uri=%2foverview'
    export = 'http://www.movescount.com/move/export'


def enable_debug():
    http.client.HTTPConnection.debuglevel = 1
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    requests_log = logging.getLogger("requests.packages.urllib3")
    requests_log.setLevel(logging.DEBUG)
    requests_log.propagate = True


def get_session():
    if not os.path.exists(SESSION_PATH):
        return requests.Session()
    with open(SESSION_PATH, 'rb') as f:
        return pickle.load(f)


def save_session(s):
    with open(SESSION_PATH, 'wb') as f:
        pickle.dump(s, f)


def all_valid(formats):
    return all([f in FORMATS for f in formats])


def configure(force=False):
    os.makedirs(CFG, exist_ok=True)
    if not os.path.exists(CONFIG_FILE) or force:
        email = input('Movescount.com email address: ')
        password = getpass.getpass()
        formats = []
        while not formats:
            save_formats = input("Formats to fetch, space-separated "
                                 "(available: {}): ".format(
                                     ", ".join(sorted(FORMATS)))).split()
            formats = save_formats if all_valid(save_formats) else []
            if not formats:
                print("Unable to recognize formats. Please try again.")
        default_data_dir = os.path.join(os.path.expanduser('~'),
                                        'Documents', 'Movescount')
        data_dir = input(f"Data storage path (default: {default_data_dir}): ")
        data_dir = data_dir or default_data_dir
        os.makedirs(data_dir, exist_ok=True)
        with open(CONFIG_FILE, 'w') as f:
            print(f"Storing configuration in {CONFIG_FILE}")
            f.write(json.dumps({
                'email': email,
                'password': password,
                'formats': formats,
                'data_dir': data_dir,
            }, sort_keys=True, indent=4))
    with open(CONFIG_FILE, 'r') as f:
        return json.loads(f.read())


def login(session, email, password):
    print("Logging in…")
    ts = int(time.time() * 1000)
    response = session.get(Urls.login, params={
        'callback': f'jQuery18104619530053417804_{ts}',
        'service': 'Movescount',
        'emailAddress': email,
        'password': password,
        '_': ts + 27314,
    }, headers={'Referer': Urls.login_referer})
    response.raise_for_status()
    token = response.text.split('"')[1]
    response = session.post(Urls.token, json={'token': token,
                                              'utcOffset': '60',
                                              'redirectUri': '/overview'})
    response.raise_for_status()


def fetch_move(session, move, formats, destination):
    if not move['eventObjectType'] == 'move':
        print(f"Skipping event {move['eventObjectId']}, type "
              f"{move['eventObjectType']}")
        return
    event_id = move['eventObjectId']
    base_path = os.path.join(destination, move['eventCreated'])
    json_path = f'{base_path}.json'
    if not os.path.exists(json_path):
        print(f"Writing {json_path}")
        with open(json_path, 'w') as f:
            f.write(json.dumps(move))
    for format in formats:
        format_path = f'{base_path}.{format}'
        if not os.path.exists(format_path):
            print(f"Fetching {format.upper()} for {event_id}")
            resp = session.get(Urls.export, params={'id': event_id,
                                                    'format': format})
            resp.raise_for_status()
            print(f"Writing {format_path}")
            with open(format_path, 'wb') as f:
                f.write(resp.content)


def get_moves(session, email, password, formats, destination, recurse=False):
    response = session.get(Urls.overview)
    if '/auth' in response.url:
        login(session, email, password)
        response = session.get(Urls.overview)

    data = response.text.split(
        'mc.OverviewPage.default.main(')[1].split(');')[0]
    config = json.loads(data)['activityFeed']
    print(f"Fetching activity feed for {config['targetUsername']}")

    url = config['feeds']['me']['id']
    token = config['token']
    empty = False
    moves = []
    while not empty:
        feed_url = '{}/{}'.format(config['url'], url)
        print(f"Fetching feed {url}")
        response = session.get(feed_url, params={'token': token})
        data = response.json()
        moves.extend(data['objects'][1:-1])
        empty = len(data['objects']) == 2 or not recurse
        url = data['objects'][-1]['url']

    for move in moves:
        fetch_move(session, move, formats, destination)


def main():
    parser = argparse.ArgumentParser(
        description='Fetch moves from movescount.com')
    parser.add_argument('--debug', dest='debug', action='store_true',
                        default=False, help='Verbose debugging output')
    parser.add_argument(
        '--recursive', dest='recursive', action='store_true', default=False,
        help=('Recursive mode: fetch entire event stream instead of '
              'stopping at first page.'))
    parser.add_argument(
        '--configure', dest='configure', action='store_true', default=False,
        help='Setup movescount-sync configuration options.')
    args = parser.parse_args()
    if args.debug:
        enable_debug()
    config = configure(force=args.configure)
    try:
        session = get_session()
        session.headers['User-Agent'] = MOST_COMMON_UA
        get_moves(session, config['email'], config['password'],
                  config['formats'], config['data_dir'], args.recursive)
    finally:
        save_session(session)
    print("All done.")


if __name__ == '__main__':
    main()
