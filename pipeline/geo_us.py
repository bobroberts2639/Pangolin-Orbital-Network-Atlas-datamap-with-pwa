import csv, unicodedata, collections, re
ST = dict(AL="Alabama",AK="Alaska",AZ="Arizona",AR="Arkansas",CA="California",CO="Colorado",CT="Connecticut",DE="Delaware",FL="Florida",GA="Georgia",HI="Hawaii",ID="Idaho",IL="Illinois",IN="Indiana",IA="Iowa",KS="Kansas",KY="Kentucky",LA="Louisiana",ME="Maine",MD="Maryland",MA="Massachusetts",MI="Michigan",MN="Minnesota",MS="Mississippi",MO="Missouri",MT="Montana",NE="Nebraska",NV="Nevada",NH="New Hampshire",NJ="New Jersey",NM="New Mexico",NY="New York",NC="North Carolina",ND="North Dakota",OH="Ohio",OK="Oklahoma",OR="Oregon",PA="Pennsylvania",RI="Rhode Island",SC="South Carolina",SD="South Dakota",TN="Tennessee",TX="Texas",UT="Utah",VT="Vermont",VA="Virginia",WA="Washington",WV="West Virginia",WI="Wisconsin",WY="Wyoming")
def norm(s): return ''.join(c for c in unicodedata.normalize('NFKD', s.lower()) if not unicodedata.combining(c)).replace(".", "").replace("-", " ").strip()
IDX = collections.defaultdict(list)
for r in csv.DictReader(open('/home/claude/sat/raw/rg_cities1000.csv')):
    if r['cc'] in ('US', 'AS', 'PR', 'GU'): IDX[norm(r['name'])].append(r)
# small places missing from cities1000 (town-level, approximate)
MANUAL = {("deadhorse","AK"):(70.20,-148.46),("utqiagvik","AK"):(71.29,-156.79),("tafuna","AS"):(-14.33,-170.72),
          ("paumalu","HI"):(21.67,-158.03),("haleiwa","HI"):(21.59,-158.10),("maui","HI"):(20.80,-156.33),("ellenwood","GA"):(33.63,-84.26),
          ("tornillo","TX"):(31.45,-106.08),("lovelock","NV"):(40.18,-118.47),("nuevo","CA"):(33.80,-117.15),("summit point","WV"):(39.24,-77.96),("andover","ME"):(44.63,-70.70),("hagerstown","MD"):(39.64,-77.72),("caneyville","KY"):(37.42,-86.49),("tremont","MS"):(34.23,-88.26),("loretto","KY"):(37.63,-85.40),("new knoxville","OH"):(40.49,-84.31),("centerview","MO"):(38.74,-93.84)}
def geocode(town, st):
    k = norm(town)
    if (k, st) in MANUAL: return MANUAL[(k, st)] + ("manual",)
    for r in IDX.get(k, []):
        if r['admin1'] == ST.get(st): return (float(r['lat']), float(r['lon']), "geonames")
    return None
