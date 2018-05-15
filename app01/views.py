from django.shortcuts import render,HttpResponse
import requests
import time
import re
import json

def ticket(html):
    from bs4 import BeautifulSoup
    ret = {}
    soup = BeautifulSoup(html,"html.parser")
    for tag in soup.find(name="error").find_all():
        ret[tag.name] = tag.text
    return ret

def login(req):
    if req.method == "GET":
        uuid_time = int(time.time() * 1000)
        base_uuid_url = "https://login.wx.qq.com/jslogin?appid=wx782c26e4c19acffb&redirect_uri=https%3A%2F%2Fwx.qq.com%2Fcgi-bin%2Fmmwebwx-bin%2Fwebwxnewloginpage&fun=new&lang=zh_CN&_={0}"
        uuid_url = base_uuid_url.format(uuid_time)
        r1 = requests.get(uuid_url)
        result = re.findall('= "(.*)";',r1.text)
        uuid = result[0]
        req.session["UUID_TIME"] = uuid_time
        req.session["UUID"] = uuid

        return render(req,"login.html")

def check_login(req):
    response = {"code":408,"data":None}
    ctime = int(time.time() * 1000)
    base_login_url = 'https://login.wx.qq.com/cgi-bin/mmwebwx-bin/login?loginicon=true&uuid={0}&tip=0&r=-1555198623&_={1}'
    login_url = base_login_url.format(req.session.get("UUID"),ctime)
    r1 = requests.get(login_url)
    print(r1.text)
    if "window.code=408" in r1.text:
        # 无人扫码
        response['code'] = 408
    elif "window.code=201" in r1.text:
        # 扫码，返回头像
        response['code'] = 201
        response["data"] = re.findall("window.userAvatar = '(.*)';",r1.text)[0]
    elif "window.code=200" in r1.text:
        # 扫码，并确认登录
        req.session["LOGIN_COOKIE"] = r1.cookies.get_dict()
        base_redirect_rul = re.findall('redirect_uri="(.*)";',r1.text)[0]
        redirect_rul = base_redirect_rul + "&fun=new&version=v2"

        # 获取凭证
        r2 = requests.get(redirect_rul)
        # print(r2.text)
        ticket_dict = ticket(r2.text)
        req.session["TICKET_DICT"] = ticket_dict
        req.session["TICKET_COOKIE"] = r2.cookies.get_dict()
        # print(ticket_dict)
        # 初始化，获取最近联系人信息、个人信息,放在session中
        post_data = {
            "BaseRequest":{
                "DeviceID":"e030886453343954",
                "Sid":ticket_dict["wxsid"],
                "Uin":ticket_dict["wxuin"],
                "Skey":ticket_dict["skey"],
            }
        }
        init_url = 'https://wx2.qq.com/cgi-bin/mmwebwx-bin/webwxinit?r=-1560453674&lang=zh_CN&pass_ticket={0}'.format(ticket_dict["pass_ticket"])

        r3 = requests.post(
            url = init_url,
            json = post_data,
        )
        r3.encoding = "utf-8"
        init_dict = json.loads(r3.text)
        req.session["INIT_DICT"] = init_dict

        response["code"] = 200

#         '''window.redirect_uri="https://wx2.qq.com/cgi-bin/mmwebwx-bin/webwxnewloginpage?ticket=A0onyDaL_JDHqBT1oveb899u@qrticket_0&uuid=YbiVhJhLKg==&lang=zh_CN&scan=1526270237";
# '''
    return HttpResponse(json.dumps(response))


def avatar(req):
    prev = req.GET.get("prev")
    username = req.GET.get("username")
    skey = req.GET.get("skey")
    img_url = "https://wx2.qq.com{0}&username={1}&skey={2}".format(prev,username,skey)
    print(img_url)
    cookies = {}
    cookies.update(req.session["LOGIN_COOKIE"])
    cookies.update(req.session["TICKET_COOKIE"])

    res = requests.get(img_url,cookies=cookies,headers={"Content-Type":"image/jpeg","Referer":"https://wx2.qq.com/"})

    return HttpResponse(res.content)

def index(req):
    """显示最近联系人"""

    return render(req,"index.html")


def contact_list(req):
    ctime = int(time.time() * 1000)
    base_url = 'https://wx2.qq.com/cgi-bin/mmwebwx-bin/webwxgetcontact?lang=zh_CN&r={0}&seq=0&skey={1}'
    url = base_url.format(ctime,req.session["TICKET_DICT"]["skey"])
    cookies = {}
    cookies.update(req.session["LOGIN_COOKIE"])
    cookies.update(req.session["TICKET_COOKIE"])

    r1 = requests.get(url,cookies=cookies)
    r1.encoding = "utf-8"

    user_list = json.loads(r1.text)

    return render(req,"contact_list.html",{"user_list":user_list})


def conversation(req):
    ctime = int(time.time() * 10000000)
    send_msg = {
        "BaseRequest": {
            "DeviceID": "e295475396326474",
            "Sid": req.session["TICKET_DICT"]["wxsid"],
            "Skey": req.session["TICKET_DICT"]["skey"],
            "Uin": req.session["TICKET_DICT"]["wxuin"],
        },
        "Msg": {
            "ClientMsgId": ctime,
            "Content": "when will you arrive home?",
            "FromUserName": req.session["INIT_DICT"]["User"]["UserName"],
            "LocalID": ctime,
            "ToUserName": "filehelper",
            "Type": 1,
        },
        "Scene": 0,
    }
    print(send_msg)
    print(req.session["INIT_DICT"]["User"])

    base_url = 'https://wx2.qq.com/cgi-bin/mmwebwx-bin/webwxsendmsg?lang=zh_CN&pass_ticket={0}'
    sendMsg_url = base_url.format(req.session["TICKET_DICT"]["pass_ticket"])
    # print(req.session["TICKET_COOKIE"])
    # print(req.session["TICKET_DICT"])


    cookies = {}
    cookies.update(req.session["LOGIN_COOKIE"])
    cookies.update(req.session["TICKET_COOKIE"])

    res = requests.post(
        url = sendMsg_url,
        data = json.dumps(send_msg,ensure_ascii=False),
        cookies=cookies,
        headers = {
            "Content-Type":"application/json"
        }
    )

    print(res.text)
    return HttpResponse("...")


def send_msg(req):
    """
    发送消息
    :param req:
    :return:
    """
    current_user = req.session["INIT_DICT"]["User"]["UserName"]
    to = req.POST.get("to")
    msg = req.POST.get("msg")
    ctime = int(time.time() * 10000000)
    ticket_dict = req.session["TICKET_DICT"]

    post_data = {
        "BaseRequest": {
            "DeviceID": "e295475396326474",
            "Sid": ticket_dict["wxsid"],
            "Skey": ticket_dict["skey"],
            "Uin": ticket_dict["wxuin"],
        },
        "Msg": {
            "ClientMsgId": ctime,
            "Content": msg,
            "FromUserName": current_user,
            "LocalID": ctime,
            "ToUserName": to,
            "Type": 1,
        },
        "Scene": 0,
    }

    base_url = 'https://wx2.qq.com/cgi-bin/mmwebwx-bin/webwxsendmsg?lang=zh_CN&pass_ticket={0}'
    sendMsg_url = base_url.format(ticket_dict["pass_ticket"])

    cookies = {}
    cookies.update(req.session["LOGIN_COOKIE"])
    cookies.update(req.session["TICKET_COOKIE"])

    res = requests.post(
        url = sendMsg_url,
        cookies = cookies,
        # json=post_data,
        data = bytes(json.dumps(post_data,ensure_ascii=False,),encoding="utf-8"),
        headers = {"Content-Type":"application/json"}
    )
    print(res.text)
    return HttpResponse(res.text)


def get_msg(req):
    """
    长轮询获取消息
    :param req:
    :return:
    """
    # 检查是否有消息到来
    ctime = int(time.time() * 1000)
    ticket_dict = req.session["TICKET_DICT"]
    check_msg_url = "https://webpush.wx2.qq.com/cgi-bin/mmwebwx-bin/synccheck"
    cookies = {}
    cookies.update(req.session["LOGIN_COOKIE"])
    cookies.update(req.session["TICKET_COOKIE"])

    synckey_dict = req.session["INIT_DICT"]["SyncKey"]
    synckey_list = []
    for item in synckey_dict["List"]:
        tmp = "%s_%s" % (item["Key"],item["Val"])
        synckey_list.append(tmp)
    synckey = "|".join(synckey_list)

    r1 = requests.get(
        url=check_msg_url,
        params={
            "r":ctime,
            "deviceID": "e295475396326474",
            "sid": ticket_dict["wxsid"],
            "skey": ticket_dict["skey"],
            "uin": ticket_dict["wxuin"],
            "_":ctime,
            "synckey":synckey,
        },
        cookies = cookies,
    )
    # 无消息
    print(r1.text)
    if 'retcode:"0",selector:"0"}' in r1.text:
        return HttpResponse("...")

    # 有消息
    if 'retcode:"0",selector:"2"}' in r1.text:
        post_data = {
            "BaseRequest": {
                "DeviceID": "e295475396326474",
                "Sid": ticket_dict["wxsid"],
                "Skey": ticket_dict["skey"],
                "Uin": ticket_dict["wxuin"],
            },
            "SyncKey": req.session["INIT_DICT"]["SyncKey"],
        }

        base_get_msg_url = "https://wx2.qq.com/cgi-bin/mmwebwx-bin/webwxsync?sid={0}&skey=[1]&lang=zh_CN"
        get_msg_url = base_get_msg_url.format(ticket_dict["wxsid"],ticket_dict["skey"])
        r2 = requests.post(
            url = get_msg_url,
            json = post_data,
            cookies = cookies,
        )
        r2.encoding = "utf-8"
        msg_dict = json.loads(r2.text)
        print(msg_dict)
        for msg in msg_dict["AddMsgList"]:
            print("\033[1;33m您有新消息到来\033[0m;",msg["Content"],msg["FromUserName"])
        # print(msg_dict["SyncKey"])
        # req.session["INIT_DICT"]["SyncKey"] = msg_dict["SyncKey"]  # 不能这么写，这样是只修改内存的值，不写入数据库
        init_dict = req.session["INIT_DICT"]
        init_dict["SyncKey"] = msg_dict["SyncKey"]
        req.session["INIT_DICT"] = init_dict

        # 接收到消息：消息，synckey

    # 有，获取新消息
    # 无

    return HttpResponse("...")











