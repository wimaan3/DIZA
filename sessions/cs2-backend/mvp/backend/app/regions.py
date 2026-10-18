"""Where the line runs: emergency numbers, crisis line, map centre and geocoder bias for the deployment's country.

The emergency number follows where the LINE operates (DIZA_COUNTRY), never the caller's phone: a tourist in
Los Angeles with a +86 phone must still dial 911, because 110/119 don't work there. The caller's country code is
only a hint for their language.

Numbers: Wikipedia "List of emergency telephone numbers" (read 2026-10-18) [S]. Check each against the national
government's own page before taking live calls in that country. Crisis lines are listed only where verified (US/CA
988); elsewhere the agent gives the emergency number instead of guessing a hotline.
"""
import os, re

# code: (name, spoken emergency instruction, {service: number}, default UI language, map centre, geocoder area, crisis line or None)
COUNTRIES = {
    'US': ('United States', '911', {'all': '911'}, 'en', (34.1, -118.2), 'Los Angeles County, CA', ('the 988 Suicide and Crisis Lifeline', '9 8 8')),
    'CA': ('Canada', '911', {'all': '911'}, 'en', (43.65, -79.38), 'Toronto, ON', ('the 988 Suicide Crisis Helpline', '9 8 8')),
    'MX': ('Mexico', '911', {'all': '911'}, 'es', (19.43, -99.13), 'Ciudad de México', None),
    'GB': ('United Kingdom', '999 or 112', {'all': '999', 'also': '112'}, 'en', (51.51, -0.13), 'London', None),
    'IE': ('Ireland', '112 or 999', {'all': '112', 'also': '999'}, 'en', (53.35, -6.26), 'Dublin', None),
    'FR': ('France', '112 (15 for an ambulance, 18 for fire, 17 for police)', {'all': '112', 'ambulance': '15', 'fire': '18', 'police': '17'}, 'fr', (48.86, 2.35), 'Paris', None),
    'DE': ('Germany', '112 (110 for police)', {'all': '112', 'police': '110'}, 'de', (52.52, 13.40), 'Berlin', None),
    'ES': ('Spain', '112', {'all': '112'}, 'es', (40.42, -3.70), 'Madrid', None),
    'IT': ('Italy', '112', {'all': '112'}, 'it', (41.90, 12.50), 'Roma', None),
    'CN': ('China', '119 for fire, 120 for an ambulance, or 110 for police', {'fire': '119', 'ambulance': '120', 'police': '110'}, 'zh', (39.90, 116.40), '北京市', None),
    'HK': ('Hong Kong', '999', {'all': '999'}, 'zh', (22.32, 114.17), 'Hong Kong', None),
    'TW': ('Taiwan', '119 for fire or an ambulance, 110 for police', {'fire': '119', 'ambulance': '119', 'police': '110'}, 'zh', (25.03, 121.57), '臺北市', None),
    'JP': ('Japan', '119 for fire or an ambulance, 110 for police', {'fire': '119', 'ambulance': '119', 'police': '110'}, 'ja', (35.68, 139.69), '東京都', None),
    'KR': ('South Korea', '119 for fire or an ambulance, 112 for police', {'fire': '119', 'ambulance': '119', 'police': '112'}, 'ko', (37.57, 126.98), '서울특별시', None),
    'VN': ('Vietnam', '114 for fire, 115 for an ambulance, 113 for police', {'fire': '114', 'ambulance': '115', 'police': '113'}, 'vi', (21.03, 105.85), 'Hà Nội', None),
    'PH': ('Philippines', '911', {'all': '911'}, 'en', (14.60, 120.98), 'Manila', None),
    'IN': ('India', '112', {'all': '112', 'police': '100', 'ambulance': '108', 'fire': '101'}, 'en', (28.61, 77.21), 'New Delhi', None),
    'AU': ('Australia', 'triple zero, 000', {'all': '000', 'also': '112'}, 'en', (-33.87, 151.21), 'Sydney NSW', None),
    'NZ': ('New Zealand', '111', {'all': '111'}, 'en', (-41.29, 174.78), 'Wellington', None),
    'AM': ('Armenia', '112 (101 for fire, 103 for an ambulance, 102 for police)', {'all': '112', 'fire': '101', 'ambulance': '103', 'police': '102'}, 'hy', (40.18, 44.51), 'Երևան', None),
    'IR': ('Iran', '125 for fire, 115 for an ambulance, 110 for police', {'fire': '125', 'ambulance': '115', 'police': '110'}, 'fa', (35.69, 51.39), 'تهران', None),
    'RU': ('Russia', '112', {'all': '112', 'fire': '101', 'police': '102', 'ambulance': '103'}, 'ru', (55.76, 37.62), 'Москва', None),
    'BR': ('Brazil', '193 for fire, 192 for an ambulance, 190 for police', {'fire': '193', 'ambulance': '192', 'police': '190'}, 'pt', (-23.55, -46.63), 'São Paulo', None),
}
# Longest calling code first, so +852 (Hong Kong) wins over +85x and +1 is the last resort.
CALLING_CODES = sorted({'1': 'US', '52': 'MX', '44': 'GB', '353': 'IE', '33': 'FR', '49': 'DE', '34': 'ES', '39': 'IT', '86': 'CN', '852': 'HK',
                        '886': 'TW', '81': 'JP', '82': 'KR', '84': 'VN', '63': 'PH', '91': 'IN', '61': 'AU', '64': 'NZ', '374': 'AM', '98': 'IR',
                        '7': 'RU', '55': 'BR'}.items(), key=lambda kv: -len(kv[0]))
LANG_OF = {'US': 'en', 'GB': 'en', 'IE': 'en', 'AU': 'en', 'NZ': 'en', 'PH': 'tl', 'IN': 'hi'}


def code():
    c = os.getenv('DIZA_COUNTRY', 'US').upper()
    return c if c in COUNTRIES else 'US'


def region():
    """The deployment's region, for the dashboard and the agents."""
    c = code()
    name, spoken, numbers, lang, centre, area, crisis = COUNTRIES[c]
    return {'country': c, 'name': name, 'emergency_spoken': spoken, 'numbers': numbers, 'ui_language': os.getenv('DIZA_UI_LANGUAGE', lang),
            'center': centre, 'area': os.getenv('DIZA_AREA', area), 'crisis_line': crisis[0] if crisis else ''}


def caller_country(number):
    """Country of a phone number from its calling code (+86 → CN). A hint only: the caller may be travelling."""
    digits = re.sub(r'\D', '', number or '')
    if not (number or '').strip().startswith('+') and len(digits) == 10:
        return 'US'  # a bare 10-digit number on a US line
    return next((c for prefix, c in CALLING_CODES if digits.startswith(prefix)), '')


def agent_variables(from_number=''):
    """Dynamic variables for the phone agents at call start. The prompts already say {{emergency_number}}."""
    r = region()
    crisis = COUNTRIES[r['country']][6]
    out = {'emergency_number': r['emergency_spoken'], 'service_area': r['area'], 'country': r['name'],
           'caller_country': caller_country(from_number)}
    if crisis:
        out['crisis_line_name'], out['crisis_line_spoken'] = crisis
    else:
        # No verified crisis line here: point to emergency services rather than a US hotline that won't connect.
        out['crisis_line_name'] = f"emergency services on {r['emergency_spoken']}"
        out['crisis_line_spoken'] = r['emergency_spoken']
        out['crisis_line_note'] = 'If you are in danger right now, call emergency services.'
    return out
