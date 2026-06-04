#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build a Finnish (FI) translation of the Ultimate Geography [Extended] CrowdAnki deck.

Source: the official English + Chinese CrowdAnki exports (deck.json). We mirror the
Chinese export's localisation strategy:

  * Per-language values that MUST differ:
      - deck-level `crowdanki_uuid`        (new, unique per language deck)
      - deck `name`                        ("Ultimate Geography [FI]")
      - deck `desc`                        (translated)
      - per-note `guid`                    (regenerated so the FI deck can coexist
                                            with the EN/ZH decks in one collection)
      - translated note fields             (Country, Country info, Capital,
                                            Capital info, Capital hint, Flag similarity)

  * Values that MUST stay the SAME (shared note type / config across all languages):
      - `note_model_uuid` and the whole `note_models` block
      - `deck_config_uuid` and `deck_configurations`
      - the Flag / Map image fields, `media_files`, and `tags`

Answer-field format (chosen by the user): "<Finnish> (<English original>)" on every
card, mirroring the Chinese deck (e.g. "Englanti (England)", "Madrid (Madrid)").

The script asserts that EVERY distinct English value in each translatable column has a
mapping, so an untranslated string can never silently leak into the output.
"""

import hashlib
import json
import shutil
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
EN_DIR = Path(
    r"C:\Users\hissa\Downloads\Ultimate_Geography_v5.3_EN_EXTENDED"
    r"\Ultimate Geography [EN] [Extended]"
)
OUT_DIR = Path(__file__).resolve().parent / "Ultimate Geography [FI] [Extended]"

# New, unique deck identity (must differ from EN/ZH).
FI_DECK_UUID = "0c9d6f2e-5a4b-4c1d-9e3a-7f8b2c6d1e40"
FI_DECK_NAME = "Ultimate Geography [FI]"

# Anki guid base91 alphabet (matches Anki / genanki).
_BASE91 = (
    "0123456789abcdefghijklmnopqrstuvwxyz"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "!#$%&()*+,-./:;<=>?@[]^_`{|}~"
)


def fi_guid(name: str) -> str:
    """Deterministic 10-char base91 guid, salted so it differs from EN/ZH guids."""
    num = int(hashlib.sha256(("UG-FI-v1:" + name).encode("utf-8")).hexdigest(), 16)
    out = ""
    while num and len(out) < 10:
        num, rem = divmod(num, 91)
        out = _BASE91[rem] + out
    return out.rjust(10, _BASE91[0])


# ---------------------------------------------------------------------------
# Translation tables
# ---------------------------------------------------------------------------

# Country / region / ocean / sea / continent names  (field 0)
FI_PLACE = {
    "England": "Englanti",
    "Scotland": "Skotlanti",
    "United Kingdom": "Yhdistynyt kuningaskunta",
    "Northern Ireland": "Pohjois-Irlanti",
    "France": "Ranska",
    "Wales": "Wales",
    "Georgia": "Georgia",
    "Germany": "Saksa",
    "Greece": "Kreikka",
    "Greenland": "Grönlanti",
    "Hungary": "Unkari",
    "Albania": "Albania",
    "Andorra": "Andorra",
    "Austria": "Itävalta",
    "Azerbaijan": "Azerbaidžan",
    "Belarus": "Valko-Venäjä",
    "Belgium": "Belgia",
    "Bosnia and Herzegovina": "Bosnia ja Hertsegovina",
    "Bulgaria": "Bulgaria",
    "Croatia": "Kroatia",
    "Czech Republic": "Tšekin tasavalta",
    "Denmark": "Tanska",
    "Estonia": "Viro",
    "Faroe Islands": "Färsaaret",
    "Finland": "Suomi",
    "Iceland": "Islanti",
    "Ireland": "Irlanti",
    "Italy": "Italia",
    "Latvia": "Latvia",
    "Liechtenstein": "Liechtenstein",
    "Lithuania": "Liettua",
    "Luxembourg": "Luxemburg",
    "North Macedonia": "Pohjois-Makedonia",
    "Malta": "Malta",
    "Moldova": "Moldova",
    "Monaco": "Monaco",
    "Montenegro": "Montenegro",
    "Netherlands": "Alankomaat",
    "Norway": "Norja",
    "Poland": "Puola",
    "Portugal": "Portugali",
    "Romania": "Romania",
    "Russia": "Venäjä",
    "San Marino": "San Marino",
    "Serbia": "Serbia",
    "Slovakia": "Slovakia",
    "Slovenia": "Slovenia",
    "Spain": "Espanja",
    "Sweden": "Ruotsi",
    "Switzerland": "Sveitsi",
    "Turkey": "Turkki",
    "Ukraine": "Ukraina",
    "Vatican City": "Vatikaanivaltio",
    "Armenia": "Armenia",
    "Cyprus": "Kypros",
    "Kazakhstan": "Kazakstan",
    "Egypt": "Egypti",
    "Algeria": "Algeria",
    "Angola": "Angola",
    "Benin": "Benin",
    "Botswana": "Botswana",
    "Burkina Faso": "Burkina Faso",
    "Cameroon": "Kamerun",
    "Burundi": "Burundi",
    "Cape Verde": "Kap Verde",
    "São Tomé and Príncipe": "São Tomé ja Príncipe",
    "Central African Republic": "Keski-Afrikan tasavalta",
    "Chad": "Tšad",
    "Equatorial Guinea": "Päiväntasaajan Guinea",
    "Kenya": "Kenia",
    "Comoros": "Komorit",
    "Ivory Coast": "Norsunluurannikko",
    "Democratic Republic of the Congo": "Kongon demokraattinen tasavalta",
    "Djibouti": "Djibouti",
    "Guinea-Bissau": "Guinea-Bissau",
    "Eritrea": "Eritrea",
    "Ethiopia": "Etiopia",
    "Gabon": "Gabon",
    "The Gambia": "Gambia",
    "Lesotho": "Lesotho",
    "Liberia": "Liberia",
    "Madagascar": "Madagaskar",
    "Malawi": "Malawi",
    "Mali": "Mali",
    "Mauritania": "Mauritania",
    "Mauritius": "Mauritius",
    "Morocco": "Marokko",
    "Mozambique": "Mosambik",
    "Namibia": "Namibia",
    "Niger": "Niger",
    "Nigeria": "Nigeria",
    "Republic of the Congo": "Kongon tasavalta",
    "Rwanda": "Ruanda",
    "Senegal": "Senegal",
    "Seychelles": "Seychellit",
    "Sierra Leone": "Sierra Leone",
    "South Africa": "Etelä-Afrikka",
    "Sudan": "Sudan",
    "Eswatini": "Eswatini",
    "Tanzania": "Tansania",
    "Togo": "Togo",
    "Tunisia": "Tunisia",
    "Uganda": "Uganda",
    "Sahrawi Arab Democratic Republic": "Saharan demokraattinen arabitasavalta",
    "Zambia": "Sambia",
    "Zimbabwe": "Zimbabwe",
    "Canary Islands": "Kanariansaaret",
    "Afghanistan": "Afganistan",
    "Bahrain": "Bahrain",
    "Bangladesh": "Bangladesh",
    "Bhutan": "Bhutan",
    "Brunei": "Brunei",
    "China": "Kiina",
    "Cambodia": "Kambodža",
    "Indonesia": "Indonesia",
    "India": "Intia",
    "Hong Kong": "Hongkong",
    "Iran": "Iran",
    "Israel": "Israel",
    "Iraq": "Irak",
    "South Korea": "Etelä-Korea",
    "North Korea": "Pohjois-Korea",
    "Jordan": "Jordania",
    "Japan": "Japani",
    "Lebanon": "Libanon",
    "Laos": "Laos",
    "Kyrgyzstan": "Kirgisia",
    "Kuwait": "Kuwait",
    "Myanmar": "Myanmar",
    "Mongolia": "Mongolia",
    "Maldives": "Malediivit",
    "Malaysia": "Malesia",
    "Oman": "Oman",
    "Nepal": "Nepal",
    "Palestine": "Palestiina",
    "Pakistan": "Pakistan",
    "Qatar": "Qatar",
    "Saudi Arabia": "Saudi-Arabia",
    "Singapore": "Singapore",
    "Syria": "Syyria",
    "Taiwan": "Taiwan",
    "Sri Lanka": "Sri Lanka",
    "Tajikistan": "Tadžikistan",
    "Thailand": "Thaimaa",
    "Timor-Leste": "Itä-Timor",
    "United Arab Emirates": "Arabiemiirikunnat",
    "Turkmenistan": "Turkmenistan",
    "Yemen": "Jemen",
    "Vietnam": "Vietnam",
    "Uzbekistan": "Uzbekistan",
    "Fiji": "Fidži",
    "Papua New Guinea": "Papua-Uusi-Guinea",
    "Australia": "Australia",
    "Solomon Islands": "Salomonsaaret",
    "Argentina": "Argentiina",
    "Bolivia": "Bolivia",
    "Brazil": "Brasilia",
    "Chile": "Chile",
    "Colombia": "Kolumbia",
    "Ecuador": "Ecuador",
    "Guyana": "Guyana",
    "Paraguay": "Paraguay",
    "Peru": "Peru",
    "Suriname": "Suriname",
    "Uruguay": "Uruguay",
    "Venezuela": "Venezuela",
    "Cook Islands": "Cookinsaaret",
    "Federated States of Micronesia": "Mikronesian liittovaltio",
    "Guam": "Guam",
    "Vanuatu": "Vanuatu",
    "Canada": "Kanada",
    "United States of America": "Yhdysvallat",
    "Mexico": "Meksiko",
    "Puerto Rico": "Puerto Rico",
    "Cuba": "Kuuba",
    "Dominican Republic": "Dominikaaninen tasavalta",
    "Haiti": "Haiti",
    "Jamaica": "Jamaika",
    "Trinidad and Tobago": "Trinidad ja Tobago",
    "Bermuda": "Bermuda",
    "Guadeloupe": "Guadeloupe",
    "The Bahamas": "Bahama",
    "Barbados": "Barbados",
    "Belize": "Belize",
    "Costa Rica": "Costa Rica",
    "El Salvador": "El Salvador",
    "Guatemala": "Guatemala",
    "Honduras": "Honduras",
    "Nicaragua": "Nicaragua",
    "Panama": "Panama",
    "Antigua and Barbuda": "Antigua ja Barbuda",
    "Dominica": "Dominica",
    "Saint Vincent and the Grenadines": "Saint Vincent ja Grenadiinit",
    "Somalia": "Somalia",
    "Zanzibar": "Sansibar",
    "Ghana": "Ghana",
    "Guinea": "Guinea",
    "New Zealand": "Uusi-Seelanti",
    "French Polynesia": "Ranskan Polynesia",
    "Philippines": "Filippiinit",
    "Kosovo": "Kosovo",
    "Libya": "Libya",
    "Palau": "Palau",
    "Saint Lucia": "Saint Lucia",
    "Bali": "Bali",
    "Grenada": "Grenada",
    "British Virgin Islands": "Brittiläiset Neitsytsaaret",
    "Turks and Caicos Islands": "Turks- ja Caicossaaret",
    "Cayman Islands": "Caymansaaret",
    "Anguilla": "Anguilla",
    "Azores": "Azorit",
    "Curaçao": "Curaçao",
    "French Guiana": "Ranskan Guayana",
    "Gibraltar": "Gibraltar",
    "Guernsey": "Guernsey",
    "Isle of Man": "Mansaari",
    "Jersey": "Jersey",
    "Kiribati": "Kiribati",
    "Macau": "Macao",
    "Madeira": "Madeira",
    "Marshall Islands": "Marshallinsaaret",
    "Nauru": "Nauru",
    "New Caledonia": "Uusi-Kaledonia",
    "Niue": "Niue",
    "Northern Cyprus": "Pohjois-Kypros",
    "Saint Kitts and Nevis": "Saint Kitts ja Nevis",
    "Samoa": "Samoa",
    "Somaliland": "Somalimaa",
    "South Sudan": "Etelä-Sudan",
    "Tuvalu": "Tuvalu",
    "United States Virgin Islands": "Yhdysvaltain Neitsytsaaret",
    "Åland Islands": "Ahvenanmaa",
    "South Ossetia": "Etelä-Ossetia",
    "American Samoa": "Amerikan Samoa",
    "Northern Mariana Islands": "Pohjois-Mariaanit",
    "Aruba": "Aruba",
    "Abkhazia": "Abhasia",
    "Sint Maarten": "Sint Maarten",
    "Tonga": "Tonga",
    "Transnistria": "Transnistria",
    "Sardinia": "Sardinia",
    "Kaliningrad Oblast": "Kaliningradin alue",
    "Martinique": "Martinique",
    "Java": "Jaava",
    "Corsica": "Korsika",
    "European Union": "Euroopan unioni",
    "Gulf of Mexico": "Meksikonlahti",
    "Philippine Sea": "Filippiinienmeri",
    "Southern Ocean": "Eteläinen jäämeri",
    "Gulf of Thailand": "Thaimaanlahti",
    "Micronesia": "Mikronesia",
    "Pacific Ocean": "Tyynimeri",
    "Atlantic Ocean": "Atlantin valtameri",
    "Indian Ocean": "Intian valtameri",
    "Arctic Ocean": "Pohjoinen jäämeri",
    "Hudson Bay": "Hudsoninlahti",
    "Labrador Sea": "Labradorinmeri",
    "White Sea": "Vienanmeri",
    "Denmark Strait": "Tanskansalmi",
    "Norwegian Sea": "Norjanmeri",
    "Baltic Sea": "Itämeri",
    "Celtic Sea": "Kelttienmeri",
    "English Channel": "Englannin kanaali",
    "Adriatic Sea": "Adrianmeri",
    "Bay of Biscay": "Biskajanlahti",
    "Black Sea": "Mustameri",
    "Aegean Sea": "Egeanmeri",
    "Balkan Peninsula": "Balkanin niemimaa",
    "Caspian Sea": "Kaspianmeri",
    "Mediterranean Sea": "Välimeri",
    "East Siberian Sea": "Itä-Siperianmeri",
    "Bering Strait": "Beringinsalmi",
    "Arabian Sea": "Arabianmeri",
    "Red Sea": "Punainenmeri",
    "Dead Sea": "Kuollutmeri",
    "Bay of Bengal": "Bengalinlahti",
    "Sea of Japan": "Japaninmeri",
    "Yellow Sea": "Keltainenmeri",
    "Coral Sea": "Korallimeri",
    "South China Sea": "Etelä-Kiinan meri",
    "Tasman Sea": "Tasmaninmeri",
    "Gulf of Carpentaria": "Carpentarianlahti",
    "Aral Sea": "Araljärvi",
    "Persian Gulf": "Persianlahti",
    "Caribbean Sea": "Karibianmeri",
    "Gulf of California": "Kalifornianlahti",
    "Polynesia": "Polynesia",
    "Melanesia": "Melanesia",
    "Scandinavia": "Skandinavia",
    "Sea of Galilee": "Genesaretinjärvi",
    "Sumatra": "Sumatra",
    "Sicily": "Sisilia",
    "Mayotte": "Mayotte",
    "Réunion": "Réunion",
    "Falkland Islands": "Falklandinsaaret",
    "Europe": "Eurooppa",
    "North America": "Pohjois-Amerikka",
    "South America": "Etelä-Amerikka",
    "Asia": "Aasia",
    "Africa": "Afrikka",
    "Oceania": "Oseania",
    "Antarctica": "Etelämanner",
    "Saint Martin": "Saint-Martin",
    "Wallis and Futuna": "Wallis ja Futuna",
    "Akrotiri and Dhekelia": "Akrotiri ja Dhekelia",
    "Svalbard": "Huippuvuoret",
    "Hawaii": "Havaiji",
    "Alaska": "Alaska",
    "Bougainville": "Bougainville",
    "Jeju": "Jeju",
    "Banda Sea": "Bandanmeri",
    "Barents Sea": "Barentsinmeri",
    "Celebes Sea": "Celebesinmeri",
    "East China Sea": "Itä-Kiinan meri",
    "Gulf of Alaska": "Alaskanlahti",
    "Gulf of Guinea": "Guineanlahti",
    "North Sea": "Pohjanmeri",
    "Sea of Okhotsk": "Ohotanmeri",
    "Timor Sea": "Timorinmeri",
}

# Capital names  (field 2)
FI_CAPITAL = {
    "London": "Lontoo",
    "Edinburgh": "Edinburgh",
    "Belfast": "Belfast",
    "Paris": "Pariisi",
    "Cardiff": "Cardiff",
    "Tbilisi": "Tbilisi",
    "Berlin": "Berliini",
    "Athens": "Ateena",
    "Nuuk": "Nuuk",
    "Tórshavn": "Tórshavn",
    "Helsinki": "Helsinki",
    "Budapest": "Budapest",
    "Tirana": "Tirana",
    "Andorra la Vella": "Andorra la Vella",
    "Vienna": "Wien",
    "Baku": "Baku",
    "Minsk": "Minsk",
    "Brussels": "Bryssel",
    "Sarajevo": "Sarajevo",
    "Sofia": "Sofia",
    "Zagreb": "Zagreb",
    "Prague": "Praha",
    "Copenhagen": "Kööpenhamina",
    "Tallinn": "Tallinna",
    "Reykjavík": "Reykjavík",
    "Dublin": "Dublin",
    "Rome": "Rooma",
    "Riga": "Riika",
    "Vaduz": "Vaduz",
    "Vilnius": "Vilna",
    "Luxembourg City": "Luxemburg",
    "Skopje": "Skopje",
    "Valletta": "Valletta",
    "Chișinău": "Chișinău",
    "Monaco": "Monaco",
    "Podgorica": "Podgorica",
    "Amsterdam": "Amsterdam",
    "Oslo": "Oslo",
    "Warsaw": "Varsova",
    "Lisbon": "Lissabon",
    "Bucharest": "Bukarest",
    "Moscow": "Moskova",
    "City of San Marino": "San Marino",
    "Belgrade": "Belgrad",
    "Bratislava": "Bratislava",
    "Ljubljana": "Ljubljana",
    "Madrid": "Madrid",
    "Stockholm": "Tukholma",
    "Bern": "Bern",
    "Ankara": "Ankara",
    "Kyiv": "Kiova",
    "Vatican City": "Vatikaani",
    "Yerevan": "Jerevan",
    "Nicosia": "Nikosia",
    "Astana": "Astana",
    "Cairo": "Kairo",
    "Algiers": "Alger",
    "Luanda": "Luanda",
    "Porto-Novo": "Porto-Novo",
    "Gaborone": "Gaborone",
    "Ouagadougou": "Ouagadougou",
    "Yaoundé": "Yaoundé",
    "Gitega": "Gitega",
    "Praia": "Praia",
    "São Tomé": "São Tomé",
    "Bangui": "Bangui",
    "N'Djamena": "N'Djamena",
    "Malabo": "Malabo",
    "Nairobi": "Nairobi",
    "Moroni": "Moroni",
    "Yamoussoukro": "Yamoussoukro",
    "Kinshasa": "Kinshasa",
    "Djibouti": "Djibouti",
    "Bissau": "Bissau",
    "Asmara": "Asmara",
    "Addis Ababa": "Addis Abeba",
    "Libreville": "Libreville",
    "Banjul": "Banjul",
    "Maseru": "Maseru",
    "Monrovia": "Monrovia",
    "Antananarivo": "Antananarivo",
    "Lilongwe": "Lilongwe",
    "Bamako": "Bamako",
    "Nouakchott": "Nouakchott",
    "Port Louis": "Port Louis",
    "Rabat": "Rabat",
    "Maputo": "Maputo",
    "Windhoek": "Windhoek",
    "Niamey": "Niamey",
    "Abuja": "Abuja",
    "Kampala": "Kampala",
    "Brazzaville": "Brazzaville",
    "Kigali": "Kigali",
    "Dakar": "Dakar",
    "Victoria": "Victoria",
    "Freetown": "Freetown",
    "Pretoria, Cape Town, Bloemfontein": "Pretoria, Kapkaupunki, Bloemfontein",
    "Khartoum": "Khartum",
    "Mbabane": "Mbabane",
    "Dodoma": "Dodoma",
    "Lomé": "Lomé",
    "Tunis": "Tunis",
    "Laayoune": "Laayoune",
    "Lusaka": "Lusaka",
    "Harare": "Harare",
    "Kabul": "Kabul",
    "Manama": "Manama",
    "Dhaka": "Dhaka",
    "Thimphu": "Thimphu",
    "Bandar Seri Begawan": "Bandar Seri Begawan",
    "Beijing": "Peking",
    "Phnom Penh": "Phnom Penh",
    "Jakarta": "Jakarta",
    "New Delhi": "New Delhi",
    "Tehran": "Teheran",
    "Jerusalem": "Jerusalem",
    "Baghdad": "Bagdad",
    "Seoul": "Soul",
    "Pyongyang": "Pjongjang",
    "Amman": "Amman",
    "Tokyo": "Tokio",
    "Beirut": "Beirut",
    "Vientiane": "Vientiane",
    "Bishkek": "Biškek",
    "Kuwait City": "Kuwait",
    "Naypyidaw": "Naypyidaw",
    "Ulaanbaatar": "Ulan Bator",
    "Malé": "Malé",
    "Kuala Lumpur": "Kuala Lumpur",
    "Muscat": "Maskat",
    "Kathmandu": "Kathmandu",
    "Islamabad": "Islamabad",
    "Doha": "Doha",
    "Riyadh": "Riad",
    "Singapore": "Singapore",
    "Damascus": "Damaskos",
    "Taipei": "Taipei",
    "Sri Jayawardenepura Kotte": "Sri Jayawardenepura Kotte",
    "Dushanbe": "Dušanbe",
    "Bangkok": "Bangkok",
    "Dili": "Dili",
    "Abu Dhabi": "Abu Dhabi",
    "Ashgabat": "Ašgabat",
    "Sanaa": "Sanaa",
    "Hanoi": "Hanoi",
    "Tashkent": "Taškent",
    "Suva": "Suva",
    "Port Moresby": "Port Moresby",
    "Canberra": "Canberra",
    "Honiara": "Honiara",
    "Buenos Aires": "Buenos Aires",
    "Sucre": "Sucre",
    "Brasília": "Brasília",
    "Santiago": "Santiago",
    "Bogotá": "Bogotá",
    "Quito": "Quito",
    "Georgetown": "Georgetown",
    "Asunción": "Asunción",
    "Lima": "Lima",
    "Paramaribo": "Paramaribo",
    "Montevideo": "Montevideo",
    "Caracas": "Caracas",
    "Avarua": "Avarua",
    "Palikir": "Palikir",
    "Hagåtña": "Hagåtña",
    "Port Vila": "Port Vila",
    "Ottawa": "Ottawa",
    "Washington, D.C.": "Washington",
    "Mexico City": "México",
    "San Juan": "San Juan",
    "Havana": "Havanna",
    "Santo Domingo": "Santo Domingo",
    "Port-au-Prince": "Port-au-Prince",
    "Kingston": "Kingston",
    "Port of Spain": "Port of Spain",
    "Nassau": "Nassau",
    "Bridgetown": "Bridgetown",
    "Belmopan": "Belmopan",
    "San José": "San José",
    "San Salvador": "San Salvador",
    "Guatemala City": "Guatemala",
    "Tegucigalpa": "Tegucigalpa",
    "Managua": "Managua",
    "Panama City": "Panama",
    "St. John's": "St. John's",
    "Roseau": "Roseau",
    "Kingstown": "Kingstown",
    "Mogadishu": "Mogadishu",
    "Accra": "Accra",
    "Conakry": "Conakry",
    "Wellington": "Wellington",
    "Papeete": "Papeete",
    "Manila": "Manila",
    "Pristina": "Priština",
    "Tripoli": "Tripoli",
    "Ngerulmud": "Ngerulmud",
    "Castries": "Castries",
    "St. George's": "St. George's",
    "Willemstad": "Willemstad",
    "South Tarawa": "South Tarawa",
    "Majuro": "Majuro",
    "Yaren": "Yaren",
    "Nouméa": "Nouméa",
    "Alofi": "Alofi",
    "North Nicosia": "Pohjois-Nikosia",
    "Basseterre": "Basseterre",
    "Apia": "Apia",
    "Hargeisa": "Hargeisa",
    "Juba": "Juba",
    "Funafuti": "Funafuti",
    "Charlotte Amalie": "Charlotte Amalie",
    "Mariehamn": "Maarianhamina",
    "Tskhinvali": "Tskhinvali",
    "Oranjestad": "Oranjestad",
    "Sukhumi": "Suhumi",
    "Nukuʻalofa": "Nukuʻalofa",
    "Tiraspol": "Tiraspol",
}

# Country info  (field 1)
FI_CINFO = {
    "A naming dispute exists between the sea's bordering countries, with South Korea notably supporting the name East Sea.":
        "Merta reunustavien maiden välillä on nimikiista: erityisesti Etelä-Korea kannattaa nimeä East Sea.",
    "Also known as Burma.": "Tunnetaan myös nimellä Burma.",
    "Also known as Cabo Verde.": "Tunnetaan myös nimellä Cabo Verde.",
    "Also known as Czechia.": "Tunnetaan myös nimellä Tšekki.",
    "Also known as Timor-Leste.": "Tunnetaan myös nimellä Timor-Leste.",
    "Also known as Türkiye": "Tunnetaan myös nimellä Türkiye",
    "Also known as the Gulf of Siam.": "Tunnetaan myös nimellä Siaminlahti (Gulf of Siam).",
    "Also known as the Sea of Cortez.": "Tunnetaan myös nimellä Cortésinmeri (Sea of Cortez).",
    "Autonomous community of Spain.": "Espanjan autonominen alue.",
    "Autonomous province of South Korea.": "Etelä-Korean autonominen maakunta.",
    "Autonomous region of Finland.": "Suomen autonominen alue.",
    "Autonomous region of Italy.": "Italian autonominen alue.",
    "Autonomous region of Papua New Guinea.": "Papua-Uuden-Guinean autonominen alue.",
    "Autonomous region of Portugal.": "Portugalin autonominen alue.",
    "Constituent country in the Kingdom of Denmark.":
        "Tanskan kuningaskuntaan kuuluva itsehallintoalue.",
    "Constituent country of the Kingdom of the Netherlands.":
        "Alankomaiden kuningaskuntaan kuuluva itsehallintoalue.",
    "Constituent country of the United Kingdom.":
        "Yhdistyneen kuningaskunnan osa.",
    "Crown dependency of the United Kingdom.": "Britannian kruununalusmaa.",
    "Formerly Zaire.": "Aiemmin Zaire.",
    "Formerly known as Macedonia.": "Tunnettiin aiemmin nimellä Makedonia.",
    "Historical and cultural region in Northern Europe, which includes the countries of Denmark, Norway and Sweden, and sometimes Finland and Iceland.":
        "Pohjois-Euroopan historiallinen ja kulttuurinen alue, johon kuuluvat Tanska, Norja ja Ruotsi sekä toisinaan Suomi ja Islanti.",
    "Independent state claimed by Georgia.":
        "Itsenäinen valtio, jota Georgia pitää omana alueenaan.",
    "Independent state claimed by Moldova.":
        "Itsenäinen valtio, jota Moldova pitää omana alueenaan.",
    "Independent state claimed by Somalia.":
        "Itsenäinen valtio, jota Somalia pitää omana alueenaan.",
    "Island of Indonesia.": "Indonesian saari.",
    "Known as Swaziland until 2018.": "Tunnettiin nimellä Swazimaa vuoteen 2018 asti.",
    "Oblast (administrative region) of the Russian Federation.":
        "Venäjän federaation oblasti (hallinnollinen alue).",
    "Officially Côte d'Ivoire.": "Virallisesti Côte d'Ivoire.",
    "Overseas department of France.": "Ranskan merentakainen departementti.",
    "Overseas territory of France.": "Ranskan merentakainen alue.",
    "Overseas territory of the United Kingdom.":
        "Yhdistyneen kuningaskunnan merentakainen alue.",
    "Partially recognised state claimed by China.":
        "Osittain tunnustettu valtio, jota Kiina pitää omana alueenaan.",
    "Partially recognised state claimed by Morocco. Also known as Western Sahara.":
        "Osittain tunnustettu valtio, jota Marokko pitää omana alueenaan. Tunnetaan myös nimellä Länsi-Sahara.",
    "Partially recognised state claimed by Serbia.":
        "Osittain tunnustettu valtio, jota Serbia pitää omana alueenaan.",
    "Region of France.": "Ranskan alue.",
    "Semi-autonomous region of Tanzania.": "Tansanian osittain itsehallinnollinen alue.",
    "Special Administrative Region of China.": "Kiinan erityishallintoalue.",
    "State of the United States.": "Yhdysvaltain osavaltio.",
    "State recognised only by Turkey and claimed by Cyprus.":
        "Vain Turkin tunnustama valtio, jota Kypros pitää omana alueenaan.",
    "Subregion of Oceania comprising thousands of small islands in the central and southern Pacific Ocean.":
        "Oseanian osa-alue, joka koostuu tuhansista pienistä saarista Tyynenmeren keski- ja eteläosassa.",
    "Subregion of Oceania comprising thousands of small islands in the western Pacific Ocean.":
        "Oseanian osa-alue, joka koostuu tuhansista pienistä saarista Tyynenmeren länsiosassa.",
    "Subregion of Oceania, which includes the four countries of Vanuatu, the Solomon Islands, Fiji, and Papua New Guinea.":
        "Oseanian osa-alue, johon kuuluu neljä maata: Vanuatu, Salomonsaaret, Fidži ja Papua-Uusi-Guinea.",
    "Unincorporated internal area of Norway.":
        "Norjaan kuuluva alue, joka ei kuulu mihinkään maakuntaan.",
    "Unincorporated territory of the United States.":
        "Yhdysvaltain järjestäytymätön alue.",
    "World region covering the Australian continent and most of the islands in the Pacific Ocean.":
        "Maailman alue, joka kattaa Australian mantereen ja suurimman osan Tyynenmeren saarista.",
}

# Capital info  (field 3)
FI_CAPINFO = {
    "Also known as Kiev.": "Tunnetaan myös nimellä Kiev.",
    "Also spelled as Sana'a.": "Kirjoitetaan myös muodossa Sana'a.",
    "Cetinje is an honorary capital.": "Cetinje on kunniapääkaupunki.",
    "Ciudad de la Paz is being built to replace Malabo as capital.":
        "Ciudad de la Paz -kaupunkia rakennetaan korvaamaan Malabo pääkaupunkina.",
    "Colombo is often referred to as the capital but Sri Jayawardenepura Kotte, a suburb of Colombo, is the official, legislative capital.":
        "Colomboa kutsutaan usein pääkaupungiksi, mutta virallinen, lainsäädännöllinen pääkaupunki on Colombon esikaupunki Sri Jayawardenepura Kotte.",
    "Disputed; claimed by Israel; Ramallah is the administrative centre.":
        "Kiistanalainen; Israel pitää sitä omanaan; hallinnollinen keskus on Ramallah.",
    "Disputed; claimed by Palestine.": "Kiistanalainen; Palestiina pitää sitä omanaan.",
    "Known as Nur-Sultan until September 2022.":
        "Tunnettiin nimellä Nur-Sultan syyskuuhun 2022 asti.",
    "Nauru has no official capital; the Yaren District is the de facto capital.":
        "Naurulla ei ole virallista pääkaupunkia; Yarenin piiri on tosiasiallinen pääkaupunki.",
    "Official capital was moved from Bujumbura to Gitega in 2019.":
        "Virallinen pääkaupunki siirrettiin Bujumburasta Gitegaan vuonna 2019.",
    "Officially Luxembourg.": "Virallisesti Luxemburg.",
    "South Africa has no legally defined capital: the branches of government are split over three cities: Pretoria (executive), Cape Town (legislative) and Bloemfontein (judicial).":
        "Etelä-Afrikalla ei ole laissa määriteltyä pääkaupunkia: hallinnon haarat jakautuvat kolmeen kaupunkiin: Pretoria (toimeenpanovalta), Kapkaupunki (lainsäädäntövalta) ja Bloemfontein (tuomiovalta).",
    "Switzerland has no official capital; Bern is the de facto capital.":
        "Sveitsillä ei ole virallista pääkaupunkia; Bern on tosiasiallinen pääkaupunki.",
    "While Amsterdam is the official capital, The Hague is the seat of the executive and legislative branches.":
        "Vaikka Amsterdam on virallinen pääkaupunki, Haag on toimeenpano- ja lainsäädäntövallan sijaintipaikka.",
    "While Dodoma is the official capital, Dar es Salaam is the de facto seat of government.":
        "Vaikka Dodoma on virallinen pääkaupunki, Dar es Salaam on hallituksen tosiasiallinen sijaintipaikka.",
    "While Laayoune, also known as El Aaiún, is the declared capital, Tifariti is the de facto seat of government.":
        "Vaikka julistettu pääkaupunki on Laayoune (tunnetaan myös nimellä El Aaiún), hallituksen tosiasiallinen sijaintipaikka on Tifariti.",
    "While Mbabane is the official, executive capital, Lobamba is the traditional, spiritual and legislative capital.":
        "Vaikka Mbabane on virallinen, toimeenpaneva pääkaupunki, Lobamba on perinteinen, hengellinen ja lainsäädännöllinen pääkaupunki.",
    "While Porto-Novo is the official capital, Cotonou is the de facto seat of government.":
        "Vaikka Porto-Novo on virallinen pääkaupunki, Cotonou on hallituksen tosiasiallinen sijaintipaikka.",
    "While Sucre is the constitutional capital, La Paz is the seat of government.":
        "Vaikka Sucre on perustuslaillinen pääkaupunki, La Paz on hallituksen sijaintipaikka.",
    "While Yamoussoukro is the official capital, Abidjan is the de facto seat of government.":
        "Vaikka Yamoussoukro on virallinen pääkaupunki, Abidjan on hallituksen tosiasiallinen sijaintipaikka.",
}

# Capital hint  (field 4)
FI_HINT = {
    "Claimed and controlled": "Vaadittu ja hallinnassa",
    "Claimed but not controlled": "Vaadittu mutta ei hallinnassa",
    "Not a sovereign country": "Ei itsenäinen valtio",
    "Sovereign country": "Itsenäinen valtio",
}

# Flag similarity  (field 6)
FI_FLAGSIM = {
    "Andorra (narrower, coat of arms with motto)":
        "Andorra (kapeampi, vaakuna ja motto)",
    "Australia (white stars, two more stars)":
        "Australia (valkoiset tähdet, kaksi tähteä enemmän)",
    "Austria (brighter red, wider white band)":
        "Itävalta (kirkkaampi punainen, leveämpi valkoinen raita)",
    "Bahrain (narrower, fewer serrated edges, red)":
        "Bahrain (kapeampi, vähemmän sahalaitaa, punainen)",
    "Bolivia (coat of arms instead of star)":
        "Bolivia (tähden sijaan vaakuna)",
    "Cameroon (green/red/yellow, yellow star)":
        "Kamerun (vihreä/punainen/keltainen, keltainen tähti)",
    "Chad (slightly darker blue)":
        "Tšad (hieman tummempi sininen)",
    "Colombia (no coat of arms)":
        "Kolumbia (ei vaakunaa)",
    "Cuba (red triangle, blue stripes)":
        "Kuuba (punainen kolmio, siniset raidat)",
    "Curaçao (two stars in top-left corner)":
        "Curaçao (kaksi tähteä vasemmassa yläkulmassa)",
    "Ecuador (with coat of arms)":
        "Ecuador (vaakunan kanssa)",
    "Egypt (emblem instead of text), Yemen (no text)":
        "Egypti (tekstin sijaan tunnus), Jemen (ei tekstiä)",
    "Egypt (with emblem), Iraq (with text)":
        "Egypti (tunnuksen kanssa), Irak (tekstin kanssa)",
    "El Salvador (different coat of arms, slightly darker blue)":
        "El Salvador (eri vaakuna, hieman tummempi sininen)",
    "Ghana (star instead of coat of arms)":
        "Ghana (vaakunan sijaan tähti)",
    "Guinea (green and red flipped, slightly darker green)":
        "Guinea (vihreä ja punainen vaihdettu, hieman tummempi vihreä)",
    "Iceland (blue background, red and white cross), Norway (red background, blue and white cross)":
        "Islanti (sininen tausta, puna-valkoinen risti), Norja (punainen tausta, sini-valkoinen risti)",
    "Iceland (blue background, red cross), Faroe Islands (white background, red and blue cross)":
        "Islanti (sininen tausta, punainen risti), Färsaaret (valkoinen tausta, puna-sininen risti)",
    "Indonesia (white and red flipped, brighter red), Monaco (white and red flipped, narrower)":
        "Indonesia (valkoinen ja punainen vaihdettu, kirkkaampi punainen), Monaco (valkoinen ja punainen vaihdettu, kapeampi)",
    "Indonesia (wider, brighter red), Poland (red and white flipped, wider)":
        "Indonesia (leveämpi, kirkkaampi punainen), Puola (punainen ja valkoinen vaihdettu, leveämpi)",
    "Iraq (text instead of emblem), Yemen (no emblem)":
        "Irak (tunnuksen sijaan teksti), Jemen (ei tunnusta)",
    "Ireland (orange and green flipped, wider)":
        "Irlanti (oranssi ja vihreä vaihdettu, leveämpi)",
    "Ivory Coast (green and orange flipped, narrower)":
        "Norsunluurannikko (vihreä ja oranssi vaihdettu, kapeampi)",
    "Latvia (darker red, narrower white band)":
        "Latvia (tummempi punainen, kapeampi valkoinen raita)",
    "Luxembourg (lighter blue)":
        "Luxemburg (vaaleampi sininen)",
    "Mali (red and green flipped, slightly brighter green)":
        "Mali (punainen ja vihreä vaihdettu, hieman kirkkaampi vihreä)",
    "Moldova (wider, coat of arms with eagle)":
        "Moldova (leveämpi, vaakuna ja kotka)",
    "Monaco (narrower, darker red), Poland (red and white flipped, darker red)":
        "Monaco (kapeampi, tummempi punainen), Puola (punainen ja valkoinen vaihdettu, tummempi punainen)",
    "Nauru (single star below yellow band)":
        "Nauru (yksittäinen tähti keltaisen raidan alla)",
    "Netherlands (darker blue)":
        "Alankomaat (tummempi sininen)",
    "New Zealand (red stars, two fewer stars)":
        "Uusi-Seelanti (punaiset tähdet, kaksi tähteä vähemmän)",
    "Nicaragua (different coat of arms, slightly lighter blue)":
        "Nicaragua (eri vaakuna, hieman vaaleampi sininen)",
    "Norway (red background, blue cross), Faroe Islands (white background, red and blue cross)":
        "Norja (punainen tausta, sininen risti), Färsaaret (valkoinen tausta, puna-sininen risti)",
    "Palestine (black/white/green, red arrow)":
        "Palestiina (musta/valkoinen/vihreä, punainen nuoli)",
    "Palestine (no symbol)":
        "Palestiina (ei tunnusta)",
    "Puerto Rico (blue triangle, red stripes)":
        "Puerto Rico (sininen kolmio, punaiset raidat)",
    "Qatar (wider, more serrated edges, maroon)":
        "Qatar (leveämpi, enemmän sahalaitaa, viininpunainen)",
    "Romania (slightly lighter blue)":
        "Romania (hieman vaaleampi sininen)",
    "Russia (no coat of arms), Slovenia (wider, smaller coat of arms)":
        "Venäjä (ei vaakunaa), Slovenia (leveämpi, pienempi vaakuna)",
    "Senegal (green/yellow/red, green star)":
        "Senegal (vihreä/keltainen/punainen, vihreä tähti)",
    "Slovakia (narrower, bigger coat of arms)":
        "Slovakia (kapeampi, isompi vaakuna)",
    "Slovakia (with coat of arms)":
        "Slovakia (vaakunan kanssa)",
    "Sudan (red/white/black, green arrow), Sahrawi Arab Democratic Republic (with star and crescent)":
        "Sudan (punainen/valkoinen/musta, vihreä nuoli), Saharan demokraattinen arabitasavalta (tähti ja puolikuu)",
}

# Translated deck description (HTML preserved verbatim except text).
FI_DESC = (
    '<a href="https://github.com/anki-geo/ultimate-geography/"><b>TÄYDELLINEN KUVAUS</b></a> | '
    '<a href="https://github.com/anki-geo/ultimate-geography/releases"><b>JULKAISUTIEDOT</b></a> | '
    '<a href="https://github.com/anki-geo/ultimate-geography/blob/master/CONTRIBUTING.md"><b>OSALLISTUMINEN</b></a>\n\n'
    '<b>Ultimate Geography v5.3</b> sisältää:\n\n'
    '- maailman <a href="https://en.wikipedia.org/wiki/List_of_sovereign_states"><b>205 itsenäistä valtiota</b></a> (820 korttia)\n'
    '- <b>59 aluetta, maailmankolkkaa ja muuta entiteettiä</b> (103 korttia)\n'
    '- <b>48 valtamerta ja merta</b> (48 korttia, vain kartat)\n'
    '- <b>7 mannerta</b> (7 korttia, vain kartat)\n'
    '- yhteensä <b>319 yksittäistä muistiinpanoa</b>, <b>978 korttia</b>, <b>221 lippua</b> ja <b>319 karttaa</b>.\n\n'
    'Pakka on <a href="https://github.com/anki-geo/ultimate-geography#other-languages-and-versions">saatavilla</a> '
    'kielillä <b>englanti</b>, <b>saksa</b>, <b>espanja</b>, <b>ranska</b>, <b>norja</b>, <b>tšekki</b>, '
    '<b>venäjä</b>, <b>hollanti</b>, <b>ruotsi</b>, <b>portugali</b>, <b>kiina</b> (yksinkertaistettu ja perinteinen), '
    '<b>puola</b>, <b>italia</b> ja <b>tanska</b>. Jokaisesta kielestä on saatavilla myös '
    '<a href="https://github.com/anki-geo/ultimate-geography#other-languages-and-versions"><b>laajennettu versio</b></a>. '
    'Muistamisen tueksi ja oppimisen taustatiedoksi osa muistiinpanoista sisältää lisätietoja, kuten '
    'samankaltaisia lippuja, hallintotietoja, vaihtoehtoisia maannimiä jne.\n\n'
    'Voit käyttää Ankin <a href="https://github.com/anki-geo/ultimate-geography#custom-study">suodatetun pakan ominaisuutta</a> '
    'keskittääksesi opiskelusi pakan osajoukkoon, kuten itsenäisiin valtioihin, yksittäiseen korttipohjaan '
    '(esim. kartasta maahan) tai tiettyyn mantereeseen (esim. Eurooppa).\n\n'
    'Tätä pakkaa <a href="https://github.com/anki-geo/ultimate-geography"><b>ylläpidetään GitHubissa</b></a>. '
    'Jos huomaat virheen, sinulla on ehdotus tai haluat auttaa, älä epäröi '
    '<a href="https://github.com/anki-geo/ultimate-geography/issues">avata issueta</a>. '
    'Haluatko <b>pysyä ajan tasalla uusista julkaisuista</b>? Seuraa GitHub-repositoriota tai tilaa '
    '<a href="https://github.com/anki-geo/ultimate-geography/releases.atom">julkaisusyötettä</a>!'
)


def fmt(fi: str, en: str) -> str:
    """Answer-field format: Finnish (English original)."""
    return f"{fi} ({en})"


def main() -> None:
    en_deck = json.loads((EN_DIR / "deck.json").read_text(encoding="utf-8"))

    # ---- completeness check: every distinct EN value must have a mapping ----
    missing = {"place": set(), "capital": set(), "cinfo": set(),
               "capinfo": set(), "hint": set(), "flagsim": set()}
    for n in en_deck["notes"]:
        f = n["fields"]
        if f[0].strip() and f[0] not in FI_PLACE:
            missing["place"].add(f[0])
        if f[1].strip() and f[1] not in FI_CINFO:
            missing["cinfo"].add(f[1])
        if f[2].strip() and f[2] not in FI_CAPITAL:
            missing["capital"].add(f[2])
        if f[3].strip() and f[3] not in FI_CAPINFO:
            missing["capinfo"].add(f[3])
        if f[4].strip() and f[4] not in FI_HINT:
            missing["hint"].add(f[4])
        if f[6].strip() and f[6] not in FI_FLAGSIM:
            missing["flagsim"].add(f[6])

    if any(missing.values()):
        print("MISSING TRANSLATIONS:")
        for k, v in missing.items():
            for s in sorted(v):
                print(f"  [{k}] {s!r}")
        raise SystemExit(1)

    # ---- build translated notes ----
    seen_guids: set[str] = set()
    fi_notes = []
    for n in en_deck["notes"]:
        f = list(n["fields"])
        en_country = f[0]
        new = list(f)
        new[0] = fmt(FI_PLACE[f[0]], f[0]) if f[0].strip() else f[0]
        new[1] = FI_CINFO.get(f[1], "") if f[1].strip() else ""
        new[2] = fmt(FI_CAPITAL[f[2]], f[2]) if f[2].strip() else f[2]
        new[3] = FI_CAPINFO.get(f[3], "") if f[3].strip() else ""
        new[4] = FI_HINT.get(f[4], "") if f[4].strip() else ""
        # f[5] Flag and f[7] Map stay verbatim
        new[6] = FI_FLAGSIM.get(f[6], "") if f[6].strip() else ""

        guid = fi_guid(en_country)
        assert guid not in seen_guids, f"guid collision for {en_country}"
        seen_guids.add(guid)

        note = dict(n)
        note["fields"] = new
        note["guid"] = guid
        fi_notes.append(note)

    # ---- assemble deck ----
    fi_deck = dict(en_deck)
    fi_deck["crowdanki_uuid"] = FI_DECK_UUID
    fi_deck["name"] = FI_DECK_NAME
    fi_deck["desc"] = FI_DESC
    fi_deck["notes"] = fi_notes

    # ---- write output ----
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "deck.json").write_text(
        json.dumps(fi_deck, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    # ---- copy media (identical across languages) ----
    src_media = EN_DIR / "media"
    dst_media = OUT_DIR / "media"
    if dst_media.exists():
        shutil.rmtree(dst_media)
    shutil.copytree(src_media, dst_media)

    print(f"Wrote {OUT_DIR / 'deck.json'}")
    print(f"Notes: {len(fi_notes)} | media files copied: {len(list(dst_media.iterdir()))}")


if __name__ == "__main__":
    main()
