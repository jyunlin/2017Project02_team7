# -*- coding: utf-8 -*-


from __future__ import unicode_literals

import random
import time
from datetime import timedelta, datetime
from pymongo import MongoClient

#ref: http://twstock.readthedocs.io/zh_TW/latest/quickstart.html#id2
import twstock
from twstock import Stock
from twstock import BestFourPoint

import matplotlib
matplotlib.use('Agg') # ref: https://matplotlib.org/faq/howto_faq.html
import matplotlib.pyplot as plt
import pandas as pd

import configparser

from imgurpython import ImgurClient

from flask import Flask, request, abort

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot import (
    LineBotApi, WebhookParser
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,ImageSendMessage,ImageMessage
)
from linebot.models import *

app = Flask(__name__)
config = configparser.ConfigParser()
config.read("config.ini")

channel_secret = config['line_bot']['channel_secret']
channel_access_token = config['line_bot']['channel_access_token']
line_bot_api = LineBotApi(channel_access_token)
parser = WebhookParser(channel_secret)
handler = WebhookHandler('52c4a36254d960900edc36e6fee9bb4b')

#imgur
client_id = config['imgur_api']['client_id']
client_secret = config['imgur_api']['client_secret']



#===================================================
#   stock bot
#===================================================
@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body +"1234")

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    try:
        events = parser.parse(body, signature)
    except InvalidSignatureError:
        print('InvalidSignatureError')
        abort(400)

    # if event is MessageEvent and message is TextMessage, then echo text
    for event in events:
        if not isinstance(event, MessageEvent):
            continue
        if not isinstance(event.message, TextMessage):
            continue

        text=event.message.text
        #userId = event['source']['userId']
        if(text.lower()=='me'):
            content = str(event.source.user_id)

            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=content)
            )
        elif(text.lower() == 'profile'):
            profile = line_bot_api.get_profile(event.source.user_id)
            my_status_message = profile.status_message
            if not my_status_message:
                my_status_message = '-'
            line_bot_api.reply_message(
                event.reply_token, [
                    TextSendMessage(
                        text='Display name: ' + profile.display_name
                    ),
                    TextSendMessage(
                        text='picture url: ' + profile.picture_url
                    ),
                    TextSendMessage(
                        text='status_message: ' + my_status_message
                    ),
                ]
            )

        elif(text.startswith('$')):
            text = text[1:]
            content = ''

            stock_rt = twstock.realtime.get(text)
            my_datetime = datetime.fromtimestamp(stock_rt['timestamp']+8*60*60)
            my_time = my_datetime.strftime('%H:%M:%S')
            stock = Stock(text)
            bfp = BestFourPoint(stock)
            signal=bfp.best_four_point()

            a = str(signal)
            b = signal[0]
            i4 = ImageSendMessage(
                    original_content_url="https://i.imgur.com/wUVUYYJ.jpg",
                    preview_image_url="https://i.imgur.com/wUVUYYJ.jpg"
                )
            i5 = ImageSendMessage(
                    original_content_url="https://i.imgur.com/mE50Pes.jpg",
                    preview_image_url="https://i.imgur.com/mE50Pes.jpg"
                )


            if b==True:
                line_bot_api.reply_message(event.reply_token,i4)
            if b==False:
                line_bot_api.reply_message(event.reply_token,i5)


        elif(text.startswith('#')):
            text = text[1:]
            content = ''

            stock_rt = twstock.realtime.get(text)
            my_datetime = datetime.fromtimestamp(stock_rt['timestamp']+8*60*60)
            my_time = my_datetime.strftime('%H:%M:%S')
            stock = Stock(text)
            bfp = BestFourPoint(stock)
            signal=bfp.best_four_point()
            a = str(signal)

            content += '%s (%s) %s\n' %(
                stock_rt['info']['name'],
                stock_rt['info']['code'],
                my_time)
            content += '現價: %s / 開盤: %s\n'%(
                stock_rt['realtime']['latest_trade_price'],
                stock_rt['realtime']['open'])
            content += '最高: %s / 最低: %s\n' %(
                stock_rt['realtime']['high'],
                stock_rt['realtime']['low'])
            content += '量: %s\n' %(stock_rt['realtime']['accumulate_trade_volume'])
            content += '買賣訊號:%s\n'%(a)
            stock = twstock.Stock(text)#twstock.Stock('2330')
            content += '------------------------\n'
            content += '最近五日價格: \n'
            price5 = stock.price[-5:][::-1]
            date5 = stock.date[-5:][::-1]
            for i in range(len(price5)):
                #content += '[%s] %s\n' %(date5[i].strftime("%Y-%m-%d %H:%M:%S"), price5[i])
                content += '[%s] %s\n' %(date5[i].strftime("%Y-%m-%d"), price5[i])

            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=content)
            )

        elif(text.startswith('/')):
            text = text[1:]
            fn = '%s.png' %(text)
            stock = twstock.Stock(text)
            my_data = {'close':stock.close, 'date':stock.date, 'open':stock.open}
            df1 = pd.DataFrame.from_dict(my_data)

            df1.plot(x='date', y='close')
            plt.title('[%s]' %(stock.sid))
            plt.savefig(fn)
            plt.close()

            # -- upload
            # imgur with account: your.mail@gmail.com



            client = ImgurClient(client_id, client_secret)
            print("Uploading image... ")
            image = client.upload_from_path(fn, anon=True)
            print("Done")

            url = image['link']
            image_message = ImageSendMessage(
                original_content_url=url,
                preview_image_url=url
            )

            line_bot_api.reply_message(
                event.reply_token,
                image_message
                )


    return 'OK'

@app.route("/", methods=['GET'])
def basic_url():
    return 'OK'


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    print("event.reply_token:", event.reply_token)
    print("event.message.text:", event.message.text)
    if event.message.text == "我要擲筊":
        dice = random.randint(0, 12)
        if dice<9:
            buttons_template = TemplateSendMessage(
                alt_text='我要測試本日運勢 template',
                template=ButtonsTemplate(
                    title='恭喜你獲得股票之神的青睞',
                    text='請確認您要詢問的股票代碼，輸入$+ID替它抽支籤、輸入#+ID看它近日表現、輸入/+ID看它線圖',
                    thumbnail_image_url='https://i.imgur.com/tfm62zq.jpg',
                    actions=[
                        MessageTemplateAction(
                            label='ex.幫台積電抽支籤',
                            text='$2330'
                        ),
                        MessageTemplateAction(
                            label='ex.看台積電近日表現',
                            text='#2330'
                        ),
                        MessageTemplateAction(
                            label='ex.看台積電線圖',
                            text='/2330'
                        )
                    ]
                )
            )
            line_bot_api.reply_message(event.reply_token,buttons_template)

        if dice>10 :
            buttons_template = TemplateSendMessage(
                alt_text='我要測試本日運勢 template',
                template=ButtonsTemplate(
                    title='股票之神說請展現您最大的誠意',
                    text='請誠心默念您的生辰八字，與欲詢問之股票',
                    thumbnail_image_url='https://i.imgur.com/RR9F1W5.jpg',
                    actions=[
                        MessageTemplateAction(
                            label='我要擲筊，再試一次',
                            text='我要擲筊，再試一次'
                        ),
                        MessageTemplateAction(
                            label='看來今日不適合投資對吧',
                            text='嗯嗯，對挖><'
                        )
                    ]
                )
            )
            line_bot_api.reply_message(event.reply_token,buttons_template)

        else :
            buttons_template = TemplateSendMessage(
                alt_text='我要測試本日運勢 template',
                template=ButtonsTemplate(
                    title='股票之神說請展現您最大的誠意',
                    text='請誠心默念您的生辰八字，與欲詢問之股票',
                    thumbnail_image_url='https://i.imgur.com/DWnGIWj.jpg',
                    actions=[
                        MessageTemplateAction(
                            label='我要擲筊，再試一次',
                            text='我要擲筊，再試一次'
                        ),
                        MessageTemplateAction(
                            label='看來今日不適合投資對吧',
                            text='嗯嗯，對挖><'
                        )
                    ]
                )
            )
            line_bot_api.reply_message(event.reply_token,buttons_template)
            return 0

    if event.message.text == "我要擲筊，再試一次":
        dice = random.randint(0, 12)
        if dice<9:
            buttons_template = TemplateSendMessage(
                alt_text='我要測試本日運勢 template',
                template=ButtonsTemplate(
                    title='恭喜你獲得股票之神的青睞',
                    text='請確認您要詢問的股票代碼，輸入$+ID替它抽支籤、輸入#+ID看它近日表現、輸入/+ID看它線圖',
                    thumbnail_image_url='https://i.imgur.com/tfm62zq.jpg',
                    actions=[
                        MessageTemplateAction(
                            label='ex.幫台積電抽支籤',
                            text='$2330'
                        ),
                        MessageTemplateAction(
                            label='ex.看台積電近日表現',
                            text='#2330'
                        ),
                        MessageTemplateAction(
                            label='ex.看台積電線圖',
                            text='/2330'
                        )
                    ]
                )
            )
            line_bot_api.reply_message(event.reply_token,buttons_template)

        if dice>10 :
            buttons_template = TemplateSendMessage(
                alt_text='我要測試本日運勢 template',
                template=ButtonsTemplate(
                    title='股票之神說請展現您最大的誠意',
                    text='請誠心默念您的生辰八字，與欲詢問之股票',
                    thumbnail_image_url='https://i.imgur.com/RR9F1W5.jpg',
                    actions=[
                        MessageTemplateAction(
                            label='我要擲筊，再試一次',
                            text='我要擲筊，再試一次'
                        ),
                        MessageTemplateAction(
                            label='看來今日不適合投資對吧',
                            text='嗯嗯，對挖><'
                        )
                    ]
                )
            )
            line_bot_api.reply_message(event.reply_token,buttons_template)

        else :
            buttons_template = TemplateSendMessage(
                alt_text='我要測試本日運勢 template',
                template=ButtonsTemplate(
                    title='股票之神說請展現您最大的誠意',
                    text='請誠心默念您的生辰八字，與欲詢問之股票',
                    thumbnail_image_url='https://i.imgur.com/DWnGIWj.jpg',
                    actions=[
                        MessageTemplateAction(
                            label='我要擲筊，再試一次',
                            text='我要擲筊，再試一次'
                        ),
                        MessageTemplateAction(
                            label='看來今日不適合投資對吧',
                            text='嗯嗯，對挖><'
                        )
                    ]
                )
            )
            line_bot_api.reply_message(event.reply_token,buttons_template)
        return 0


    if event.message.text == "安安":
        buttons_template = TemplateSendMessage(
            alt_text='我要測試本日運勢 template',
            template=ButtonsTemplate(
                title='我要請股票之神測試本日運勢',
                text='請誠心默念您的生辰八字，與欲詢問之股票',
                thumbnail_image_url='https://i.imgur.com/Abbr3ho.jpg',
                actions=[
                    MessageTemplateAction(
                        label='我要擲筊',
                        text='我要擲筊'
                    )
                ]
            )
        )
        line_bot_api.reply_message(event.reply_token, buttons_template)


if __name__ == "__main__":
    app.run()
