#!/usr/local/bin/env python3

from pygtail import Pygtail
import mutagen, time, re, subprocess, requests, json

#path to you library
path = '/media/archiv/'

# the verbose logfile from minimserver
minimlog = '/media/minimserver.log'

#Your listenbrainz token
lbtoken = 'YOURTOKEN'

def logtail():
    prevline = ''
    lasthit = ''
    oldtime = 0
    pattern = re.compile('(Content-Type: audio)')
    pattern2 = re.compile('(?<=from file ).*')
    try:
        for line in Pygtail(minimlog):
            # go o end of logfile
            pass
        while True:
            # poll the logfile
            time.sleep(0.5) # decrease cpu load
            for line in Pygtail(minimlog):
                hit2 = re.search(pattern, prevline) # check if "Contentype: audio" is present in the previous line
                if hit2:
                    hit1 = re.search(pattern2, line) # match the filename that was served
                    if hit1:
                        nowtime = time.time()
                        file = hit1.group(0)
                        #print(file) # verbose debug
                        if (file == lasthit) and (nowtime - oldtime < 59):
                            # if the filename is the same as the last one, check how much time has passed; if a minute it is and it was less than a minute ago, pass on that one
                            pass
                        else:
                            lasthit = file
                            fp = path + file.rstrip() # assemble the full path to the file
                            print(fp) #verbose
                            readtags(fp) # pass to mutagen
                            time.sleep(0.5) # decrease cpu load
                        oldtime = nowtime
                prevline = line
    except KeyboardInterrupt:
        pass

def readtags(fp):
    '''Extract relevant Metainformation via mutagen'''
    f = mutagen.File(fp)
    if f.__class__.__name__ == 'FLAC':
        artistname = f["artist"][0]
        trackname = f["title"][0]
        releasename = f["album"][0]
        releasembid = f["musicbrainz_albumid"][0]
        recordingmbid = f["musicbrainz_trackid"][0]
        artistmbids = f["musicbrainz_artistid"]
    elif f.__class__.__name__ == 'MP3':
        artistname = f["TPE1"][0]   # Trackartist
        trackname = f["TIT2"][0]    # Trackname
        releasename = f["TALB"][0]  # Release Name
        releasembid = f["TXXX:MusicBrainz Album Id"][0]
        recordingmbid = f["TXXX:MusicBrainz Release Track Id"][0]
        artistmbids = f["TXXX:MusicBrainz Artist Id"].text
    write_listen(artistname,trackname,releasename,releasembid,recordingmbid,artistmbids)

def write_listen(artistname,trackname,releasename,releasembid,recordingmbid,artistmbids):
    '''Write a JSON blob. This could be probably done better with creating a json object instead of glueing together a str'''
    listen = ('{\n'
              '  "listen_type": "single",\n'
              '  "payload": [\n'
              '    {\n'
              '      "listened_at": ' + str((int(time.time()))) + ',\n'
              '      "track_metadata": {\n'
              '        "additional_info": {\n'
              '          "release_mbid": "' + releasembid  + '",\n'
              '          "artist_mbids": [\n')
    if isinstance(artistmbids,str):
        listen = (listen + ''
              '            "' + artistmbids[0] + '"\n')
    elif isinstance(artistmbids,list): # if multiple artistmbids present, omit the last comma
        for i in artistmbids[:-1]:
            listen = (listen + '            "' + i + '",\n')
        listen = (listen + '            "' + artistmbids[-1] + '"\n')
    listen = (listen + ''
              '          ],\n'
              '          "recording_mbid": "' + recordingmbid + '"\n'
              '        },\n'
              '        "artist_name": "' + artistname + '",\n'
              '        "track_name": "' + trackname + '",\n'
              '        "release_name": "' + releasename + '"\n'
              '      }\n'
              '    }\n'
              '  ]\n'
              '}')
    print('')     # verbose
    print(listen) # verbose
    send_listen(listen)

def send_listen(listen):
    url = 'https://api.listenbrainz.org/1/submit-listens'
    payload = json.loads(listen)
    headers = {'content-type': 'application/json', 'Authorization': 'token ' + lbtoken}
    r = requests.post(url, data=json.dumps(payload), headers=headers)
    print(r.status_code, r.reason, r.text)

logtail()
