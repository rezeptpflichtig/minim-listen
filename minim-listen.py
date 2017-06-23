#!/usr/local/bin/env python3

from pygtail import Pygtail
import mutagen, time, re, requests, json

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
                            trackmetadata = readtags(fp) # read metadata
                            listen = write_listen(trackmetadata)
                            send_listen(listen)
                            time.sleep(0.5) # decrease cpu load
                        oldtime = nowtime
                prevline = line
    except KeyboardInterrupt:
        pass

def readtags(fp):
    '''Extract relevant Metainformation via mutagen'''
    f = mutagen.File(fp)
    # list of tags to query
    tagsflac_basic = {
                'artist_name': 'artist',
                'track_name': 'title',
                'release_name': 'album'}
    tagsflac_additional = {
                'release_mbid': 'musicbrainz_albumid',
                'recording_mbid': 'musicbrainz_trackid',
                'artist_mbids': 'musicbrainz_artistid',
                'rating': 'rating'}
    tagsmp3_basic =  {
                'artist_name': 'TPE1',
                'track_name': 'TIT2',
                'release_name': 'TALB'}
    tagsmp3_additional = {
                'release_mbid': 'TXXX:MusicBrainz Album Id',
                'recording_mbid': 'TXXX:MusicBrainz Release Track Id',
                'artist_mbids': 'TXXX:MusicBrainz Artist Id',
                'rating': 'TXXX:rating'}
    trackmetadata = {'additional_info': {}}
    if f.__class__.__name__ == 'FLAC':
        for i in tagsflac_basic:
            if tagsflac_basic[i] in f:
                trackmetadata[i] = f[tagsflac_basic[i]][0]
        for i in tagsflac_additional:
            if tagsflac_additional[i] in f:
                if i == 'artist_mbids':
                    trackmetadata['additional_info'][i] = f[tagsflac_additional[i]]
                else:
                    trackmetadata['additional_info'][i] = f[tagsflac_additional[i]][0]
    elif f.__class__.__name__ == 'MP3':
        for i in tagsflac_basic:
            if tagsmp3_basic[i] in f:
                trackmetadata[i] = f[tagsmp3_basic[i]][0]
        for i in tagsmp3_additional:
            if tagsmp3_additional[i] in f:
                if i == 'artist_mbids':
                    trackmetadata['additional_info'][i] = f[tagsmp3_additional[i]].text
                else:
                    trackmetadata['additional_info'][i] = f[tagsmp3_additional[i]][0]
    return trackmetadata

def write_listen(tm):
    listen = {
               'listen_type': 'single',
               'payload': [
                 {
                   'listened_at': int(time.time()),
                   'track_metadata': tm
                 }
               ]
             }
    pprint.pprint(listen) #debug
    return listen

def send_listen(listen):
    url = 'https://api.listenbrainz.org/1/submit-listens'
    headers = {'content-type': 'application/json', 'Authorization': 'token ' + lbtoken}
    r = requests.post(url, data=json.dumps(listen), headers=headers)
    print(r.status_code, r.reason, r.text)

logtail()
