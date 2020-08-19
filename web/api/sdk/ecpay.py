from . import ecpay_payment_sdk
from . import ecpay_logistic_sdk
import json

from datetime import datetime
from log import logger
import os
import copy
import collections
from urllib.parse import quote_plus, parse_qsl, parse_qs
import hashlib

host_url_map = dict(
    prod='https://ezgo-buy.com/',
    dev='https://e7918ba7bc46.ngrok.io/',
    test='https://li1858-106.members.linode.com/'
)
ENV = os.environ.get('ENV')
host_url = host_url_map[ENV]


def check_env(env):
    return env != 'prod'


if check_env(ENV):
    ecpay_keys = dict(
        MerchantID='2000132',
        HashKey='5294y06JbISpM5x9',
        HashIV='v77hoKGq4kWxNNIS'
    )

else:
    ecpay_keys = dict(
        MerchantID='3176819',
        HashKey='1KNuJ3exSlgXEtrp',
        HashIV='YNOdMJKcofOCyC1x'
    )
logger.info(f'ENV: {ENV} {host_url}')
logger.info(f'ecpay_keys: {ecpay_keys}')
payment_type = dict(
    WebATM_TAISHIN='台新銀行 WebATM',
    WebATM_ESUN='玉山銀行 WebATM(暫不提供)',
    WebATM_BOT='台灣銀行 WebATM',
    WebATM_FUBON='台北富邦 WebATM',
    WebATM_CHINATRUST='中國信託 WebATM',
    WebATM_FIRST='第一銀行 WebATM(暫不提供)',
    WebATM_CATHAY='國泰世華 WebATM',
    WebATM_MEGA='兆豐銀行 WebATM',
    WebATM_LAND='土地銀行 WebATM',
    WebATM_TACHONG='大眾銀行 WebATM(2018 年已併到元大銀行)',
    WebATM_SINOPAC='永豐銀行 WebATM',
    ATM_TAISHIN='台新銀行 ATM',
    ATM_ESUN='玉山銀行 ATM(暫不提供)',
    ATM_BOT='台灣銀行 ATM',
    ATM_FUBON='台北富邦 ATM',
    ATM_CHINATRUST='中國信託 ATM',
    ATM_FIRST='第一銀行 ATM(暫不提供)',
    ATM_LAND='土地銀行 ATM',
    ATM_CATHAY='國泰世華銀行 ATM',
    ATM_TACHONG='大眾銀行 ATM(2018 年已併到元大銀行)',
    CVS_CVS='超商代碼繳款',
    CVS_OK='OK 超商代碼繳款',
    CVS_FAMILY='全家超商代碼繳款',
    CVS_HILIFE='萊爾富超商代碼繳款',
    CVS_IBON='7-11 ibon 代碼繳款',
    BARCODE_BARCODE='超商條碼繳款',
    Credit_CreditCard='信用卡',
)


def create_html(callback_url, order, lang=''):
    import random
    import string
    product_shot = json.loads(order.product_shot)
    names = [f'{el["cn_name"]} X {el["quantity"]}' for el in product_shot]
    product_name = "#".join(names)
    trader_no = order.order_number + ''.join(random.choices(string.digits, k=2))
    return_url = f'{host_url}api/ecpay/return_url/'
    payment_info_url = f'{host_url}api/ecpay/payment_info_url/'
    logger.info('ecpay create html: %s %s', trader_no, return_url)
    order_params = {
        'MerchantTradeNo': trader_no,
        'StoreID': '',
        'MerchantTradeDate': datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
        'PaymentType': 'aio',
        'TotalAmount': int(order.total_price),
        'TradeDesc': '177',
        'ItemName': product_name,
        'ReturnURL': return_url,
        'ChoosePayment': 'ALL',
        'ClientBackURL': f'{callback_url}?order={order.id}',
        'Remark': order.order_remark,
        'ChooseSubPayment': '',
        'NeedExtraPaidInfo': 'Y',
        'DeviceSource': '',
        'IgnorePayment': '',
        'PlatformID': '',
        'InvoiceMark': 'N',
        'CustomField1': '',
        'CustomField2': '',
        'CustomField3': '',
        'CustomField4': '',
        'EncryptType': 1,
    }

    extend_params_1 = {
        'ExpireDate': 7,
        'ClientRedirectURL': '',
    }

    extend_params_2 = {
        'StoreExpireDate': 15,
        'Desc_1': '',
        'Desc_2': '',
        'Desc_3': '',
        'Desc_4': '',
        'PaymentInfoURL': payment_info_url,
        'ClientRedirectURL': '',
    }

    extend_params_3 = {
        'BindingCard': 0,
        'MerchantMemberID': '',
        'Language': lang,
    }

    extend_params_4 = {
        'Redeem': 'N',
        'UnionPay': 0,
    }

    # 建立實體
    ecpay_payment_sdk_instance = ecpay_payment_sdk.ECPayPaymentSdk(
        **ecpay_keys
    )

    # 合併延伸參數
    order_params.update(extend_params_1)
    order_params.update(extend_params_2)
    order_params.update(extend_params_3)
    order_params.update(extend_params_4)
    # 產生綠界訂單所需參數
    # order_params['OrderResultURL'] = order_result_url
    final_order_params = ecpay_payment_sdk_instance.create_order(order_params)

    # 產生 html 的 form 格式
    if check_env(ENV):
        action_url = 'https://payment-stage.ecpay.com.tw/Cashier/AioCheckOut/V5'  # 測試環境
    else:
        action_url = 'https://payment.ecpay.com.tw/Cashier/AioCheckOut/V5'  # 正式環境
    logger.info(
        'action_url: %s params: %s', action_url, final_order_params
    )
    html = ecpay_payment_sdk_instance.gen_html_post_form(action_url, final_order_params)
    return html


def create_shipping_map(sub_type, member_id, callback_url):
    assert sub_type in ['FAMI', 'UNIMART', 'HILIFE']
    if check_env(ENV) is False:
        sub_type += 'C2C'

    cvs_map_params = {
        "MerchantTradeNo": "anyno",
        "LogisticsType": "CVS",
        # 若申請類型為 B2C，只能串參數為 FAMI、UNIMART、HILIFE
        # 若申請類型為 C2C，只能串參數為 FAMIC2C、UNIMARTC2C、HILIFEC2C

        "LogisticsSubType": sub_type,
        "IsCollection": "Y",
        "ServerReplyURL": f'{host_url}api/ecpay/map_return_url/',
        "ExtraData": f'{member_id}###{callback_url}',
        "Device": ecpay_logistic_sdk.Device['PC'],
    }

    # 建立實體
    instance = ecpay_logistic_sdk.ECPayLogisticSdk(
        **ecpay_keys
    )
    logger.info('shipping keys: %s', ecpay_keys)
    logger.info('sub_type: %s', sub_type)

    try:
        # 產生綠界物流訂單所需參數
        final_params = instance.cvs_map(cvs_map_params)

        # 產生 html 的 form 格式
        if check_env(ENV):
            action_url = 'https://logistics-stage.ecpay.com.tw/Express/map'  # 測試環境
        else:
            action_url = 'https://logistics.ecpay.com.tw/Express/map'  # 正式環境
        html = instance.gen_html_post_form(action_url, final_params)
        return html
    except Exception as error:
        print('An exception happened: ' + str(error))


def generate_check_value(self, params):
    _params = copy.deepcopy(params)

    if 'CheckMacValue' in _params:
        _params.pop('CheckMacValue')

    ordered_params = collections.OrderedDict(
        sorted(_params.items(), key=lambda k: k[0]))

    encoding_lst = []
    encoding_lst.append('HashKey=%s&' % self['HashKey'])
    encoding_lst.append(''.join(
        ['{}={}&'.format(key, value) for key, value in ordered_params.items()]))
    encoding_lst.append('HashIV=%s' % self['HashIV'])

    safe_characters = '-_.!*()'

    encoding_str = ''
    for encoding_ls in encoding_lst:
        encoding_str = f'{encoding_str}{encoding_ls}'
    encoding_str = quote_plus(
        str(encoding_str), safe=safe_characters).lower()

    check_mac_value = hashlib.md5(
        encoding_str.encode('utf-8')).hexdigest().upper()
    return check_mac_value


def shipping(sub_type, store_id, order):
    import re
    if check_env(ENV) is False and 'C2C' not in sub_type:
        logger.info('原來是這邊沒有加入C2C: %s', sub_type)
        sub_type += 'C2C'
    product_shot = json.loads(order.product_shot)
    names = [f'{el["cn_name"]} X {el["quantity"]}' for el in product_shot]
    product_name = " ".join(names)
    product_name = re.sub(r'\W', '', product_name)
    service_replay_url = f'{host_url}api/ecpay/shipping_return_url/'
    logger.info('shipping url: %s', service_replay_url)
    create_shipping_order_params = {
        'MerchantTradeNo': order.order_number,
        'MerchantTradeDate': datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
        'LogisticsType': 'CVS',
        'LogisticsSubType': sub_type,
        'IsCollection': 'Y' if order.pay_type == 1 else 'N',
        'GoodsAmount': int(order.total_price),
        'CollectionAmount': int(order.total_price),
        'GoodsName': product_name[:20],
        'SenderName': 'EZGO',
        'SenderCellPhone': '0911222333',
        'ReceiverName': order.shipping_name,
        'ReceiverCellPhone': order.phone,
        'TradeDesc': '177',
        'ServerReplyURL': service_replay_url,
        'LogisticsC2CReplyURL': service_replay_url,
        'ClientReplyURL': '',
        'Remark': '' if not order.remark else order.remark,
        'PlatformID': '',
    }

    shipping_cvs_params = {
        'ReceiverStoreID': store_id,
        'ReturnStoreID': store_id,
    }

    # 更新及合併參數
    create_shipping_order_params.update(shipping_cvs_params)

    # 建立實體
    instance = ecpay_logistic_sdk.ECPayLogisticSdk(
        **ecpay_keys
    )

    if not order.to_store:
        create_shipping_order_params['LogisticsType'] = 'HOME'
        create_shipping_order_params['LogisticsSubType'] = 'TCAT'
        create_shipping_order_params['SenderAddress'] = '高雄市前金區中正四路148號11F'
        create_shipping_order_params['SenderZipCode'] = '801'
        create_shipping_order_params['ReceiverZipCode'] = order.shipping_area
        create_shipping_order_params['ReceiverAddress'] = order.shipping_address
        create_shipping_order_params['Temperature'] = '0001'
        create_shipping_order_params['CheckMacValue'] = generate_check_value(ecpay_keys, create_shipping_order_params)

    try:
        # 介接路徑
        if check_env(ENV):
            action_url = 'https://logistics-stage.ecpay.com.tw/Express/Create'  # 測試環境
        else:
            action_url = 'https://logistics.ecpay.com.tw/Express/Create'  # 正式環境
        logger.info('shiiping url: %s', action_url)
        logger.info('order params: %s', create_shipping_order_params)
        # 建立物流訂單並接收回應訊息
        reply_result = instance.create_shipping_order(
            action_url=action_url,
            client_parameters=create_shipping_order_params)
        logger.info('reply: %s', reply_result)
        return reply_result

    except Exception as error:
        print('An exception happened: ' + str(error))
