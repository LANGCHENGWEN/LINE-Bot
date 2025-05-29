from flask import (
    Flask, 
    request, 
    abort, 
    render_template
)
'''
引入 Flask 框架與其常用方法：
Flask: 建立 Web 應用，用它來定義路由、設定參數等[建立應用程式主體]
request: 用來存取 HTTP 請求中的資訊，例如使用者傳來的資料、表單、參數等[取得用戶端送來的資料]
abort: 用來終止請求流程，並回傳錯誤狀態碼（例如 404、403、400）[主動回應錯誤，停止處理請求]
render_template: 用來渲染 HTML 模板，會從 /templates 資料夾中載入 .html 檔案（目前未使用）[用來輸出 HTML 頁面並傳入變數]
'''

from linebot.v3 import (    #linebot.v3 是套件的主要入口，用來處理 LINE Bot 與 LINE 伺服器之間的 webhook 互動
    WebhookHandler    #這個類別是用來接收、解析並處理從 LINE 傳過來的 webhook 事件（如文字訊息、貼圖、追蹤事件等）
)
#匯入 LINE Bot SDK 中的 Webhook 處理器，用來處理事件

from linebot.v3.exceptions import (    #linebot.v3.exceptions 是 LINE Bot SDK 中的例外處理模組，裡面定義了在使用 SDK 時，可能會遇到的錯誤型別
    InvalidSignatureError    #這個例外是用來處理「簽章驗證失敗」的情況
)
#用於處理錯誤的例外狀況

from linebot.v3.messaging import (    #從 linebot.v3.messaging 模組中，匯入幾個「處理傳送訊息」相關的重要類別
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,  # 傳輸回Line官方後台的資料格式
)
'''
匯入與訊息傳遞有關的設定與物件：
Configuration: 設定 LINE Messaging API 所需的參數，例如存取權杖（access token）[設定 API 的存取權杖等參數]
ApiClient: 建立與 LINE Messaging API 的 HTTP 連線客戶端[建立 API 用的連線客戶端]
MessagingApi: 這是主要的 API 操作介面，包含像 reply_message()、push_message() 等方法，用來傳送訊息[提供傳訊息的功能（如回覆、推播等）]
ReplyMessageRequest: 建立「回覆訊息」的請求物件，用來指定要回傳給使用者的訊息內容[包裝回覆訊息請求（含 reply token 與訊息）]
TextMessage: 建立一個純文字訊息物件，會作為回傳給使用者的內容之一，想要傳回給 LINE 使用者的一句話[單一純文字訊息的格式]
'''

from linebot.v3.webhooks import (    #從 LINE Bot SDK 中的 linebot.v3.webhooks 模組匯入「處理使用者訊息」相關的類別
    MessageEvent,FollowEvent, # 傳輸過來的方法
    TextMessageContent, # 使用者傳過來的資料格式\
)
'''
匯入 webhook 事件與訊息格式：
MessageEvent: 接收訊息事件，表示使用者傳送的「訊息事件」[使用者傳送訊息（文字、圖片等）時觸發]
FollowEvent: 新加入好友事件，表示使用者「加入好友」時觸發的事件[使用者加入好友（首次或重新加入）時觸發]
TextMessageContent: 傳入文字訊息格式，用來取得使用者傳來的「純文字訊息」內容
'''

import pandas as pd    #pandas: 用來處理 CSV 資料
from handle_keys import get_secret_and_token    #get_secret_and_token: 自定義函式，取得金鑰
from import_modules import *
from create_linebot_messages_sample import *    #import_modules, create_linebot_messages_sample: 其他自定義模組（應為功能元件），全部匯入
from collections import defaultdict    #defaultdict: 預設字典結構，這裡雖引入但未使用

app = Flask(__name__)    #建立 Flask 應用，準備接收 HTTP 請求
keys = get_secret_and_token()    #呼叫自定義函式 get_secret_and_token()，從模組中讀取 LINE 的 secret 與 Token
handler = WebhookHandler(keys['LINEBOT_SECRET_KEY'])    #建立 LINE Bot 的 WebhookHandler 處理器
configuration = Configuration(access_token=keys['LINEBOT_ACCESS_TOKEN'])    #建立 LINE Bot 的 API 存取設定[設定連接 LINE Messaging API 所需的 access token]

rest_recommand_memory = dict()    #建立一個空的字典，並將它指定給變數 rest_recommand_memory，用來儲存「使用者的餐廳推薦記憶」

rest_dict = {
    'breakfast_rest': pd.read_csv('taichungeatba/breakfast_rest.csv').dropna(axis=1).groupby('區域'),
    'lunch_rest': pd.read_csv('taichungeatba/lunch_rest.csv').dropna(axis=1).groupby('區域'),
    'dinner_rest': pd.read_csv('taichungeatba/dinner_rest.csv').dropna(axis=1).groupby('區域')
}
#分別讀取早餐、午餐、晚餐的資料，依「區域」分組
#把含有空值的欄（column） 移除（axis=1 代表欄）

@app.route("/callback", methods=['POST'])
def callback():    #當 LINE 發送 Webhook 事件到 /callback，會由這個函式處理
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']    #從 Header 取得簽章，驗證訊息來源是否正確

    # get request body as text
    body = request.get_data(as_text=True)    #取得 HTTP 請求的主體內容（使用者傳的 JSON）
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)    #驗證與處理事件
    except InvalidSignatureError:
        app.logger.info("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)
    #如果簽章錯誤則回傳 400

    return 'OK'    #成功回應

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):    #當使用者傳送訊息，會觸發這個事件
    user_id = event.source.user_id
    user_message = event.message.text # 使用者傳過來的訊息
    #取得使用者 ID 和傳來的文字訊息

    if "sample" in user_message:
        responses = [handle_sample(user_message)]
    elif '美食推薦' in user_message: # Get Time
        responses = [handle_choose_time()]
    elif user_message.startswith('#') and user_message.endswith('餐'): # Get Section
        responses = [handle_choose_section(user_id, user_message)]
    elif user_message.startswith('#') and user_message.endswith('區'): # Get recommand
        section_name = user_message[1:]
        responses = [handle_rests_recommand(user_id, section_name)]
    else:# 閒聊
        responses = [TextMessage(text='Got it!')] 
    '''
    根據訊息內容給出不同回應：
    sample → 測試訊息範例
    美食推薦 → 顯示選擇餐別
    #...餐 → 顯示區域選項
    #...區 → 推薦餐廳
    其他 → 回 "Got it!"
    '''

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=responses
            )
        )
    #建立 LINE API 用戶端並發送回覆

def handle_choose_time():
    response = ButtonsTemplate(
        thumbnail_image_url='https://i.imgur.com/b9oaYpu.jpeg',
        title='歡迎使用!!',
        text='請選擇要推薦的風格餐廳。',
        actions=[
            MessageAction(text='#文青早餐', label='享用文青早點'),
            MessageAction(text='#在地午餐', label='品嘗在地美食'),
            MessageAction(text='#高檔晚餐', label='暢享高檔餐廳')
        ]
    )
    return TemplateMessage(
        type='template',
        altText="TemplateMessage",
        template=response
    )
  #傳送一個 ButtonsTemplate，提供三個餐別選項

def handle_choose_section(user_id, time_message):
    def create_quick_reply_item(section_name):
        return QuickReplyItem(action=MessageAction(text=f'#{section_name}', label=f'{section_name}'))

    if time_message == '#文青早餐':
        rest_groups = rest_dict['breakfast_rest']
    elif time_message == '#在地午餐':
        rest_groups = rest_dict['lunch_rest']
    elif time_message == '#高檔晚餐':
        rest_groups = rest_dict['dinner_rest']
    
    rest_recommand_memory[user_id] = rest_groups


    sections = rest_groups.groups.keys()
    quick_reply_items = [create_quick_reply_item(section) for section in sections]
    quick_reply_body = QuickReply(items=quick_reply_items)

    return TextMessage(
        text="請選擇你的所在區域~",
        quickReply=quick_reply_body
    )
  #根據餐別讀取對應的區域群組，並用 quick reply 顯示區域選項

def handle_rests_recommand(user_id, section_name):
    def create_rest_col(rest_text, rest_title, rest_comment="",rest_address="",rest_phon="",rest_url=""):
#       url = 'https://www.google.com'
        address = rest_address if rest_address else '這是地址'
        phon = rest_phon if rest_phon else '這是電話'
        comment = rest_comment if rest_comment else '這是評論'
        return CarouselColumn(
            text=rest_text,
            title=rest_title,
            thumbnail_image_url='https://i.imgur.com/97LucO0.jpg',
            actions=[
                # MessageAction(label='餐廳地址', text=address),
                # MessageAction(label='連絡電話', text=phon),
                # MessageAction(label='餐廳評價', text=comment),
                PostbackAction(label='餐廳地址', data=f'action=address&info={address}'),
                PostbackAction(label='連絡電話', data=f'action=phon&info={phon}'),
                PostbackAction(label='餐廳評價', data=f'action=comment&info={comment}')

            ]
        )
    
    def get_group_sample(group):
        group_size = len(group)
        return group.sample(min(group_size, 3))

    rests = rest_recommand_memory[user_id]
    samples = rests.get_group(section_name).apply(get_group_sample)
    carousel = CarouselTemplate(columns=[
        create_rest_col(opentime, name, comment, address,phone)
        for name, opentime, phone, section, address, comment in samples.values
    ])
    return TemplateMessage(
        type='template',
        altText="TemplateMessage",
        template=carousel
    )
'''
根據使用者選的區域，從記憶體取出餐廳分組，隨機推薦 3 間
用 CarouselTemplate 顯示多筆餐廳資訊
'''

from urllib.parse import parse_qsl
@handler.add(FollowEvent) 
def handle_postback(event):
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text="歡迎加入台中吃飽小幫手!!一起探索台中美味，發現更多好吃的餐廳吧!若要使用尋找美食功能，請輸入關鍵字<美食推薦>")]
            )
        )
#使用者加入好友時，回傳歡迎訊息

def handle_sample(user_message):
    if "按鈕sample" in user_message:
        return create_buttons_template()
    elif "輪播sample" in user_message:
        return create_carousel_template()
    elif "確認sample" in user_message:
        return create_check_template()
    else:
        return create_quick_reply()
#測試 sample 功能（按鈕、輪播、確認、快速回覆）


if __name__ == "__main__":
    app.run(debug=True)
#執行 Flask 應用，啟動 server
