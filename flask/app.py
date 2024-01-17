# 本py只提供了酷我和网易云的搜索、mp3链接、歌词接口

from flask import Flask,jsonify
from flask import request
from flask import abort
from flask_cors import CORS
import requests
import json
from kw import kwFirstUrl
import re

#我添加的
import vlc
import sqlite3
from flask import g

app = Flask(__name__)
cors = CORS(app)
DATABASE = '/var/www/flask/database.db'

# 酷我
@app.route('/search')
def kuwoAPI():
    key = request.args.get('key')
    pn = request.args.get('pn')
    rn = 30
    url = f'http://search.kuwo.cn/r.s?pn={int(pn) - 1}&rn={rn}&all={key}&ft=music&newsearch=1&alflac=1&itemset=web_2013&client=kt&cluster=0&vermerge=1&rformat=json&encoding=utf8&show_copyright_off=1&pcmp4=1&ver=mbox&plat=pc&vipver=MUSIC_9.2.0.0_W6&devid=11404450&newver=1&issubtitle=1&pcjson=1'
    headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36 Edg/115.0.1901.188'
    }
    responseText =  requests.get(url=url, headers=headers).text
    search = []
    try:
        responseJson = json.loads(responseText)
        for song in responseJson.get("abslist"):
            if song.get('web_albumpic_short') != '':
                if "120" in song.get('web_albumpic_short'):
                    pic = f'https://img4.kuwo.cn/star/albumcover/{song.get("web_albumpic_short").replace("120", "300")}'
                else:
                    pic = f'https://img4.kuwo.cn/star/albumcover/{song.get("web_albumpic_short")}'
            else:
                if "120" in song.get('web_artistpic_short'):
                    pic = f'https://img1.kuwo.cn/star/starheads/{song.get("web_artistpic_short").replace("120", "300")}'
                else:
                    pic = f'https://img1.kuwo.cn/star/starheads/{song.get("web_artistpic_short")}'
            tempList = {
                'name': song.get('SONGNAME'),
                'artist': song.get('ARTIST'),
                'rid': int(song.get('DC_TARGETID')),
                'pic': pic
            }
            search.append(tempList)
        return json.dumps(obj=search, ensure_ascii=False)
    except Exception as e:
        print(f'Server Error: {format(str(e))}')
        print(responseText)
        return abort(500)


@app.route('/mp3')
def ridKuwoAPI():
    rid = request.args.get('rid')
    url = kwFirstUrl(rid=rid)
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36 Edg/110.0.1587.50",
        "csrf": "96Y8RG5X3X64",
        "Referer": "https://www.kuwo.cn"
    }
    try:
        music_url = requests.get(url=url, headers=headers, timeout=3).text
    except requests.Timeout:
        print('获取mp3链接超时，正在重试……')
        music_url = requests.get(url=url, headers=headers).text
    # 正则提取最终url
    pattern = r'url=(.*)'
    match = re.search(pattern, music_url)
    if match:
        music_url = match.group(1)
        print(f'已获取到mp3文件链接=>{str(music_url)}')
        return str(music_url)
    else:
        print("未找到URL")
        print('Error Info:\n' + music_url)
        abort(500)


@app.route('/lrc')
def lrcKuwoAPI():
    rid = request.args.get('rid')
    url = f'http://m.kuwo.cn/newh5/singles/songinfoandlrc?musicId={rid}&httpsStatus=1&reqId=1c3ccf60-f4a2-11ed-b93d-c5042ed5dae3'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36 Edg/113.0.1774.42'
    }
    try:
        lrc = requests.get(url=url, headers=headers, timeout=3).json()["data"]["lrclist"]
    except requests.Timeout:
        print('获取歌词超时，正在重试……')
        lrc = requests.get(url=url, headers=headers).json()["data"]["lrclist"]
    print('已获取到歌词\n\n')
    return json.dumps(lrc)


# 网易云
# 网易云API需要自行部署开源的NeteaseCloudMusicApi项目
# 为了方便音乐盒前端，以下将网易云的API转成了酷我的格式

NeteaseCloudMusicApiBaseUrl = '你部署的NeteaseCloudMusicApi项目BaseUrl'
@app.route('/wyy/search')
def wyySearch():
    key = request.args.get('key')
    pn = request.args.get('pn')
    url = f'{NeteaseCloudMusicApiBaseUrl}/cloudsearch?keywords={key}&offset={(int(pn) - 1) * 30}'
    responseText = requests.get(url).text
    search = []
    try:
        responseJson = json.loads(responseText)
        for song in responseJson["result"]["songs"]:
            search.append({
                "name": song["name"],
                "artist": song["ar"][0]["name"],
                "rid": song["id"],
                "pic": f'{song["al"]["picUrl"].replace("http://", "https://")}?param=300y300',
                "iswyy": True
            })
        print('网易云获取搜索结果成功！')
        return json.dumps(obj=search, ensure_ascii=False)
    except:
        print(f'网易云获取搜索结果出错！key: {key}\nresponseText: {responseText}')
        return abort(500)
    
@app.route('/wyy/mp3')
def wyyMp3():
    rid = request.args.get('rid')
    url = f'{NeteaseCloudMusicApiBaseUrl}/song/url?id={rid}&br=320000'
    responseText = requests.get(url).text
    try:
        responseJson = json.loads(responseText)["data"][0]["url"]
        if(responseJson == None):
            print(f'网易云获取mp3出错！rid: {rid}')
            check = requests.get(f'{NeteaseCloudMusicApiBaseUrl}/check/music?id={rid}').text
            print('检测信息: ' + check)
            print(f'版权原因，无播放权限！info:\n{responseText}')
            return '版权原因，无播放权限！'
        else:
            print('网易云获取mp3成功！')
            return responseJson
    except:
        print('其他异常！')
        return abort(500)

@app.route('/wyy/lrc')
def wyyLrc():
    rid = request.args.get('rid')
    url = f'{NeteaseCloudMusicApiBaseUrl}/lyric?id={rid}'
    responseText = requests.get(url).text
    lrcArr = []
    try:
        responseJson = json.loads(responseText)
        lrc_str = responseJson["lrc"]["lyric"]
        for match in re.finditer(r'\[(\d+):(\d+\.\d+)\](.*)', lrc_str):
            min, sec, lyric = match.groups()
            time = float(min) * 60 + float(sec)
            # print(time, lyric)
            lrcArr.append({
                "lineLyric": lyric,
                "time": format(time, ".2f")
            })
        print('网易云获取歌词成功！')
        return json.dumps(obj=lrcArr, ensure_ascii=False)
    except:
        print(f'网易云获取歌词出错！rid: {rid}\nresponseText: {responseText}')
        return abort(500)



# 创建全局的MediaPlayer对象
media_player = None

# VLC 音乐播放
@app.route('/play-music', methods=['POST'])
def play_music():
    try:
        # 声明全局变量
        global media_player

        # 如果已有歌曲在播放，停止先前的播放
        if media_player is not None:
            media_player.stop()

        # 获取请求中的音频文件链接
        data = request.json
        filename = data.get('filename')

        # 如果之前未创建过 就创建新的MediaPlayer对象并播放音乐
        if media_player is None:
            media_player = vlc.MediaPlayer(filename)
            media_player.play()
        # 否则media_player对象已经创建，使用set_media方法更新待播放的音频文件路径，并调用play方法来播放音乐
        else:
            media_player.set_media(vlc.Media(filename))
            media_player.play()

        return {'status': 'success', 'message': '音乐播放成功'}

    except Exception as e:
        return {'status': 'error', 'message': str(e)}



# VLC 音乐播放暂停功能
@app.route('/pause-music', methods=['POST'])
def pause_music():
    try:
        # 声明全局变量
        global media_player

        # 检查是否存在正在播放的媒体
        if media_player is not None:
            # 如果当前处于播放状态，暂停音乐
            if media_player.is_playing():
                media_player.pause()
                return {'status': 'success', 'message': '音乐已暂停'}
            # 如果当前处于暂停状态，切换成播放状态
            else:
                media_player.play()
                return {'status': 'success', 'message': '音乐已播放'}

        return {'status': 'error', 'message': '没有正在播放的音乐'}

    except Exception as e:
        return {'status': 'error', 'message': str(e)}



#保存歌单功能
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

@app.teardown_appcontext
def close_db(error):
    if hasattr(g, '_database'):
        g._database.close()

@app.route('/music-box-list/', methods=['GET', 'POST'])
def musicBoxList():
    if request.method == 'GET':
        id = request.args.get('id')
        result = get_music_box(id)
        if result:
            return jsonify(result)
        else:
            return jsonify({"error": "歌单不存在"})
    elif request.method == 'POST':
        music_list = request.json
        result = save_music_box(music_list)
        return jsonify(result)

def get_music_box(id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM musicBox WHERE ID = ?', (id,))
    row = cursor.fetchone()
    cursor.close()
    if row is not None:
        result = {
            "ID": row[0],
            "Name": row[1],
            "List": json.loads(row[2])
        }
    else:
        result = None
    print(result)  # 添加打印语句
    return result

def save_music_box(music_list):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT ID FROM musicBox ORDER BY ID DESC LIMIT 1')
    last_id = cursor.fetchone()
    if last_id is None:
        new_id = 10000
    else:
        new_id = last_id[0] + 1
    music_name = music_list["name"]
    display_list = music_list["list"]
    cursor.execute('INSERT INTO musicBox (ID, Name, List) VALUES (?, ?, ?)', (new_id, music_name, json.dumps(display_list)))
    conn.commit()
    cursor.close()
    return {"ID": new_id}




if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9000)
