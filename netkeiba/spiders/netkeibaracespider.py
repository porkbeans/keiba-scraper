import re
from datetime import datetime, timedelta, timezone

import scrapy


class NetkeibaRaceSpider(scrapy.Spider):
    name = 'NetkeibaRaceSpider'

    def __init__(self, *args, **kwargs):
        super(NetkeibaRaceSpider, self).__init__(*args, **kwargs)

        today = datetime.now(tz=timezone(timedelta(hours=9)))

        self.start_year = kwargs.get('start_year', f'{today.year}')
        self.start_month = kwargs.get('start_month', f'{today.month}')
        self.end_year = kwargs.get('end_year', f'{today.year}')
        self.end_month = kwargs.get('end_month', f'{today.month}')

    def parse(self, response: scrapy.http.Response, **kwargs):
        race_name = response.css('dl.racedata h1::text').get()
        race_conditions = re.split(r'\xa0/?\xa0', response.css('dl.racedata diary_snap_cut span::text').get())

        race_data = response.meta['race_data']
        race_data['race_name'] = race_name
        race_data['race_condition'] = dict()
        race_data['race_condition']['has_turf'] = '芝' in race_conditions[0]
        race_data['race_condition']['has_dirt'] = 'ダ' in race_conditions[0]
        race_data['race_condition']['has_obstacle'] = '障' in race_conditions[0]

        distance_match = re.match(r'\D*\s*0*(?P<distance>\d+)m', race_conditions[0])
        if distance_match is None:
            race_data['race_distance'] = None
        else:
            race_data['race_distance'] = int(distance_match.group('distance'))

        race_data['other_data'] = []

        for condition in race_conditions[1:]:
            if len(condition) == 0:
                continue

            key, val = condition.split(' : ')
            if key == '天候':
                race_data['race_condition']['weather'] = val
            elif key == '芝':
                race_data['race_condition']['turf_condition'] = val
            elif key == 'ダート':
                race_data['race_condition']['dirt_condition'] = val
            elif key == '発走':
                race_data['start_time'] = f"{race_data['race_date']} {val}"
            else:
                race_data['other_data'].append(f'{key}={val}')

        race_data['race_results'] = []
        for result in response.css('table.race_table_01 tr'):
            # Skip header row
            if result.xpath('./th').get() is not None:
                continue

            race_data['race_results'].append({
                'finishing_order': result.xpath('./td[1]/text()').get(),
                'passing_order': result.xpath('./td[12]/text()').get(),
                'time_record': result.xpath('./td[8]/text()').get(),
                'sprint_time_record': result.xpath('./td[13]/text()').get(),
                'frame_number': result.xpath('./td[2]//text()').get(),
                'horse_number': result.xpath('./td[3]/text()').get(),
                'horse_id': result.xpath('./td[4]/a/@href').re_first(r'/horse/(.+)/'),
                'horse_name': result.xpath('./td[4]/a/text()').get(),
                'horse_sex': result.xpath('./td[5]/text()').re_first(r'(\w)\d+'),
                'horse_age': result.xpath('./td[5]/text()').re_first(r'\w(\d+)'),
                'horse_weight': result.xpath('./td[15]/text()').re_first(r'(\d+)\([+\-]?\d+\)'),
                'horse_weight_diff': result.xpath('./td[15]/text()').re_first(r'\d+\(([+\-]?\d+)\)'),
                'jockey_id': result.xpath('./td[7]/a/@href').re_first(r'/jockey/(.+)/'),
                'jockey_name': result.xpath('./td[7]/a/text()').get(),
                'jockey_weight': result.xpath('./td[6]/text()').get(),
                'trainer_id': result.xpath('./td[19]/a/@href').re_first(r'/trainer/(.+)/'),
                'trainer_name': result.xpath('./td[19]/a/text()').get(),
                'owner_id': result.xpath('./td[20]/a/@href').re_first(r'/owner/(.+)/'),
                'owner_name': result.xpath('./td[20]/a/text()').get(),
            })

        yield race_data

    def parse_search_page(self, response: scrapy.http.Response):
        for race_summary in response.xpath('//table[@summary="レース検索結果"]//tr'):
            # Skip header row
            if race_summary.xpath('./th').get() is not None:
                continue

            race_data = {
                'race_date': race_summary.xpath('./td[1]/a/text()').get().replace('/', '-'),
                'location_id': race_summary.xpath('./td[2]/a/@href').re_first(r'/race/sum/(.+)/.+/'),
                'location_name': race_summary.xpath('./td[2]/a/text()').get(),
                'race_order_in_day': race_summary.xpath('./td[4]/text()').get(),
                'race_id': race_summary.xpath('./td[5]/a/@href').re_first(r'/race/(.+)/'),
            }

            yield scrapy.Request(
                url=f"https://db.netkeiba.com/race/{race_data['race_id']}/",
                encoding='euc-jp',
                meta={
                    'race_data': race_data
                }
            )

        serial = response.xpath('//form[@name="sort"]/input[@name="serial"]/@value').get()
        next_link = response.xpath('//div[@class="pager"]/a[text()="次"]/@href')
        if next_link.get() is not None:
            yield scrapy.FormRequest(
                url='https://db.netkeiba.com/',
                formdata={
                    'pid': 'race_list',
                    'serial': serial,
                    'sort_key': 'date',
                    'sort_type': 'desc',
                    'page': next_link.re_first(r'^javascript:paging\(\'(\d+)\'\)$'),
                },
                encoding='euc-jp',
                callback=self.parse_search_page,
            )

    def start_requests(self):
        return [
            scrapy.FormRequest(
                url='https://db.netkeiba.com/',
                formdata={
                    'pid': 'race_list',
                    'word': '',
                    'start_year': self.start_year,
                    'start_mon': self.start_month,
                    'end_year': self.end_year,
                    'end_mon': self.end_month,
                    'kyori_min': '',
                    'kyori_max': '',
                    'sort': 'date',
                    'list': '20',
                },
                encoding='euc-jp',
                callback=self.parse_search_page
            ),
        ]
