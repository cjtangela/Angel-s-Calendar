from pathlib import Path
from datetime import datetime, timedelta, timezone, date
import re
import requests
from bs4 import BeautifulSoup
from lunardate import LunarDate

ROOT = Path(__file__).resolve().parent
DOCS = ROOT / 'docs'
BJ_GEONAME = '1816670'
NOWSTAMP = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
MONTH_CN = {1:'正月',2:'二月',3:'三月',4:'四月',5:'五月',6:'六月',7:'七月',8:'八月',9:'九月',10:'十月',11:'冬月',12:'腊月'}
DAY_CN = {1:'初一',2:'初二',3:'初三',4:'初四',5:'初五',6:'初六',7:'初七',8:'初八',9:'初九',10:'初十',11:'十一',12:'十二',13:'十三',14:'十四',15:'十五',16:'十六',17:'十七',18:'十八',19:'十九',20:'二十',21:'廿一',22:'廿二',23:'廿三',24:'廿四',25:'廿五',26:'廿六',27:'廿七',28:'廿八',29:'廿九',30:'三十'}

def header(name, tz, desc, color):
    return '
'.join(['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//Perplexity//Spiritual Practice Calendar//CN','CALSCALE:GREGORIAN','METHOD:PUBLISH',f'X-WR-CALNAME:{name}',f'X-WR-TIMEZONE:{tz}',f'X-WR-CALDESC:{desc}',f'X-APPLE-CALENDAR-COLOR:{color}']) + '
'

def event_block(uid, start_date, end_date, summary, description):
    return '
'.join(['BEGIN:VEVENT',f'UID:{uid}',f'DTSTAMP:{NOWSTAMP}',f'DTSTART;VALUE=DATE:{start_date.strftime("%Y%m%d")}',f'DTEND;VALUE=DATE:{end_date.strftime("%Y%m%d")}',f'SUMMARY:{summary}',f'DESCRIPTION:{description}','TRANSP:TRANSPARENT','END:VEVENT'])

def write_calendar(path, cal_name, tz, desc, color, events):
    path.write_text(header(cal_name,tz,desc,color) + '
'.join(events) + '
END:VCALENDAR
', encoding='utf-8')

def extract_events(text):
    return re.findall(r'BEGIN:VEVENT\n.*?\nEND:VEVENT', text, flags=re.S)

def lunar_events_for_years(start_year, years_ahead):
    six_events, ten_events = [], []
    six_days, ten_days = {8,14,15,23,29,30}, {1,8,14,15,18,23,24,28,29,30}
    d, end = date(start_year,1,1), date(start_year+years_ahead,1,1)
    while d < end:
        lunar = LunarDate.fromSolarDate(d.year, d.month, d.day)
        if not getattr(lunar, 'isLeapMonth', False):
            if lunar.day in six_days:
                six_events.append((d, event_block(f'six-{d.isoformat()}@jitong-calendar', d, d+timedelta(days=1), f'斋戒-{DAY_CN[lunar.day]}', f'佛教六斋日；农历{lunar.month}月{DAY_CN[lunar.day]}。')))
            if lunar.day in ten_days:
                ten_events.append((d, event_block(f'ten-{d.isoformat()}@jitong-calendar', d, d+timedelta(days=1), f'十斋日-{DAY_CN[lunar.day]}', f'佛教十斋日；农历{lunar.month}月{DAY_CN[lunar.day]}。')))
        d += timedelta(days=1)
    for y in range(start_year, start_year+years_ahead):
        for m in [1,5,9]:
            s = LunarDate(y, m, 1, False).toSolarDate()
            e = LunarDate(y, m+1, 1, False).toSolarDate() if m < 12 else LunarDate(y+1, 1, 1, False).toSolarDate()
            ten_events.append((s, event_block(f'longfast-{y}-{m:02d}@jitong-calendar', s, e, f'长斋月-{MONTH_CN[m]}', f'佛教三长斋月：农历{MONTH_CN[m]}。')))
    six_events.sort(key=lambda x: x[0]); ten_events.sort(key=lambda x: x[0])
    return [b for _,b in six_events], [b for _,b in ten_events]

def scrape_beijing_ekadashi(year):
    url = f'https://www.drikpanchang.com/vrats/ekadashidates.html?geoname-id={BJ_GEONAME}&year={year}'
    html = requests.get(url, timeout=40, headers={'User-Agent':'Mozilla/5.0'}).text
    soup = BeautifulSoup(html, 'html.parser')
    pairs = []
    for card in soup.select('div.dpHalfCard'):
        dnode = card.select_one('.dpEventDateTitle')
        anode = card.select_one('.dpSingleEventLink a')
        if not dnode or not anode: continue
        title = anode.get_text(' ', strip=True)
        if 'Ekadashi' not in title: continue
        m = re.search(r'([A-Za-z]+)\s+(\d{1,2}),\s*(\d{4})', dnode.get_text(' ', strip=True))
        if not m: continue
        ds = datetime.strptime(f"{m.group(1)} {m.group(2)} {m.group(3)}", '%B %d %Y').date()
        pairs.append((ds, title))
    out, seen = [], set()
    for ds, title in sorted(pairs, key=lambda x: (x[0], x[1])):
        key = (ds.isoformat(), title)
        if key not in seen:
            seen.add(key)
            out.append((ds, title))
    return out

def fasting_events(start_year, years_ahead):
    events = []
    for y in range(start_year, start_year+years_ahead):
        for ds, title in scrape_beijing_ekadashi(y):
            slug = re.sub(r'[^a-z0-9]+','-',title.lower()).strip('-')
            events.append((ds, event_block(f'fast-{ds.isoformat()}-{slug}@jitong-calendar', ds, ds+timedelta(days=1), '断食日', f'印度教断食日：{title}（按北京时间标准）。')))
    events.sort(key=lambda x: (x[0], x[1]))
    return [b for _,b in events]

if __name__ == '__main__':
    start_year = datetime.now().year
    years_ahead = 5
    six, ten = lunar_events_for_years(start_year, years_ahead)
    fast = fasting_events(start_year, years_ahead)
    spiritual = (DOCS/'spiritual.ics').read_text(encoding='utf-8')
    write_calendar(DOCS/'six-zhai.ics', '六斋日（绿色）', 'America/New_York', '佛教六斋日订阅源。建议在 Apple Calendar 设为绿色。', '#34C759', six)
    write_calendar(DOCS/'extra-ten-zhai.ics', '十斋日（橘色）', 'America/New_York', '佛教十斋日订阅源，已含三长斋月。建议在 Apple Calendar 设为橘色。', '#FF9F0A', ten)
    write_calendar(DOCS/'fasting.ics', '断食日（黄色）', 'Asia/Shanghai', '印度教断食日订阅源，按北京时间标准自动更新。建议在 Apple Calendar 设为黄色。', '#FFD60A', fast)
    combined = []
    for txt in [(DOCS/'six-zhai.ics').read_text(encoding='utf-8'), (DOCS/'extra-ten-zhai.ics').read_text(encoding='utf-8'), spiritual, (DOCS/'fasting.ics').read_text(encoding='utf-8')]:
        for blk in extract_events(txt):
            m = re.search(r'DTSTART;VALUE=DATE:(\d{8})', blk)
            combined.append((m.group(1) if m else '99999999', blk))
    combined.sort(key=lambda x: x[0])
    write_calendar(DOCS/'combined.ics', '修行日历（合并）', 'America/New_York', '六斋日、十斋日、灵性与断食日合并订阅源。', '#8E8E93', [b for _,b in combined])
