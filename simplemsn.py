from ast import While
import requests
from urllib import parse
from datetime import datetime,timedelta,date
import os.path , os
import json,time

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Load configuration from JSON file
with open('config.json', 'r') as config_file:
    config = json.load(config_file)

os.chdir('LOCALFOLD')

# Access configuration values
tenantid = config['tenantid']
clientid = config['clientid']
APIend = config['APIend']
clientsec = config['clientsec']
reduri = config['reduri']
scope = config['scope']
egraphurl = config['egraphurl']
graphurl = config['graphurl']
msauth_url = config['msauth_url']
mstok_url = config['mstok_url']
mstoken_file = config['mstoken_file']
gtoken_file = config['gtoken_file']

def msnauth():
    if os.path.exists(mstoken_file):
        with open(mstoken_file) as json_file:
            creds = json.load(json_file)
    else:
        with open(mstoken_file, 'w') as f:
            print('Enter this URL in browser to authunticate and paste result URL here:')
            print(msauth_url)
            resurl = input()
            if parse.parse_qs(parse.urlparse(resurl).query)['code'][0]:
                code = parse.parse_qs(parse.urlparse(resurl).query)['code'][0]
            payload = {'client_id':clientid,
            'scope':scope,
            'code':code,
            'redirect_uri':reduri,
            'grant_type':'authorization_code',
            'client_secret':clientsec}
            creds = requests.post(mstok_url,data=payload).json()
            f.write(json.dumps(creds))
    global mstoken
    global msrtoken
    mstoken = creds['access_token']
    msrtoken = creds['refresh_token']
    print("MSN Authunticated !!!")

def refresh_credentials(rtoken):
    data = {'grant_type': 'refresh_token',
    'refresh_token': rtoken,
    'client_id': clientid,
    'client_secret': clientsec}
    response = requests.post(mstok_url, data=data)
    creds = response.json()
    with open(mstoken_file, 'w') as f:
        f.write(json.dumps(response.json()))
    global mstoken
    global msrtoken
    mstoken = creds['access_token']
    msrtoken = creds['refresh_token']
    print("MSN Authuntication refreshed !!!")

def getmsncal(start,end):
    count = 1000
    global headers
    headers = {'Authorization': 'Bearer '+ mstoken,
    'Host': 'graph.microsoft.com',
    'Prefer': 'outlook.timezone="Asia/Dubai"'}
    from backports.zoneinfo import ZoneInfo
    import urllib.parse
    loczone = ZoneInfo('Asia/Dubai')
    startfilter = datetime.combine(date.today() ,datetime.min.time()) + timedelta(days=start)
    endfilter = datetime.combine(date.today() ,datetime.min.time()) + timedelta(days=end)
    print(f'\nMSN Start Date: {startfilter}')
    print(f'MSN END Date: {endfilter}')
    payload = {
        'startDateTime': startfilter.replace(tzinfo=loczone).isoformat(), 
        'endDateTime': endfilter.replace(tzinfo=loczone).isoformat()
    }
    msnurl = graphurl +f"?top={count}&orderby=start/dateTime&format=json&select=subject,start,end&"+ urllib.parse.urlencode(payload)
    res = requests.get(msnurl, headers = headers)
    while res.status_code != 200:
            refresh_credentials(msrtoken)
            headers['Authorization'] = 'Bearer '+ mstoken
            res = requests.get(msnurl, headers = headers)
    print("MSN events collected !!")
    return res.json()['value']
    
def authgoog():
    SCOPES = ['https://www.googleapis.com/auth/calendar']
    creds = None
    if os.path.exists(gtoken_file):
        creds = Credentials.from_authorized_user_file(gtoken_file, SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(gtoken_file, 'w') as token:
            token.write(creds.to_json())
    print("Google Authunticated")
    return creds

def getgoog(start,end):
    global gservice
    gservice = build('calendar', 'v3', credentials=googcreds)
    now = (datetime.combine(date.today() ,datetime.min.time())+ timedelta(days=start)).isoformat() + 'Z'  # 'Z' indicates UTC time
    later = (datetime.combine(date.today() ,datetime.min.time()) + timedelta(days=end)).isoformat() + 'Z'  # 'Z' indicates UTC time
    print(f'\nABC Start Date: {now}')
    print(f'ABC End Date: {later}')
    events_result = gservice.events().list(calendarId='primary', timeMin=now, timeMax=later,
                                            maxResults=1000, singleEvents=True,
                                            orderBy='startTime').execute()
    events = events_result.get('items', [])
    print("Google Events Collected")
    if not events:
        print('No upcoming events found.')
    return events

def putmsn(start,end,id):
    payload = {
    "subject": 'Overlap ' + id,
    "start": {
        "dateTime": start.partition("+")[0],
        "timeZone": "Asia/Dubai"
    },
    "end": {
        "dateTime": end.partition("+")[0],
        "timeZone": "Asia/Dubai"
    },
    "categories" : ['Red category'],
    }
    res = requests.post(egraphurl,headers=headers ,json=payload)
    print(res.status_code, " ==> Creating ABC Event in MSN at " + start)
    while res.status_code != 201:
            refresh_credentials(msrtoken)
            headers['Authorization'] = 'Bearer '+ mstoken
            res = requests.get(egraphurl, headers = headers)
            print(res.status_code)

def putgoog(start,end,id):
    start = datetime.strptime(start[:-8], "%Y-%m-%dT%H:%M:%S").isoformat()+"+04:00"
    end = datetime.strptime(end[:-8], "%Y-%m-%dT%H:%M:%S").isoformat()+"+04:00"
    event = {
        'summary': 'OFFLINE',
        'description': 'OFFLLAP ' + id,
        'start': {
        'dateTime': start,
        'timeZone': 'Asia/Dubai',
        },
        'end': {
        'dateTime': end,
        'timeZone': 'Asia/Dubai',
        },
        'colorId': '8',
        }
    gservice.events().insert(calendarId='primary', body=event).execute()
    print("Gooood ==> Creating XYZ Event in Google at " + start)

def ABC_to_o365():
#Get MSN list and creat ban list
    for event in gABClist:
        if event['id'] not in msABClist:
            if 'dateTime' in event['start']:
                putmsn(event['start']['dateTime'],event['end']['dateTime'],event['id'])
            elif 'date' in event['start']:
                print('=====>> False event: '+ event['summary'] + ' == at == ' + event['start']['date'])
        elif event['id'] in msABClist:
            #check time match
            gtime = datetime.strptime(event['start']['dateTime'], "%Y-%m-%dT%H:%M:%S%z").replace(tzinfo=None)
            mtime = datetime.strptime(requests.get(egraphurl + f"?select=subject,start&filter=contains(subject,'{event['id']}')", headers = headers).json()['value'][0]['start']['dateTime'][:-8], "%Y-%m-%dT%H:%M:%S")
            if mtime == gtime:
                while event['id'] in msABClist: msABClist.remove(event['id'])
    for i in msABClist:
        delid = requests.get(egraphurl + f"?select=id&filter=contains(subject,'{i}')", headers = headers).json()['value'][0]['id']
        delevent = requests.delete('https://graph.microsoft.com/v1.0/me/events/'+delid, headers = headers)
        print(delevent.status_code, " ==> Deleteing ABC Event from MSN")

def o365_to_ABC():
#Get MSN list and creat ban list
    for event in msXYZlist:
        if event['id'] not in gXYZlist:
            putgoog(event['start']['dateTime'],event['end']['dateTime'],event['id'])
        elif event['id'] in gXYZlist:
            #check time match
            mtime = event['start']['dateTime'][:19]
            pulled = gservice.events().list(calendarId='primary',q=event['id']).execute()
            if  pulled['items']:
                gtime = gservice.events().list(calendarId='primary',q=event['id']).execute()['items'][0]['start']['dateTime'][:19]
                if mtime == gtime:
                    while event['id'] in gXYZlist: gXYZlist.remove(event['id'])
    for i in gXYZlist:
        items = gservice.events().list(calendarId='primary',q=i).execute()['items']
        if items:
            id = items[0]['id']
            gservice.events().delete(calendarId='primary', eventId=id).execute()
            print("Gooood ==> Removing XYZ Event from Google")

def bildlst(a,b):
    msnlist  = getmsncal(a,b)
    googlist  = getgoog(a,b)
    try:
        msABClist = []
        msXYZlist = []
        gABClist = []
        gXYZlist = []
        for i in msnlist:
            if 'Overlap' in i['subject']:
                msABClist.append(i['subject'].split(' ')[1])
            else:
                msXYZlist.append(i)
        for j in googlist:
            if 'description' in j:
                if 'OFFLLAP' == j['description'].split(' ')[0]:
                    gXYZlist.append(j['description'].split(' ')[1])
                else:
                    gABClist.append({'id': j['id'],'summary': j['summary'], 'start': j['start'],'end': j['end']})
            else:
                gABClist.append(j)
        return msABClist,msXYZlist,gABClist,gXYZlist
    except:
        print('collection failure')
        return False

msnauth()
googcreds = authgoog()

#while True:
msABClist,msXYZlist,gABClist,gXYZlist = bildlst(0,28)
print('\nStartting ABC to MSN at ',datetime.now())
ABC_to_o365()
print('\nStartting MSN to ABC at ',datetime.now())
o365_to_ABC()
print('\n',30*'#','\nEnd of Sync Cycle at ',datetime.now(),'\n',30*'#')

#Start Clean up
print('\n### Start Cleaning Cycle ### ',datetime.now())
msABClist,msXYZlist,gABClist,gXYZlist = bildlst(-15,0)
while len(msABClist) != 0:
    for i in msABClist:
        delid = requests.get(egraphurl + f"?select=id&filter=contains(subject,'{i}')", headers = headers).json()['value'][0]['id']
        delevent = requests.delete('https://graph.microsoft.com/v1.0/me/events/'+delid, headers = headers)
        print(delevent.status_code, " ==> Deleteing ABC Event from MSN")
        msABClist.remove(i)
while len(gXYZlist) != 0:
    for i in gXYZlist:
        items = gservice.events().list(calendarId='primary',singleEvents=True,q=i).execute()['items']
        while items:
            id = items[0]['id']
            gservice.events().delete(calendarId='primary', eventId=id).execute()
            items.pop(0)
            print("Gooood ==> Removing XYZ Event from Google")
        gXYZlist.remove(i)
print('\n### END Cleaning Cycle ### ',datetime.now())
print(30*'\/')
#time.sleep(10800)

'''
pip install requests
pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib
#pip install --upgrade google-cloud-storage
pip3 install zoneinfo

'''
