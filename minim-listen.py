#!/usr/local/bin/env python3

from pygtail import Pygtail
import mutagen, time, re, requests, json, pprint, configparser

cfg = configparser.ConfigParser()
cfg.read('config.ini')

def logtail():
    prev_line = ''
    prev_listen = ''
    lasthit = ''
    oldtime = 0
    pattern = re.compile('(Content-Type: audio)')
    pattern2 = re.compile('(?<=from file ).*')
    minimlog = cfg['DEFAULT']['minimlog']
    path = cfg['DEFAULT']['medialib']
    try:
        for line in Pygtail(minimlog):
            # go to end of logfile since no accurate timestamp can be created for old data
            pass
        while True:
            # poll the logfile
            time.sleep(0.2) # decrease cpu load
            for line in Pygtail(minimlog):
                hit2 = re.search(pattern, prev_line) # check if "Contentype: audio" is present in the previous line
                if hit2:
                    hit1 = re.search(pattern2, line) # match the filename that was served
                    if hit1:
                        nowtime = time.time()
                        file = hit1.group(0)
                        if (file == lasthit) and (nowtime - oldtime < 59):
                            # if the filename is the same as the last one, check how much time has passed; if it is and it was less than a minute ago, pass on that one
                            pass
                        else:
                            lasthit = file
                            fp = path + file.rstrip()                           # assemble the full path to the file
                            #print(fp)                                           # verbose output
                            trackmetadata = readtags(fp)                        # read metadata of current file
                            listen = write_listen('playing_now', trackmetadata) # create a playing_now listen
                            print('now playing: ' + fp)
                            send_listen(listen)                                 # send that playing now listen to listenbrainz
                            time.sleep(0.2)                                     # decrease cpu load
                            if prev_listen != '':
                                if prev_listen['payload'][0]['track_metadata']['additional_info']['length'] < 90:
                                    print(str(time.time()) + ': you listened to: ' + prev_listen['payload'][0]['track_metadata']['artist_name'] + ' - ' + prev_listen['payload'][0]['track_metadata']['track_name'])
                                    send_listen(prev_listen)
                                elif (listen['payload'][0]['listened_at'] - prev_listen['payload'][0]['listened_at']) > (prev_listen['payload'][0]['track_metadata']['additional_info']['length'] / 2):
                                    # if there was a previous listen and if more than half the songlenght has passed, send out the listen as 'single' type listen
                                    print(str(time.time()) + ': you listened to: ' + prev_listen['payload'][0]['track_metadata']['artist_name'] + ' - ' + prev_listen['payload'][0]['track_metadata']['track_name'])
                                    send_listen(prev_listen)
                            prev_listen = listen
                            prev_listen['listen_type'] = 'single'
                        oldtime = nowtime
                prev_line = line
            # send single listen if time of the last track has passed and no new file started playing
            if prev_listen != '' and (time.time() - prev_listen['payload'][0]['listened_at']) > prev_listen['payload'][0]['track_metadata']['additional_info']['length']:
                print(str(time.time()) + ': you listened to: ' + prev_listen['payload'][0]['track_metadata']['artist_name'] + ' - ' + prev_listen['payload'][0]['track_metadata']['track_name'])
                send_listen(prev_listen)
                prev_listen = ''
    except KeyboardInterrupt:
        pass

def readtags(fp):
    '''Extract relevant Metainformation via mutagen'''
    f = mutagen.File(fp)
    # list of tags to query, add any custom tag to '*_additional' you want to submit
    tagsflac_basic = {
                'artist_name': 'artist',
                'track_name': 'title',
                'release_name': 'album'}
    tagsflac_additional = {
                'release_mbid': 'musicbrainz_albumid',
                'recording_mbid': 'musicbrainz_trackid',
                'track_mbid': 'musicbrainz_releasetrackid',
                'artist_mbids': 'musicbrainz_artistid',
                'rating': 'rating'}
    tagsmp3_basic =  {
                'artist_name': 'TPE1',
                'track_name': 'TIT2',
                'release_name': 'TALB'}
    tagsmp3_additional = {
                'release_mbid': 'TXXX:MusicBrainz Album Id',
                'track_mbid': 'TXXX:MusicBrainz Release Track Id',
                'recording_mbid': 'UFID:http://musicbrainz.org',
                'artist_mbids': 'TXXX:MusicBrainz Artist Id',
                'rating': 'TXXX:rating'}
    trackmetadata = {'additional_info': {}} #initialize dict for metadata json
    if f.__class__.__name__ == 'FLAC':
        tags_basic = tagsflac_basic
        tags_additional = tagsflac_additional
        fileformat = 'FLAC'
    elif f.__class__.__name__ == 'MP3':
        tags_basic = tagsmp3_basic
        tags_additional = tagsmp3_additional
        fileformat = 'MP3'
    for i in tags_basic:
        if tags_basic[i] in f:
            trackmetadata[i] = f[tags_basic[i]][0]
    for i in tags_additional:
        if tags_additional[i] in f:
            # handle different handling of artist_mbids for MP3
            if i == 'artist_mbids':
                if fileformat == 'FLAC':
                    trackmetadata['additional_info'][i] = f[tags_additional[i]]
                elif fileformat == 'MP3':
                    trackmetadata['additional_info'][i] = f[tags_additional[i]].text
            # handle recording_mbid differences with MP3
            elif i == 'recording_mbid' and fileformat == 'MP3':
                trackmetadata['additional_info'][i] = f[tags_additional[i]].data.decode('utf-8')
            else:
                trackmetadata['additional_info'][i] = f[tags_additional[i]][0]
    # add the audiolength in seconds (float)
    trackmetadata['additional_info']['length'] = f.info.length
    return trackmetadata

def write_listen(type, tm):
    listen = {
               'listen_type': type,
               'payload': [
                 {
                   'listened_at': int(time.time()),
                   'track_metadata': tm
                 }
               ]
             }
    #pprint.pprint(listen) #debug
    return listen

def send_listen(listen):
    url = 'https://api.listenbrainz.org/1/submit-listens'
    headers = {'content-type': 'application/json', 'Authorization': 'token ' + cfg['listenbrainz.org']['token']}
    r = requests.post(url, data=json.dumps(listen), headers=headers)
    #pprint.pprint(listen)
    print(r.status_code, r.reason, r.text)

logtail()
