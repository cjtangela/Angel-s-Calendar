from pathlib import Path
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from lunardate import LunarDate
import ephem
import argparse

ROOT = Path(__file__).resolve().parent
DOCS = ROOT / 'docs'
DOCS.mkdir(exist_ok=True)

DAY_LABELS = {1:'初一',8:'初八',14:'十四',15:'十五',18:'十八',23:'廿三',24:'廿四',28:'廿八',29:'廿九',30:'三十'}


def lunar_label(day: int) -> str:
    return DAY_LABELS[day]


def month_length(ld: LunarDate) -> int:
    try:
        LunarDate(ld.year, ld.month, 30, ld.isLeapMonth).toSolarDate()
        return 30
    except ValueError:
        return 29


def classify_zhai(g: date):
    ld = LunarDate.fromSolarDate(g.year, g.month, g.day)
    d = ld.day
    if d in {8, 14, 15, 23, 29, 30}:
        return 'six', lunar_label(d), ld
    if d == 28:
        return ('six' if month_length(ld) == 29 else 'extra'), lunar_label(d), ld
    if d in {1, 18, 24}:
        return 'extra', lunar_label(d), ld
    return None, None, ld


def moon_dates(start_year: int, end_year: int, tz_name: str):
    tz = ZoneInfo(tz_name)
    start_dt = datetime(start_year, 1, 1, tzinfo=tz)
    end_dt = datetime(end_year + 1, 1, 1, tzinfo=tz)
    out = []
    seen = set()

    cursor = ephem.Date((start_dt - timedelta(days=40)).astimezone(timezone.utc))
    while True:
        nm = ephem.next_new_moon(cursor)
        nmdt = ephem.Date(nm).datetime().replace(tzinfo=timezone.utc).astimezone(tz)
        if nmdt >= end_dt:
            break
        if nmdt >= start_dt:
            key = ('新月', nmdt.date())
            if key not in seen:
                out.append(key)
                seen.add(key)
        cursor = ephem.Date(nm + 1 / 24)

    cursor = ephem.Date((start_dt - timedelta(days=40)).astimezone(timezone.utc))
    while True:
        fm = ephem.next_full_moon(cursor)
        fmdt = ephem.Date(fm).datetime().replace(tzinfo=timezone.utc).astimezone(tz)
        if fmdt >= end_dt:
            break
        if fmdt >= start_dt:
            key = ('满月', fmdt.date())
            if key not in seen:
                out.append(key)
                seen.add(key)
        cursor = ephem.Date(fm + 1 / 24)

    out.sort(key=lambda x: x[1])
    return out


def stargates(start_year: int, end_year: int):
    return [(f'星门 {m}.{m}', date(y, m, m)) for y in range(start_year, end_year + 1) for m in range(1, 13)]


def escape_ics(text: str) -> str:
    return text.replace('\', '\\').replace(';', '\;').replace(',', '\,').replace('
', '\n')


def fold_ics(line: str):
    b = line.encode('utf-8')
    if len(b) <= 73:
        return [line]
    parts = []
    current = b''
    for ch in line:
        enc = ch.encode('utf-8')
        if len(current) + len(enc) > 73:
            parts.append(current.decode('utf-8'))
            current = enc
        else:
            current += enc
    if current:
        parts.append(current.decode('utf-8'))
    return [parts[0]] + [' ' + p for p in parts[1:]]


def make_event_lines(uid, day: date, summary: str, description: str):
    fields = [
        'BEGIN:VEVENT',
        f'UID:{uid}',
        f'DTSTAMP:{datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")}',
        f'DTSTART;VALUE=DATE:{day.strftime("%Y%m%d")}',
        f'DTEND;VALUE=DATE:{(day + timedelta(days=1)).strftime("%Y%m%d")}',
        f'SUMMARY:{escape_ics(summary)}',
        f'DESCRIPTION:{escape_ics(description)}',
        'TRANSP:TRANSPARENT',
        'END:VEVENT',
    ]
    out = []
    for field in fields:
        out.extend(fold_ics(field))
    return out


def write_calendar(path: Path, calname: str, color: str, desc: str, events, tz_name: str):
    lines = [
        'BEGIN:VCALENDAR',
        'VERSION:2.0',
        'PRODID:-//Perplexity//Spiritual Practice Calendar//CN',
        'CALSCALE:GREGORIAN',
        'METHOD:PUBLISH',
        f'X-WR-CALNAME:{escape_ics(calname)}',
        f'X-WR-TIMEZONE:{tz_name}',
        f'X-WR-CALDESC:{escape_ics(desc)}',
        f'X-APPLE-CALENDAR-COLOR:{color}',
    ]
    for event in events:
        lines.extend(make_event_lines(*event))
    lines.append('END:VCALENDAR')
    path.write_text('
'.join(lines) + '
', encoding='utf-8')


def generate(start_year: int, end_year: int, tz_name: str):
    six_events, extra_events, spiritual_events, all_events = [], [], [], []

    for year in range(start_year, end_year + 1):
        current = date(year, 1, 1)
        while current.year == year:
            kind, label, ld = classify_zhai(current)
            if kind == 'six':
                summary = f'斋戒-{label}'
                desc = f'佛教六斋日；农历{ld.month}月{label}。'
                item = (f'six-{current.isoformat()}@jitong-calendar', current, summary, desc)
                six_events.append(item)
                all_events.append(item)
            elif kind == 'extra':
                summary = label
                desc = f'十斋日加上日；农历{ld.month}月{label}。'
                item = (f'extra-{current.isoformat()}@jitong-calendar', current, summary, desc)
                extra_events.append(item)
                all_events.append(item)
            current += timedelta(days=1)

    for name, day in moon_dates(start_year, end_year, tz_name):
        item = (f'spiritual-{name}-{day.isoformat()}@jitong-calendar', day, name, f'灵性事件：{name}。')
        spiritual_events.append(item)
        all_events.append(item)

    for name, day in stargates(start_year, end_year):
        item = (f'spiritual-stargate-{day.isoformat()}@jitong-calendar', day, name, f'灵性事件：{name}。')
        spiritual_events.append(item)
        all_events.append(item)

    six_events.sort(key=lambda x: x[1])
    extra_events.sort(key=lambda x: x[1])
    spiritual_events.sort(key=lambda x: x[1])
    all_events.sort(key=lambda x: x[1])

    write_calendar(DOCS / 'six-zhai.ics', '六斋日（设为绿色）', '#34C759', '佛教六斋日订阅源。建议在 Apple Calendar 设为绿色。', six_events, tz_name)
    write_calendar(DOCS / 'extra-ten-zhai.ics', '十斋日加上日（设为橘色）', '#FF9500', '十斋日中不属于六斋日的加上日。建议在 Apple Calendar 设为橘色。', extra_events, tz_name)
    write_calendar(DOCS / 'spiritual.ics', '灵性事件（设为蓝色）', '#0A84FF', '新月、满月与每月星门日。建议在 Apple Calendar 设为蓝色。', spiritual_events, tz_name)
    write_calendar(DOCS / 'combined.ics', '修行日历（合并版）', '#8E8E93', '合并版订阅源；若想分颜色显示，请订阅前三个日历。', all_events, tz_name)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--start-year', type=int)
    parser.add_argument('--end-year', type=int)
    parser.add_argument('--timezone', default='America/New_York')
    parser.add_argument('--rolling-years', type=int, default=4)
    args = parser.parse_args()

    today = date.today()
    start_year = args.start_year or today.year
    end_year = args.end_year or (start_year + args.rolling_years - 1)
    generate(start_year, end_year, args.timezone)


if __name__ == '__main__':
    main()
