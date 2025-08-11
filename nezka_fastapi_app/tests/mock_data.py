import uuid

# Stocks report mock data

sid = str(uuid.uuid4())

stocks_report_mock_response = {
        'data': {
            'data': {
                'items': [
                    {'nmId': 123456, 'stock': 15, 'warehouse': 'Москва'},
                    {'nmId': 654321, 'stock': 30, 'warehouse': 'Казань'},
                ]
            }
        },
        'sid': sid
    }

# Adv stat words mock data

adv_stat_words_mock_response = {
    "words": {
        "phrase": [],
        "strong": [],
        "excluded": [],
        "pluse": [
            "детское постельное белье для мальчика 1.5"
        ],
        "keywords": [
            {
                "keyword": "постельное белье 1.5",
                "count": 772
            }
        ],
        "fixed": True
    },
    "stat": [
        {
            "advertId": 7703570,
            "keyword": "Всего по кампании",
            "advertName": "",
            "campaignName": "Бельё",
            "begin": "2023-07-03T15:15:38.287441+03:00",
            "end": "2023-07-03T15:15:38.287441+03:00",
            "views": 1846,
            "clicks": 73,
            "frq": 1.03,
            "ctr": 3.95,
            "cpc": 7.88,
            "duration": 769159,
            "sum": 575.6
        },
        {
            "advertId": 7703570,
            "keyword": "постельное белье 1.5 детское",
            "advertName": "",
            "campaignName": "Бельё",
            "begin": "2023-07-03T15:15:38.287441+03:00",
            "end": "2023-07-03T15:15:38.287441+03:00",
            "views": 1846,
            "clicks": 73,
            "frq": 1.03,
            "ctr": 3.95,
            "cpc": 7.88,
            "duration": 769159,
            "sum": 575.6
        }
    ]
}
