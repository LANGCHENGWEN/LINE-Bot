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

@app.route("/callback", methods=['POST'])    #這是 Flask 的路由裝飾器（decorator），設定當收到一個 POST 請求到 /callback 這個路徑時，就會執行接下來定義的 callback() 函式
def callback():    #定義一個名為 callback 的 Python 函式，當 LINE 發送 Webhook 事件到 /callback，/callback 路由被觸發（即收到 POST 請求）時會執行這段程式碼
    # get X-Line-Signature header value(從 HTTP 請求的標頭（headers）中，取得 X-Line-Signature 的值，並將其存入 signature 變數)
    signature = request.headers['X-Line-Signature']    #從 Header 取得簽章，驗證訊息來源是否正確
'''
@app.route(...) 是設定一個 URL 路由
"/callback" 是路由的 URL 路徑
methods=['POST'] 表示這個路由只接受 POST 請求，這是因為 LINE 的 webhook 資料是用 POST 傳送的
'''
'''
request.headers 是 Flask 提供的請求標頭物件
'X-Line-Signature' 是 LINE Messaging API 為了驗證請求合法性所附加的簽章
這個簽章用來驗證 webhook 資料是否來自 LINE 的伺服器，避免惡意或假冒的請求
'''

    # get request body as text(從 HTTP 請求中「取得原始的請求內容（request body）」，並將它轉成文字格式，儲存在 body 變數中)
    body = request.get_data(as_text=True)    #取得 HTTP 請求的主體內容（使用者傳的 JSON）[接收資料，從 POST 請求中讀取 JSON 文字內容]
    app.logger.info("Request body: " + body)    #把剛剛取得的 body 輸出到伺服器的日誌（log）中，用來做除錯或紀錄[記錄資料，把收到的內容寫進 log，方便你查看]
    '''
    request 是 Flask 提供的物件，代表這次收到的 HTTP 請求
    .get_data() 是取得原始的請求資料（也就是 POST 傳過來的資料）
    as_text=True 代表把這些資料當成字串（text）來處理，而不是二進位（bytes）
    '''
    '''
    app.logger.info(...) 是 Flask 提供的 log 功能，會把這行資訊記錄到日誌中，層級是「info」（資訊級別）
    "Request body: " + body 是要輸出的文字
    '''

    # handle webhook body
    try:    #開始一個 try 區塊，用來嘗試執行某些可能會出錯的程式碼。如果發生錯誤，就會跳到 except 處理[嘗試執行，準備處理 webhook 資料]
        handler.handle(body, signature)    #驗證與處理事件，使用 LINE 提供的 handler 物件，來「驗證簽章」並「處理 webhook 的事件」[驗證+處理事件，若簽章正確，執行相對應的事件邏輯]
    except InvalidSignatureError:    #如果上面 handler.handle() 發生了 InvalidSignatureError 錯誤（代表簽章驗證失敗），就執行下面的錯誤處理程式碼[錯誤處理，如果簽章不正確就會進入這段]
        app.logger.info("Invalid signature. Please check your channel access token/channel secret.")    #把錯誤資訊記錄到伺服器日誌中，方便你排錯。這樣你會知道是簽章驗證失敗，而不是其他錯誤[記錄錯誤，把錯誤原因寫進 log]
        abort(400)    #如果簽章錯誤則回傳 400[回應錯誤，通知 LINE 請求格式有誤或未通過驗證]
    '''
    body：你剛剛從請求中取出的原始資料（字串格式的 JSON）
    signature：從 header 拿到的 X-Line-Signature 簽章
    handler.handle(...)：這個方法會先用 signature 驗證 body 的來源是否為 LINE，如果合法，才會進一步解析事件（例如文字訊息、貼圖等）並交由對應的處理函式執行
    '''

    return 'OK'    #通知 LINE 伺服器這次 webhook 接收與處理成功

@handler.add(MessageEvent, message=TextMessageContent)    #當接收到 MessageEvent 且其訊息類型為 TextMessageContent 時，就執行下方的 handle_message 函式[註冊事件處理器，當使用者發送「文字訊息」時觸發]
def handle_message(event):    #當使用者傳送訊息，會觸發這個事件。這個函式會在收到符合條件的 LINE 訊息事件時被呼叫，並接收一個 event 參數(event 是一個物件，包含了這次訊息事件的詳細內容，例如：誰傳送的、傳送什麼訊息、是從聊天室還是群組等等)[定義處理函式，接收這次事件物件]
    user_id = event.source.user_id    #從事件中取得發送訊息的使用者 ID，並存到 user_id 變數裡[取得使用者 ID，可用於辨識使用者身份]
    user_message = event.message.text #取得使用者傳送的文字訊息，並儲存在 user_message 變數裡，event.message 是事件中的訊息物件，.text 是該訊息的內容（只有在訊息類型是文字時才有這個欄位）[取得訊息內容，把使用者傳的字存進變數]
'''
@handler.add(...)：註冊一個事件處理函式
MessageEvent：代表使用者發送了訊息（可能是文字、貼圖、圖片等）
message=TextMessageContent：這裡限制訊息類型為「文字訊息」（text message），只有文字才會觸發這個函式
'''

    if "sample" in user_message:    #如果使用者訊息中有包含「sample」這個字串，就執行下方的對應邏輯
        responses = [handle_sample(user_message)]    #呼叫 handle_sample(user_message) 函式，將使用者訊息傳入處理，並把結果放入一個列表 responses 中
    elif '美食推薦' in user_message: # Get Time    #如果訊息中有「美食推薦」這四個字，就執行下面的程式
        responses = [handle_choose_time()]    #呼叫 handle_choose_time() 函式（不需要傳參數），然後把回傳結果放進 responses，這可能是顯示一個時間選單，讓使用者選「什麼時候要吃美食」
    elif user_message.startswith('#') and user_message.endswith('餐'): # Get Section    #如果訊息以「#」開頭、以「餐」結尾，就執行下面的程式，這可能是用來表示「餐別」，例如早餐、午餐、晚餐
        responses = [handle_choose_section(user_id, user_message)]    #把 user_id 和 user_message 傳進 handle_choose_section() 函式，執行邏輯並取得回覆訊息，放進 responses，有可能根據餐別記錄或推薦餐廳給使用者
    elif user_message.startswith('#') and user_message.endswith('區'): # Get recommand    #如果訊息以「#」開頭，並以「區」結尾，就執行下面的程式，這應該是用來表示「地區」，也許用來查找該區域的美食
        section_name = user_message[1:]    #把訊息去掉最前面的 #，取出純地區名稱
        responses = [handle_rests_recommand(user_id, section_name)]    #呼叫 handle_rests_recommand() 函式，傳入使用者 ID 與地區名稱，取得該地區推薦餐廳列表
    else:    #如果上面條件都不符合，就執行這個 else，也就是「其他聊天訊息」
        responses = [TextMessage(text='Got it!')]    #建立一個簡單的文字回應 'Got it!'，表示機器人收到了訊息，但沒有特別的處理邏輯
    '''
    根據訊息內容給出不同回應：
    sample → 測試訊息範例
    美食推薦 → 顯示選擇餐別
    #...餐 → 顯示區域選項
    #...區 → 推薦餐廳
    其他 → 回 "Got it!"
    '''

    with ApiClient(configuration) as api_client:    #使用 ApiClient（LINE 官方提供的 API 用戶端），並傳入 configuration 來建立連線設定，開啟一個「with 區塊」[建立 API 用戶端，包含憑證與連線資訊]
        line_bot_api = MessagingApi(api_client)    #建立一個 MessagingApi 的實例，來呼叫 LINE Messaging API 功能，例如回覆訊息、推送訊息等
        line_bot_api.reply_message_with_http_info(    #呼叫 reply_message_with_http_info() 方法，回覆訊息給使用者[呼叫 LINE API 回覆訊息，搭配 ReplyMessageRequest()]
            ReplyMessageRequest(    #建立一個 ReplyMessageRequest 請求物件，這是回覆訊息所需的格式
                reply_token=event.reply_token,    #指定回覆用的 reply_token，這是 LINE 傳來的臨時回覆憑證[用來回覆的憑證，來自 event，限時限用]
                messages=responses    #要回覆的訊息內容列表（前面程式碼已將訊息放入 responses 中，例如文字訊息、貼圖等）
            )
        )
    #建立 LINE API 用戶端並發送回覆
    '''第1行
    ApiClient 是與 LINE 平台溝通的主要工具（用來發送 API 請求）
    configuration 是你事先設定好的憑證、金鑰、伺服器位置等資訊（通常包含 Channel access token）
    with 的作用是確保這段程式碼執行完後自動釋放資源，避免記憶體或網路連線未釋放的問題
    '''
    '''第2行
    api_client 是上面建立的 API 連線物件
    MessagingApi 提供很多方法，例如：reply_message_with_http_info()、push_message()、get_profile() 等等
    '''
    '''第3行
    reply_message_with_http_info() 是 LINE Messaging API 中用來回覆訊息的方法（包含回應 metadata）
    與 reply_message() 不同的是：這個方法會回傳 HTTP 狀態碼、回應內容等，方便除錯與監控
    '''
    '''第5行
    每次使用者傳訊息，LINE 都會附上 reply_token
    你只能用一次這個 token，而且要在短時間內用完（大約 1 分鐘內）
    '''

def handle_choose_time():    #定義一個函式 handle_choose_time()，不需要參數。當使用者觸發某些條件時（如傳送「美食推薦」），會呼叫這個函式，產生一個按鈕選單訊息
    response = ButtonsTemplate(    #建立一個 ButtonsTemplate 物件，這是 LINE 提供的按鈕樣板訊息格式
        thumbnail_image_url='https://i.imgur.com/b9oaYpu.jpeg',    #設定按鈕樣板的上方圖片網址，這裡是用 Imgur 圖片
        title='歡迎使用!!',    #按鈕樣板的標題文字，會顯示在圖片下方
        text='請選擇要推薦的風格餐廳。',    #說明文字，提供進一步提示用途
        actions=[    #設定這個按鈕樣板的可點選動作清單，這裡是 3 個 MessageAction（也就是按鈕）
            MessageAction(text='#文青早餐', label='享用文青早點'),    #按鈕上顯示文字：享用文青早點。點下去後，會傳送文字訊息 #文青早餐 給 bot（觸發後續處理）
            MessageAction(text='#在地午餐', label='品嘗在地美食'),    #按鈕上顯示文字：品嘗在地美食。點下去後，會傳送文字訊息 #在地午餐 給 bot（觸發後續處理）
            MessageAction(text='#高檔晚餐', label='暢享高檔餐廳')     #按鈕上顯示文字：暢享高檔餐廳。點下去後，會傳送文字訊息 #高檔晚餐 給 bot（觸發後續處理）
        ]
    )
    return TemplateMessage(    #傳回一個 TemplateMessage 物件，這是實際用來發送給 LINE 使用者的格式
        type='template',    #指定訊息類型為 "template"（LINE 規定格式）
        altText="TemplateMessage",    #替代文字：當使用者使用的 LINE 版本太舊無法顯示按鈕樣板時，會顯示這段文字
        template=response    #把剛剛建立的 ButtonsTemplate 傳入這個 TemplateMessage
    )

def handle_choose_section(user_id, time_message):    #定義函式 handle_choose_section()，接收兩個參數
    def create_quick_reply_item(section_name):    #用來根據傳入的「區域名稱」，建立一個快速回覆項目（Quick Reply）
        return QuickReplyItem(action=MessageAction(text=f'#{section_name}', label=f'{section_name}'))    #label=f'{section_name}'：按鈕顯示的文字，text=f'#{section_name}'：點按後會傳出的訊息，會被後續處理

    if time_message == '#文青早餐':    #根據使用者選擇的時段，從 rest_dict 字典中取得對應的餐廳資料分組（例如早餐餐廳）
        rest_groups = rest_dict['breakfast_rest']
    elif time_message == '#在地午餐':
        rest_groups = rest_dict['lunch_rest']
    elif time_message == '#高檔晚餐':
        rest_groups = rest_dict['dinner_rest']
    #rest_dict 是一個全域字典，應該包含三個 key（如 'breakfast_rest', 'lunch_rest', 'dinner_rest'）
    #每個 key 裡面對應的 rest_groups 是一個餐廳區域分類群（dict-like object）
    
    rest_recommand_memory[user_id] = rest_groups    #記錄使用者的選擇結果（早餐/午餐/晚餐對應的餐廳群），存在全域變數 rest_recommand_memory 中
    #以 user_id 為 key，儲存使用者目前對應的餐廳區域資料
    #日後根據這個資訊可以推薦不同區域的餐廳

    sections = rest_groups.groups.keys()    #取得餐廳分組中的所有「區域名稱」，例如「中正區」、「信義區」等等。rest_groups.groups 是一個 dict-like 結構，裡面每個 key 是一個區域
    quick_reply_items = [create_quick_reply_item(section) for section in sections]    #用 list comprehension 建立所有區域的快速回覆按鈕項目
    quick_reply_body = QuickReply(items=quick_reply_items)    #建立一個 QuickReply 物件，包含上面建立的所有快速回覆項目

    return TextMessage(    #回傳一個 LINE 的文字訊息物件 TextMessage
        text="請選擇你的所在區域~",    #訊息內容是 "請選擇你的所在區域~"
        quickReply=quick_reply_body    #下方會顯示快速回覆按鈕（Quick Reply）供使用者選擇區域
    )
  #根據餐別讀取對應的區域群組，並用 quick reply 顯示區域選項
'''第1行
user_id：使用者的 LINE ID（用來記錄使用者狀態）
time_message：使用者剛剛選擇的時間類型（如 #文青早餐）
'''
'''def函式整段概要:
1.選擇時段:使用者點選 #文青早餐 等
2.查找資料:從 rest_dict 中取得對應餐廳群組
3.記錄狀態:儲存在 rest_recommand_memory[user_id]
4.建立按鈕:針對各區域建立 Quick Reply 按鈕
5.回傳訊息:要求使用者選擇所在區域（附帶快速回覆）
'''

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
