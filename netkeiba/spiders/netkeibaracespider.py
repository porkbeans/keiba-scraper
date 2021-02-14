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
        race_data['race_condition'] = {
            'has_turf': '芝' in race_conditions[0],
            'has_dirt': 'ダ' in race_conditions[0],
            'has_obstacle': '障' in race_conditions[0],
        }

        if (distance_match := re.match(r'\D*\s*0*(?P<distance>\d+)m', race_conditions[0])) is None:
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
        for result in response.css('table.race_table_01 tr')[1:]:
            columns = result.xpath('.//td')
            num_cols = len(columns)

            xpath_text = './/text()'
            xpath_link_url = './a/@href'
            xpath_link_text = './a/text()'

            if num_cols == 21:
                race_data['race_results'].append({
                    'finishing_order': columns[0].xpath(xpath_text).get(),
                    'passing_order': columns[10].xpath(xpath_text).get(),
                    'time_record': columns[7].xpath(xpath_text).get(),
                    'time_record_homestretch': columns[11].xpath(xpath_text).get(),
                    'frame_number': columns[1].xpath(xpath_text).get(),
                    'horse_number': columns[2].xpath(xpath_text).get(),
                    'horse_id': columns[3].xpath(xpath_link_url).re_first(r'/horse/(.+)/'),
                    'horse_name': columns[3].xpath(xpath_link_text).get(),
                    'horse_sex': columns[4].xpath(xpath_text).re_first(r'(\w)\d+'),
                    'horse_age': columns[4].xpath(xpath_text).re_first(r'\w(\d+)'),
                    'horse_weight': columns[14].xpath(xpath_text).re_first(r'(\d+)\([+\-]?\d+\)'),
                    'horse_weight_diff': columns[14].xpath(xpath_text).re_first(r'\d+\(([+\-]?\d+)\)'),
                    'jockey_id': columns[6].xpath(xpath_link_url).re_first(r'/jockey/(.+)/'),
                    'jockey_name': columns[6].xpath(xpath_link_text).get(),
                    'jockey_weight': columns[5].xpath(xpath_text).get(),
                    'trainer_id': columns[18].xpath(xpath_link_url).re_first(r'/trainer/(.+)/'),
                    'trainer_name': columns[18].xpath(xpath_link_text).get(),
                    'owner_id': columns[19].xpath(xpath_link_url).re_first(r'/owner/(.+)/'),
                    'owner_name': columns[19].xpath(xpath_link_text).get(),
                    'prize': columns[20].xpath(xpath_text).get(),
                })
            elif num_cols == 14:
                race_data['race_results'].append({
                    'finishing_order': columns[0].xpath(xpath_text).get(),
                    'passing_order': None,
                    'time_record': columns[7].xpath(xpath_text).get(),
                    'time_record_homestretch': None,
                    'frame_number': columns[1].xpath(xpath_text).get(),
                    'horse_number': columns[2].xpath(xpath_text).get(),
                    'horse_id': columns[3].xpath(xpath_link_url).re_first(r'/horse/(.+)/'),
                    'horse_name': columns[3].xpath(xpath_link_text).get(),
                    'horse_sex': columns[4].xpath(xpath_text).re_first(r'(\w)\d+'),
                    'horse_age': columns[4].xpath(xpath_text).re_first(r'\w(\d+)'),
                    'horse_weight': None,
                    'horse_weight_diff': None,
                    'jockey_id': columns[6].xpath(xpath_link_url).re_first(r'/jockey/(.+)/'),
                    'jockey_name': columns[6].xpath(xpath_link_text).get(),
                    'jockey_weight': columns[5].xpath(xpath_text).get(),
                    'trainer_id': columns[11].xpath(xpath_link_url).re_first(r'/trainer/(.+)/'),
                    'trainer_name': columns[11].xpath(xpath_link_text).get(),
                    'owner_id': columns[12].xpath(xpath_link_url).re_first(r'/owner/(.+)/'),
                    'owner_name': columns[12].xpath(xpath_link_text).get(),
                    'prize': columns[13].xpath(xpath_text).get(),
                })

        yield race_data

    def parse_search_page(self, response: scrapy.http.Response):
        for race_summary in response.xpath('//table[@summary="レース検索結果"]//tr')[1:]:
            race_data = {
                'race_date': race_summary.xpath('./td[1]/a/text()').get().replace('/', '-'),
                'location_id': race_summary.xpath('./td[2]/a/@href').re_first(r'/race/sum/(.+)/.+/'),
                'location_name': race_summary.xpath('./td[2]/a/text()').get(),
                'race_order_in_day': race_summary.xpath('./td[4]/text()').get(),
                'race_id': race_summary.xpath('./td[5]/a/@href').re_first(r'/race/(.+)/'),
                'num_horses': race_summary.xpath('./td[8]/text()').get(),
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
                    'list': '100',
                },
                encoding='euc-jp',
                callback=self.parse_search_page
            ),
        ]
