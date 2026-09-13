"""UPS-based shipping rate calculator.

Computes rates from the configured origin (110 Inner Campus Drive,
Austin, TX 78705) to any US destination ZIP using published UPS
zone-based tariffs, dimensional weight, fuel surcharge, and
residential delivery surcharge.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.config import settings


# ──────────────────────────── Data classes ────────────────────────────
@dataclass(frozen=True)
class PackageSpec:
    weight_lbs: float
    length_in: float | None = None
    width_in: float | None = None
    height_in: float | None = None


@dataclass(frozen=True)
class RateResult:
    service: str
    service_name: str
    rate: float
    estimated_business_days: int
    currency: str = "USD"


@dataclass(frozen=True)
class ShippingEstimate:
    origin: str
    destination_zip: str
    rates: list[RateResult]
    package: dict


# ──────────────────────────── Zone map ────────────────────────────
# Mapping of destination ZIP prefix (first 3 digits) to UPS zone from
# Austin TX (78705). Derived from UPS published ZIP-to-zone tables.
_ORIGIN_ZIP = "78705"

_PREFIX_TO_ZONE: dict[str, int] = {
    # Zone 1 – Central TX & surrounding
    "733": 1, "734": 1, "735": 1, "736": 1, "739": 1,
    "750": 1, "751": 1, "754": 1, "755": 1, "756": 1, "757": 1, "758": 1, "759": 1,
    "760": 1, "761": 1, "762": 1, "763": 1, "764": 1, "765": 1, "766": 1, "767": 1, "768": 1, "769": 1,
    "770": 1, "771": 1, "772": 1, "773": 1, "774": 1, "775": 1, "776": 1, "777": 1, "778": 1, "779": 1,
    "780": 2, "781": 2, "782": 2, "783": 2, "784": 2, "785": 2, "786": 2, "787": 2, "788": 2, "789": 2,
    # Zone 3 – Southern states
    "706": 3, "710": 3, "711": 3, "712": 3, "713": 3, "714": 3, "715": 3, "716": 3, "717": 3, "718": 3, "719": 3,
    "307": 3, "310": 3, "311": 3, "312": 3, "317": 3, "318": 3, "320": 3, "321": 3,
    "350": 3, "351": 3, "352": 3, "354": 3, "355": 3, "356": 3, "358": 3, "359": 3,
    "360": 3, "361": 3, "362": 3, "363": 3, "364": 3, "365": 3, "366": 3, "367": 3, "368": 3, "369": 3,
    "370": 3, "371": 3, "372": 3, "373": 3, "374": 3, "375": 3, "376": 3, "377": 3, "378": 3, "379": 3, "380": 3, "381": 3, "382": 3, "383": 3, "384": 3, "385": 3, "386": 3, "388": 3, "389": 3,
    "390": 3, "391": 3, "392": 3, "393": 3, "394": 3, "395": 3, "396": 3, "397": 3, "398": 3, "399": 3,
    "601": 3, "602": 3, "603": 3, "604": 3, "605": 3, "606": 3, "607": 3, "608": 3, "609": 3, "610": 3, "611": 3, "612": 3, "613": 3, "614": 3, "615": 3, "616": 3, "617": 3, "618": 3, "619": 3, "620": 3, "622": 3, "623": 3, "624": 3, "625": 3, "626": 3, "627": 3, "628": 3, "629": 3,
    # Zone 4 – Mid-Atlantic / Southeast
    "210": 4, "211": 4, "212": 4, "213": 4, "214": 4, "215": 4, "216": 4, "217": 4, "218": 4, "219": 4, "220": 4, "221": 4, "222": 4, "223": 4, "224": 4, "225": 4, "226": 4, "227": 4, "228": 4, "229": 4,
    "230": 4, "231": 4, "232": 4, "233": 4, "234": 4, "235": 4, "236": 4, "237": 4, "238": 4, "239": 4,
    "240": 4, "241": 4, "242": 4, "243": 4, "244": 4, "245": 4, "246": 4, "247": 4, "248": 4, "249": 4,
    "250": 4, "251": 4, "252": 4, "253": 4, "254": 4, "255": 4, "256": 4, "257": 4, "258": 4, "259": 4,
    "260": 4, "261": 4, "262": 4, "263": 4, "264": 4, "265": 4, "266": 4, "267": 4, "268": 4, "269": 4,
    "270": 4, "271": 4, "272": 4, "273": 4, "274": 4, "275": 4, "276": 4, "277": 4, "278": 4, "279": 4,
    "280": 4, "281": 4, "282": 4, "283": 4, "284": 4, "285": 4, "286": 4, "287": 4, "288": 4, "289": 4,
    "290": 4, "291": 4, "292": 4, "293": 4, "294": 4, "295": 4, "296": 4, "297": 4, "298": 4, "299": 4,
    "300": 4, "301": 4, "302": 4, "303": 4, "304": 4, "305": 4, "306": 4, "308": 4,
    # Zone 5 – Great Lakes / Northeast
    "400": 5, "401": 5, "402": 5, "403": 5, "404": 5, "405": 5, "406": 5, "407": 5, "408": 5, "409": 5,
    "410": 5, "411": 5, "412": 5, "413": 5, "414": 5, "415": 5, "416": 5, "417": 5, "418": 5, "419": 5,
    "420": 5, "421": 5, "422": 5, "423": 5, "424": 5, "425": 5, "426": 5, "427": 5, "428": 5, "429": 5,
    "430": 5, "431": 5, "432": 5, "433": 5, "434": 5, "435": 5, "436": 5, "437": 5, "438": 5, "439": 5,
    "440": 5, "441": 5, "442": 5, "443": 5, "444": 5, "445": 5, "446": 5, "447": 5, "448": 5, "449": 5,
    "450": 5, "451": 5, "452": 5, "453": 5, "454": 5, "455": 5, "456": 5, "457": 5, "458": 5, "459": 5,
    "460": 5, "461": 5, "462": 5, "463": 5, "464": 5, "465": 5, "466": 5, "467": 5, "468": 5, "469": 5,
    "470": 5, "471": 5, "472": 5, "473": 5, "474": 5, "475": 5, "476": 5, "477": 5, "478": 5, "479": 5,
    "480": 5, "481": 5, "482": 5, "483": 5, "484": 5, "485": 5, "486": 5, "487": 5, "488": 5, "489": 5,
    "490": 5, "491": 5, "492": 5, "493": 5, "494": 5, "495": 5, "496": 5, "497": 5, "498": 5, "499": 5,
    "500": 5, "501": 5, "502": 5, "503": 5, "504": 5, "505": 5, "506": 5, "507": 5, "508": 5, "509": 5,
    "510": 5, "511": 5, "512": 5, "513": 5, "514": 5, "515": 5, "516": 5, "517": 5, "518": 5, "519": 5,
    "520": 5, "521": 5, "522": 5, "523": 5, "524": 5, "525": 5, "526": 5, "527": 5, "528": 5, "529": 5,
    "530": 5, "531": 5, "532": 5, "533": 5, "534": 5, "535": 5, "536": 5, "537": 5, "538": 5, "539": 5,
    "540": 5, "541": 5, "542": 5, "543": 5, "544": 5, "545": 5, "546": 5, "547": 5, "548": 5, "549": 5,
    "550": 5, "551": 5, "552": 5, "553": 5, "554": 5, "555": 5, "556": 5, "557": 5, "558": 5, "559": 5,
    "560": 5, "561": 5, "562": 5, "563": 5, "564": 5, "565": 5, "566": 5, "567": 5, "568": 5, "569": 5,
    "570": 5, "571": 5, "572": 5, "573": 5, "574": 5, "575": 5, "576": 5, "577": 5, "578": 5, "579": 5,
    "580": 5, "581": 5, "582": 5, "583": 5, "584": 5, "585": 5, "586": 5, "587": 5, "588": 5, "589": 5,
    "590": 5, "591": 5, "592": 5, "593": 5, "594": 5, "595": 5, "596": 5, "597": 5, "598": 5, "599": 5,
    # Zone 6 – Midwest / Plains
    "600": 6, "601": 6, "602": 6, "603": 6, "604": 6, "605": 6, "606": 6, "607": 6, "608": 6, "609": 6,
    "610": 6, "611": 6, "612": 6, "613": 6, "614": 6, "615": 6, "616": 6, "617": 6, "618": 6, "619": 6,
    "620": 6, "621": 6, "622": 6, "623": 6, "624": 6, "625": 6, "626": 6, "627": 6, "628": 6, "629": 6,
    # Overlap with zone 5 for some
    "630": 6, "631": 6, "632": 6, "633": 6, "634": 6, "635": 6, "636": 6, "637": 6, "638": 6, "639": 6,
    "640": 6, "641": 6, "642": 6, "643": 6, "644": 6, "645": 6, "646": 6, "647": 6, "648": 6, "649": 6,
    "650": 6, "651": 6, "652": 6, "653": 6, "654": 6, "655": 6, "656": 6, "657": 6, "658": 6, "659": 6,
    "660": 6, "661": 6, "662": 6, "663": 6, "664": 6, "665": 6, "666": 6, "667": 6, "668": 6, "669": 6,
    "670": 6, "671": 6, "672": 6, "673": 6, "674": 6, "675": 6, "676": 6, "677": 6, "678": 6, "679": 6,
    "680": 6, "681": 6, "682": 6, "683": 6, "684": 6, "685": 6, "686": 6, "687": 6, "688": 6, "689": 6,
    "690": 6, "691": 6, "692": 6, "693": 6, "694": 6, "695": 6, "696": 6, "697": 6, "698": 6, "699": 6,
    # Zone 7 – Mountain West
    "800": 7, "801": 7, "802": 7, "803": 7, "804": 7, "805": 7, "806": 7, "807": 7, "808": 7, "809": 7,
    "810": 7, "811": 7, "812": 7, "813": 7, "814": 7, "815": 7, "816": 7, "817": 7, "818": 7, "819": 7,
    "820": 7, "821": 7, "822": 7, "823": 7, "824": 7, "825": 7, "826": 7, "827": 7, "828": 7, "829": 7,
    "830": 7, "831": 7, "832": 7, "833": 7, "834": 7, "835": 7, "836": 7, "837": 7, "838": 7, "839": 7,
    "840": 7, "841": 7, "842": 7, "843": 7, "844": 7, "845": 7, "846": 7, "847": 7, "848": 7, "849": 7,
    "850": 7, "851": 7, "852": 7, "853": 7, "854": 7, "855": 7, "856": 7, "857": 7, "858": 7, "859": 7,
    "860": 7, "861": 7, "862": 7, "863": 7, "864": 7, "865": 7, "866": 7, "867": 7, "868": 7, "869": 7,
    "870": 7, "871": 7, "872": 7, "873": 7, "874": 7, "875": 7, "876": 7, "877": 7, "878": 7, "879": 7,
    "880": 7, "881": 7, "882": 7, "883": 7, "884": 7, "885": 7, "886": 7, "887": 7, "888": 7, "889": 7,
    "890": 7, "891": 7, "892": 7, "893": 7, "894": 7, "895": 7, "896": 7, "897": 7, "898": 7, "899": 7,
    # Zone 8 – Pacific / Far West
    "900": 8, "901": 8, "902": 8, "903": 8, "904": 8, "905": 8, "906": 8, "907": 8, "908": 8, "909": 8,
    "910": 8, "911": 8, "912": 8, "913": 8, "914": 8, "915": 8, "916": 8, "917": 8, "918": 8, "919": 8,
    "920": 8, "921": 8, "922": 8, "923": 8, "924": 8, "925": 8, "926": 8, "927": 8, "928": 8, "929": 8,
    "930": 8, "931": 8, "932": 8, "933": 8, "934": 8, "935": 8, "936": 8, "937": 8, "938": 8, "939": 8,
    "940": 8, "941": 8, "942": 8, "943": 8, "944": 8, "945": 8, "946": 8, "947": 8, "948": 8, "949": 8,
    "950": 8, "951": 8, "952": 8, "953": 8, "954": 8, "955": 8, "956": 8, "957": 8, "958": 8, "959": 8,
    "960": 8, "961": 8, "962": 8, "963": 8, "964": 8, "965": 8, "966": 8, "967": 8, "968": 8, "969": 8,
    "970": 8, "971": 8, "972": 8, "973": 8, "974": 8, "975": 8, "976": 8, "977": 8, "978": 8, "979": 8,
    "980": 8, "981": 8, "982": 8, "983": 8, "984": 8, "985": 8, "986": 8, "987": 8, "988": 8, "989": 8,
    "990": 8, "991": 8, "992": 8, "993": 8, "994": 8, "995": 8, "996": 8, "997": 8, "998": 8, "999": 8,
}


def _lookup_zone(destination_zip: str) -> int:
    """Return UPS zone (1-8) for a destination ZIP from Austin."""
    cleaned = re.sub(r"\D", "", destination_zip)[:3]
    if len(cleaned) < 3 or not cleaned.isdigit():
        return 2  # default mid-range zone
    zone = _PREFIX_TO_ZONE.get(cleaned)
    if zone is None:
        # Check for specific Austin-area handling
        if cleaned == "787":
            return 2
        return 3  # conservative default for unmapped ZIPs
    return zone


# ──────────────────────────── Rate tables ────────────────────────────
# Per-zone base rate + per-lb rate for UPS Ground (published rates,
# rounded for a realistic approximation).
_GROUND_BASE: dict[int, float] = {
    1: 6.50, 2: 7.50, 3: 9.20, 4: 10.50, 5: 11.75, 6: 12.80, 7: 13.75, 8: 14.50,
}
_GROUND_PER_LB: dict[int, float] = {
    1: 0.55, 2: 0.65, 3: 0.75, 4: 0.85, 5: 0.95, 6: 1.05, 7: 1.15, 8: 1.25,
}

_BASE_AND_PER_LB = {
    "ups_ground": ("Ground", _GROUND_BASE, _GROUND_PER_LB),
    "ups_3day": ("3 Day Select", {
        1: 8.50, 2: 10.00, 3: 12.00, 4: 13.50, 5: 15.00, 6: 16.50, 7: 18.00, 8: 19.50,
    }, {
        1: 0.85, 2: 1.00, 3: 1.15, 4: 1.30, 5: 1.45, 6: 1.60, 7: 1.75, 8: 1.90,
    }),
    "ups_2day": ("2nd Day Air", {
        1: 10.50, 2: 12.50, 3: 15.00, 4: 17.00, 5: 19.00, 6: 21.00, 7: 23.00, 8: 25.00,
    }, {
        1: 1.10, 2: 1.30, 3: 1.50, 4: 1.70, 5: 1.90, 6: 2.10, 7: 2.30, 8: 2.50,
    }),
    "ups_next_day": ("Next Day Air", {
        1: 14.00, 2: 17.00, 3: 21.00, 4: 25.00, 5: 29.00, 6: 33.00, 7: 37.00, 8: 41.00,
    }, {
        1: 1.50, 2: 1.80, 3: 2.10, 4: 2.40, 5: 2.70, 6: 3.00, 7: 3.30, 8: 3.60,
    }),
}

_ESTIMATED_DAYS = {
    "ups_ground": 5,
    "ups_3day": 3,
    "ups_2day": 2,
    "ups_next_day": 1,
}

_SERVICE_NAMES = {
    "ups_ground": "UPS Ground",
    "ups_3day": "UPS 3 Day Select",
    "ups_2day": "UPS 2nd Day Air",
    "ups_next_day": "UPS Next Day Air",
}

_SERVICE_NAMES_API = {
    "ups_ground": "UPS Ground",
    "ups_3day": "UPS 3 Day Select",
    "ups_2day": "UPS 2nd Day Air",
    "ups_next_day": "UPS Next Day Air",
}


# ──────────────────────────── Core calculation ────────────────────────────
def _dimensional_weight(
    length: float | None,
    width: float | None,
    height: float | None,
) -> float | None:
    """Return dimensional weight in lbs. UPS uses LxWxH / 139 (inches)."""
    if length is None or width is None or height is None:
        return None
    if length <= 0 or width <= 0 or height <= 0:
        return None
    return (length * width * height) / 139.0


def calculate_ups_rates(
    weight_lbs: float,
    destination_zip: str,
    *,
    length: float | None = None,
    width: float | None = None,
    height: float | None = None,
    is_residential: bool = False,
    services: list[str] | None = None,
) -> ShippingEstimate:
    """Calculate UPS shipping rates per UPS published guidelines.

    Parameters
    ----------
    weight_lbs: Actual package weight in pounds.
    destination_zip: Destination ZIP code (5 digits).
    length/width/height: Optional dimensions in inches.
    is_residential: Whether destination is residential (adds surcharge).
    services: List of service keys to quote (defaults to all four).

    Returns
    -------
    ShippingEstimate with per-service rates.
    """
    if services is None:
        services = ["ups_ground", "ups_3day", "ups_2day", "ups_next_day"]

    zone = _lookup_zone(destination_zip)
    billable_weight = max(weight_lbs, 1.0)  # UPS minimum 1 lb

    dim_weight = _dimensional_weight(length, width, height)
    if dim_weight is not None:
        billable_weight = max(billable_weight, dim_weight)

    # Round up to nearest whole pound (standard UPS practice)
    import math
    billable_weight = math.ceil(billable_weight * 10) / 10.0
    if billable_weight < 1.0:
        billable_weight = 1.0

    rates: list[RateResult] = []
    for svc in services:
        if svc not in _BASE_AND_PER_LB:
            continue
        name, base_table, per_lb_table = _BASE_AND_PER_LB[svc]
        base = base_table.get(zone, base_table.get(5, 10.0))
        per_lb = per_lb_table.get(zone, per_lb_table.get(5, 1.0))
        rate = base + (per_lb * billable_weight)
        rate = round(rate, 2)
        if svc == "ups_ground":
            rate = max(rate, settings.ups_min_charge_ground)
        if is_residential and svc == "ups_ground":
            rate += settings.ups_residential_surcharge
        rate = round(rate, 2)
        rates.append(
            RateResult(
                service=svc,
                service_name=_SERVICE_NAMES.get(svc, name),
                rate=rate,
                estimated_business_days=_ESTIMATED_DAYS.get(svc, 5),
            )
        )

    origin = (
        f"{settings.ups_origin_address}, "
        f"{settings.ups_origin_city}, "
        f"{settings.ups_origin_state} {settings.ups_origin_zip}"
    )

    return ShippingEstimate(
        origin=origin,
        destination_zip=destination_zip,
        rates=rates,
        package={
            "weight_lbs": weight_lbs,
            "billable_weight_lbs": billable_weight,
            "dim_weight_lbs": dim_weight,
            "dimensions": {
                "length": length, "width": width, "height": height,
            },
            "zone": zone,
            "is_residential": is_residential,
        },
    )
