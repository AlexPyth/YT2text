import requests
from re import findall
import json
from requests.exceptions import ReadTimeout


class YouTubeTranscriptBot:
    def __init__(self):
        self.tg_key = 'Your_HTTP_API_token'
        
        updates = requests.get(f'https://api.telegram.org/bot{self.tg_key}/getUpdates').json()['result']
        self.last_update = updates[-1]['update_id']+1 if updates else 0

    def get_transcript(self, yt_url):
        with requests.Session() as session:
            session.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.141 Safari/537.36'}
            
            response = session.get(yt_url)

            key = findall(r'"INNERTUBE_API_KEY":"([\w\W]+?)"', response.text)[0]
            json_data = json.loads(findall(r'var ytInitialData = ([\w\W]+?);</script>', response.text)[0])
            ts_data = [i['engagementPanelSectionListRenderer']['content']['continuationItemRenderer']['continuationEndpoint'] for i in json_data['engagementPanels'] if i['engagementPanelSectionListRenderer']['targetId'] == 'engagement-panel-searchable-transcript'][0]

            ts_url = 'https://www.youtube.com'+ts_data['commandMetadata']['webCommandMetadata']['apiUrl']
            params = {
                'key': key,
                'prettyPrint': 'false'
            }
            payload = {
                'context':{
                    'clickTracking':{
                        'clickTrackingParams': ts_data['clickTrackingParams']
                    },
                    'adSignalsInfo': {},
                    'client': json.loads('{"hl": "ru", "gl": "RU", "remoteHost": "0.0.0.0", "deviceMake": "", "deviceModel": "", "visitorData": "", "userAgent": "'+session.headers['User-Agent']+'", "clientName": "WEB", "clientVersion": "2.20220512.01.00", "osName": "Windows", "osVersion": "1", "originalUrl": "'+yt_url+'", "platform": "DESKTOP", "clientFormFactor": "UNKNOWN_FORM_FACTOR", "configInfo": { "appInstallData": "" }, "browserName": "Chrome", "browserVersion": "1", "screenWidthPoints": 1, "screenHeightPoints": 1, "screenPixelDensity": 1, "screenDensityFloat": 1.25, "utcOffsetMinutes": 300, "userInterfaceTheme": "USER_INTERFACE_THEME_LIGHT", "connectionType": "CONN_CELLULAR_4G", "memoryTotalKbytes": "4000000", "mainAppWebInfo": { "graftUrl": "'+yt_url+'", "pwaInstallabilityStatus": "PWA_INSTALLABILITY_STATUS_UNKNOWN", "webDisplayMode": "WEB_DISPLAY_MODE_BROWSER", "isWebNativeShareAvailable": true }, "timeZone": "Europe/Moscow"}'),
                    'request': {},
                    'user': {},
                }
            }
            payload.update(ts_data['getTranscriptEndpoint'])
            
            response = session.post(ts_url, params=params, data=json.dumps(payload))
            text_data = response.json()['actions'][0]['updateEngagementPanelAction']['content']['transcriptRenderer']['content']['transcriptSearchPanelRenderer']['body']['transcriptSegmentListRenderer']['initialSegments']
            return ' '.join([i['transcriptSegmentRenderer']['snippet']['runs'][0]['text'] for i in text_data if 'runs' in i['transcriptSegmentRenderer']['snippet']])

    def send_tg(self, chat_id, message):
        url = f'https://api.telegram.org/bot{self.tg_key}/sendMessage'
        if len(message) > 4096:
            for x in range(0, len(message), 4096):
                requests.post(url, data={'chat_id': chat_id, 'text': message[x:x+4096]})
        else:
            requests.post(url, data={'chat_id': chat_id, 'text': message})

    def start(self):
        while True:
            try:
                response = requests.get(f'https://api.telegram.org/bot{self.tg_key}/getUpdates', params={'offset': self.last_update, 'timeout': 60, 'allowed_updates':['message'], 'limit': 1}, timeout=60).json()['result']
                if not response:
                    continue
                response = response[0]
            except ReadTimeout:
                continue
            self.last_update = response['update_id']+1
            text = response['message']['text'].replace('http:', 'https:')
            if text[0:24] != 'https://www.youtube.com/':
                continue
            chat_id = response['message']['chat']['id']
            try:
                transcript = self.get_transcript(yt_url=text)
            except Exception:
                self.send_tg(chat_id=chat_id, message='Error')
                continue
            self.send_tg(chat_id=chat_id, message=transcript)


if __name__ == "__main__":
    bot = YouTubeTranscriptBot()
    bot.start()
