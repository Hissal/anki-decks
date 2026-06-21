# -*- coding: utf-8 -*-
"""Curated Finnish facts for the Suomen Presidentit deck builder.

Researched from fi.wikipedia (Paasikivi's birthplace cross-checked against
kansallisbiografia.fi); reviewed and approved by the user. Keyed by ordinal
(1-13). `Nickname` is "" when no well-attested nickname exists. All prose in
Finnish, no HTML. `Link` is the president's fi.wikipedia article.
"""

ENRICH = {
    1: {
        "Life": "1865–1952",
        "Profession": "lakimies, professori",
        "Birthplace": "Suomussalmi",
        "KnownFor": "Suomen ensimmäinen presidentti; tasavallan hallitusmuodon keskeinen laatija.",
        "Nickname": "",
        "Link": "https://fi.wikipedia.org/wiki/Kaarlo_Juho_Ståhlberg",
    },
    2: {
        "Life": "1883–1942",
        "Profession": "agronomi, maaherra",
        "Birthplace": "Kurkijoki",
        "KnownFor": "Tunnettu lukuisista valtiovierailuistaan.",
        "Nickname": "Reissu-Lasse",
        "Link": "https://fi.wikipedia.org/wiki/Lauri_Kristian_Relander",
    },
    3: {
        "Life": "1861–1944",
        "Profession": "lakimies, tuomari",
        "Birthplace": "Sääksmäki",
        "KnownFor": "Itsenäisyyssenaatin johtaja 1917–1918; kolmas presidentti.",
        "Nickname": "Ukko-Pekka",
        "Link": "https://fi.wikipedia.org/wiki/Pehr_Evind_Svinhufvud",
    },
    4: {
        "Life": "1873–1940",
        "Profession": "maanviljelijä, poliitikko",
        "Birthplace": "Ylivieska",
        "KnownFor": "Talonpoikaispresidentti; kuoli virassa joulukuussa 1940.",
        "Nickname": "",
        "Link": "https://fi.wikipedia.org/wiki/Kyösti_Kallio",
    },
    5: {
        "Life": "1889–1956",
        "Profession": "lakimies, Suomen Pankin pääjohtaja",
        "Birthplace": "Huittinen",
        "KnownFor": "Sota-ajan presidentti; tuomittiin sotasyyllisyysoikeudenkäynnissä.",
        "Nickname": "",
        "Link": "https://fi.wikipedia.org/wiki/Risto_Ryti",
    },
    6: {
        "Life": "1867–1951",
        "Profession": "sotilas, sotamarsalkka",
        "Birthplace": "Askainen (Louhisaari)",
        "KnownFor": "Ylipäällikkö toisessa maailmansodassa; valittiin presidentiksi poikkeuslailla 1944.",
        "Nickname": "Marski",
        "Link": "https://fi.wikipedia.org/wiki/Carl_Gustaf_Emil_Mannerheim",
    },
    7: {
        "Life": "1870–1956",
        "Profession": "lakimies, pankinjohtaja",
        "Birthplace": "Koski Hl (nyk. Hämeenkoski)",
        "KnownFor": "Sodanjälkeisen idänpolitiikan (Paasikiven linja) muotoilija.",
        "Nickname": "",
        "Link": "https://fi.wikipedia.org/wiki/Juho_Kusti_Paasikivi",
    },
    8: {
        "Life": "1900–1986",
        "Profession": "lakimies, poliitikko",
        "Birthplace": "Pielavesi",
        "KnownFor": "Pisin presidenttikausi (1956–1982); Etyk-kokous 1975.",
        "Nickname": "UKK",
        "Link": "https://fi.wikipedia.org/wiki/Urho_Kekkonen",
    },
    9: {
        "Life": "1923–2017",
        "Profession": "Suomen Pankin pääjohtaja, valtiot. tri",
        "Birthplace": "Turku",
        "KnownFor": "Vähensi presidentin valtaoikeuksia; suosittu kansanpresidentti.",
        "Nickname": "Manu",
        "Link": "https://fi.wikipedia.org/wiki/Mauno_Koivisto",
    },
    10: {
        "Life": "1937–2023",
        "Profession": "diplomaatti, YK-virkamies",
        "Birthplace": "Viipuri",
        "KnownFor": "Kansainvälinen rauhanvälittäjä; Nobelin rauhanpalkinto 2008.",
        "Nickname": "",
        "Link": "https://fi.wikipedia.org/wiki/Martti_Ahtisaari",
    },
    11: {
        "Life": "1943–",
        "Profession": "lakimies, ministeri",
        "Birthplace": "Helsinki",
        "KnownFor": "Suomen ensimmäinen naispresidentti.",
        "Nickname": "Muumimamma",
        "Link": "https://fi.wikipedia.org/wiki/Tarja_Halonen",
    },
    12: {
        "Life": "1948–",
        "Profession": "lakimies, valtiovarainministeri",
        "Birthplace": "Salo",
        "KnownFor": "Presidentti Suomen Nato-jäsenyyden aikaan (2023).",
        "Nickname": "",
        "Link": "https://fi.wikipedia.org/wiki/Sauli_Niinistö",
    },
    13: {
        "Life": "1968–",
        "Profession": "valtiot. tohtori, poliitikko",
        "Birthplace": "Helsinki",
        "KnownFor": "Suomen nykyinen presidentti (2024–).",
        "Nickname": "",
        "Link": "https://fi.wikipedia.org/wiki/Alexander_Stubb",
    },
}

# Canonical party display names (also used to group the rosters).
PARTY_CANON = {
    "Edistyspuolue": "Edistyspuolue",
    "Maalaisliitto": "Maalaisliitto",
    "Kokoomuspuolue": "Kokoomus",
    "Kokoomus": "Kokoomus",
    "Sosiaalidemokraatti": "Sosiaalidemokraatit (SDP)",
    "Sitoutumaton": "Sitoutumaton",
}

# Aggregate trivia (design spec §6 C). (question, answer) — Finnish, no HTML.
TRIVIA = [
    ("Kuka oli Suomen ensimmäinen presidentti?", "K. J. Ståhlberg (1.)"),
    ("Kuka oli Suomen ensimmäinen naispresidentti?", "Tarja Halonen (11.)"),
    ("Kuka istui presidenttinä pisimpään?", "Urho Kekkonen (8.), n. 26 vuotta"),
    ("Kuka on Suomen nykyinen presidentti?", "Alexander Stubb (13.)"),
    ("Kuka presidentti kuoli virassa?", "Kyösti Kallio (4.)"),
    ("Ketkä presidentit erosivat kesken kauden?", "Ryti (5.), Mannerheim (6.), Kekkonen (8.)"),
    ("Ketkä valittiin tai joiden kautta jatkettiin poikkeuslailla?", "Mannerheim (6.) ja Kekkonen (8.)"),
    ("Ketkä olivat presidentteinä toisen maailmansodan aikana?", "Kallio (4.), Ryti (5.), Mannerheim (6.)"),
    ("Kuka oli presidentti, kun Suomi liittyi EU:hun (1995)?", "Martti Ahtisaari (10.)"),
    ("Kuka oli presidentti, kun Suomi liittyi Natoon (2023)?", "Sauli Niinistö (12.)"),
]
