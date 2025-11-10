"""전국 주요 시/도 및 시/군/구 좌표 데이터"""

# 서울 25개 구
SEOUL_DISTRICTS = [
    {"name": "강남구", "region": "서울", "longitude": 127.0495556, "latitude": 37.514575},
    {"name": "강동구", "region": "서울", "longitude": 127.1237708, "latitude": 37.52736667},
    {"name": "강북구", "region": "서울", "longitude": 127.0277194, "latitude": 37.6395444},
    {"name": "강서구", "region": "서울", "longitude": 126.8495972, "latitude": 37.5509722},
    {"name": "관악구", "region": "서울", "longitude": 126.9515667, "latitude": 37.4781528},
    {"name": "광진구", "region": "서울", "longitude": 127.0845333, "latitude": 37.5384444},
    {"name": "구로구", "region": "서울", "longitude": 126.8895972, "latitude": 37.4954444},
    {"name": "금천구", "region": "서울", "longitude": 126.9001417, "latitude": 37.4519444},
    {"name": "노원구", "region": "서울", "longitude": 127.0583889, "latitude": 37.6542778},
    {"name": "도봉구", "region": "서울", "longitude": 127.0495222, "latitude": 37.6688889},
    {"name": "동대문구", "region": "서울", "longitude": 127.0421417, "latitude": 37.5742778},
    {"name": "동작구", "region": "서울", "longitude": 126.9395556, "latitude": 37.5124361},
    {"name": "마포구", "region": "서울", "longitude": 126.9052778, "latitude": 37.5663889},
    {"name": "서대문구", "region": "서울", "longitude": 126.9368472, "latitude": 37.5791111},
    {"name": "서초구", "region": "서울", "longitude": 127.0276194, "latitude": 37.4836111},
    {"name": "성동구", "region": "서울", "longitude": 127.0379306, "latitude": 37.5633611},
    {"name": "성북구", "region": "서울", "longitude": 127.0203333, "latitude": 37.5894444},
    {"name": "송파구", "region": "서울", "longitude": 127.1079306, "latitude": 37.5145556},
    {"name": "양천구", "region": "서울", "longitude": 126.8687083, "latitude": 37.5170028},
    {"name": "영등포구", "region": "서울", "longitude": 126.8983417, "latitude": 37.5263889},
    {"name": "용산구", "region": "서울", "longitude": 126.9816667, "latitude": 37.5311111},
    {"name": "은평구", "region": "서울", "longitude": 126.9312417, "latitude": 37.6176111},
    {"name": "종로구", "region": "서울", "longitude": 126.9816417, "latitude": 37.5730556},
    {"name": "중구", "region": "서울", "longitude": 126.9979417, "latitude": 37.5636111},
    {"name": "중랑구", "region": "서울", "longitude": 127.0947696, "latitude": 37.6063056},
]

# 부산 16개 구/군
BUSAN_DISTRICTS = [
    {"name": "강서구", "region": "부산", "longitude": 128.9811667, "latitude": 35.2122222},
    {"name": "금정구", "region": "부산", "longitude": 129.0927778, "latitude": 35.2422222},
    {"name": "기장군", "region": "부산", "longitude": 129.2222222, "latitude": 35.2444444},
    {"name": "남구", "region": "부산", "longitude": 129.0841667, "latitude": 35.1361111},
    {"name": "동구", "region": "부산", "longitude": 129.0455556, "latitude": 35.1294444},
    {"name": "동래구", "region": "부산", "longitude": 129.0838889, "latitude": 35.2047222},
    {"name": "부산진구", "region": "부산", "longitude": 129.0525, "latitude": 35.1625},
    {"name": "북구", "region": "부산", "longitude": 128.9911111, "latitude": 35.1947222},
    {"name": "사상구", "region": "부산", "longitude": 128.9911111, "latitude": 35.1497222},
    {"name": "사하구", "region": "부산", "longitude": 128.9741667, "latitude": 35.1044444},
    {"name": "서구", "region": "부산", "longitude": 129.0241667, "latitude": 35.0977778},
    {"name": "수영구", "region": "부산", "longitude": 129.1136111, "latitude": 35.1452778},
    {"name": "연제구", "region": "부산", "longitude": 129.0822222, "latitude": 35.1763889},
    {"name": "영도구", "region": "부산", "longitude": 129.0688889, "latitude": 35.0913889},
    {"name": "중구", "region": "부산", "longitude": 129.0322222, "latitude": 35.1063889},
    {"name": "해운대구", "region": "부산", "longitude": 129.1600000, "latitude": 35.1627778},
]

# 인천 10개 구/군
INCHEON_DISTRICTS = [
    {"name": "계양구", "region": "인천", "longitude": 126.7375, "latitude": 37.5377778},
    {"name": "남동구", "region": "인천", "longitude": 126.7313889, "latitude": 37.4475},
    {"name": "동구", "region": "인천", "longitude": 126.6333333, "latitude": 37.4738889},
    {"name": "미추홀구", "region": "인천", "longitude": 126.6505556, "latitude": 37.4633333},
    {"name": "부평구", "region": "인천", "longitude": 126.7219444, "latitude": 37.5072222},
    {"name": "서구", "region": "인천", "longitude": 126.6758333, "latitude": 37.5452778},
    {"name": "연수구", "region": "인천", "longitude": 126.6783333, "latitude": 37.4105556},
    {"name": "중구", "region": "인천", "longitude": 126.6213889, "latitude": 37.4738889},
    {"name": "강화군", "region": "인천", "longitude": 126.4880556, "latitude": 37.7466667},
    {"name": "옹진군", "region": "인천", "longitude": 126.6363889, "latitude": 37.4466667},
]

# 대구 8개 구/군
DAEGU_DISTRICTS = [
    {"name": "남구", "region": "대구", "longitude": 128.5975, "latitude": 35.8463889},
    {"name": "달서구", "region": "대구", "longitude": 128.5325, "latitude": 35.8297222},
    {"name": "동구", "region": "대구", "longitude": 128.6347222, "latitude": 35.8869444},
    {"name": "북구", "region": "대구", "longitude": 128.5827778, "latitude": 35.8858333},
    {"name": "서구", "region": "대구", "longitude": 128.5591667, "latitude": 35.8719444},
    {"name": "수성구", "region": "대구", "longitude": 128.6308333, "latitude": 35.8580556},
    {"name": "중구", "region": "대구", "longitude": 128.6061111, "latitude": 35.8691667},
    {"name": "달성군", "region": "대구", "longitude": 128.4311111, "latitude": 35.7744444},
]

# 대전 5개 구
DAEJEON_DISTRICTS = [
    {"name": "대덕구", "region": "대전", "longitude": 127.4155556, "latitude": 36.3466667},
    {"name": "동구", "region": "대전", "longitude": 127.4547222, "latitude": 36.3113889},
    {"name": "서구", "region": "대전", "longitude": 127.3841667, "latitude": 36.3552778},
    {"name": "유성구", "region": "대전", "longitude": 127.3566667, "latitude": 36.3622222},
    {"name": "중구", "region": "대전", "longitude": 127.4213889, "latitude": 36.3255556},
]

# 광주 5개 구
GWANGJU_DISTRICTS = [
    {"name": "광산구", "region": "광주", "longitude": 126.7938889, "latitude": 35.1397222},
    {"name": "남구", "region": "광주", "longitude": 126.9025, "latitude": 35.1327778},
    {"name": "동구", "region": "광주", "longitude": 126.9147222, "latitude": 35.1458333},
    {"name": "북구", "region": "광주", "longitude": 126.9122222, "latitude": 35.1741667},
    {"name": "서구", "region": "광주", "longitude": 126.8930556, "latitude": 35.1522222},
]

# 울산 5개 구/군
ULSAN_DISTRICTS = [
    {"name": "남구", "region": "울산", "longitude": 129.3302778, "latitude": 35.5438889},
    {"name": "동구", "region": "울산", "longitude": 129.4161111, "latitude": 35.5044444},
    {"name": "북구", "region": "울산", "longitude": 129.3611111, "latitude": 35.5825},
    {"name": "중구", "region": "울산", "longitude": 129.3336111, "latitude": 35.5688889},
    {"name": "울주군", "region": "울산", "longitude": 129.1563889, "latitude": 35.5819444},
]

# 세종시
SEJONG_DISTRICTS = [
    {"name": "세종시", "region": "세종", "longitude": 127.2890000, "latitude": 36.4800000},
]

# 경기도 주요 시/군 (31개 시/군)
GYEONGGI_CITIES = [
    {"name": "수원시", "region": "경기", "longitude": 127.0286111, "latitude": 37.2636111},
    {"name": "성남시", "region": "경기", "longitude": 127.1372222, "latitude": 37.4200000},
    {"name": "고양시", "region": "경기", "longitude": 126.8350000, "latitude": 37.6583333},
    {"name": "용인시", "region": "경기", "longitude": 127.1777778, "latitude": 37.2411111},
    {"name": "부천시", "region": "경기", "longitude": 126.7830556, "latitude": 37.5036111},
    {"name": "안산시", "region": "경기", "longitude": 126.8308333, "latitude": 37.3216667},
    {"name": "안양시", "region": "경기", "longitude": 126.9566667, "latitude": 37.3944444},
    {"name": "남양주시", "region": "경기", "longitude": 127.2163889, "latitude": 37.6361111},
    {"name": "화성시", "region": "경기", "longitude": 126.8311111, "latitude": 37.1997222},
    {"name": "평택시", "region": "경기", "longitude": 127.1127778, "latitude": 36.9922222},
    {"name": "의정부시", "region": "경기", "longitude": 127.0477778, "latitude": 37.7380556},
    {"name": "시흥시", "region": "경기", "longitude": 126.8027778, "latitude": 37.3802778},
    {"name": "파주시", "region": "경기", "longitude": 126.7797222, "latitude": 37.7597222},
    {"name": "김포시", "region": "경기", "longitude": 126.7155556, "latitude": 37.6152778},
    {"name": "광명시", "region": "경기", "longitude": 126.8644444, "latitude": 37.4786111},
    {"name": "광주시", "region": "경기", "longitude": 127.2552778, "latitude": 37.4297222},
    {"name": "군포시", "region": "경기", "longitude": 126.9352778, "latitude": 37.3616667},
    {"name": "이천시", "region": "경기", "longitude": 127.4350000, "latitude": 37.2722222},
    {"name": "양주시", "region": "경기", "longitude": 127.0452778, "latitude": 37.7852778},
    {"name": "오산시", "region": "경기", "longitude": 127.0772222, "latitude": 37.1497222},
    {"name": "구리시", "region": "경기", "longitude": 127.1294444, "latitude": 37.5941667},
    {"name": "안성시", "region": "경기", "longitude": 127.2797222, "latitude": 37.0080556},
    {"name": "포천시", "region": "경기", "longitude": 127.2000000, "latitude": 38.0311111},
    {"name": "의왕시", "region": "경기", "longitude": 126.9686111, "latitude": 37.3447222},
    {"name": "하남시", "region": "경기", "longitude": 127.2147222, "latitude": 37.5391667},
    {"name": "여주시", "region": "경기", "longitude": 127.6377778, "latitude": 37.2980556},
    {"name": "양평군", "region": "경기", "longitude": 127.4872222, "latitude": 37.4911111},
    {"name": "동두천시", "region": "경기", "longitude": 127.0605556, "latitude": 37.9038889},
    {"name": "과천시", "region": "경기", "longitude": 127.0138889, "latitude": 37.4291667},
    {"name": "가평군", "region": "경기", "longitude": 127.5097222, "latitude": 37.8313889},
    {"name": "연천군", "region": "경기", "longitude": 127.0752778, "latitude": 38.0961111},
]

# 강원도 주요 시/군 (18개)
GANGWON_CITIES = [
    {"name": "춘천시", "region": "강원", "longitude": 127.7302778, "latitude": 37.8813889},
    {"name": "원주시", "region": "강원", "longitude": 127.9202778, "latitude": 37.3422222},
    {"name": "강릉시", "region": "강원", "longitude": 128.8758333, "latitude": 37.7513889},
    {"name": "동해시", "region": "강원", "longitude": 129.1144444, "latitude": 37.5247222},
    {"name": "태백시", "region": "강원", "longitude": 128.9858333, "latitude": 37.1638889},
    {"name": "속초시", "region": "강원", "longitude": 128.5916667, "latitude": 38.2072222},
    {"name": "삼척시", "region": "강원", "longitude": 129.1647222, "latitude": 37.4497222},
    {"name": "홍천군", "region": "강원", "longitude": 127.8886111, "latitude": 37.6969444},
    {"name": "횡성군", "region": "강원", "longitude": 127.9861111, "latitude": 37.4827778},
    {"name": "영월군", "region": "강원", "longitude": 128.4613889, "latitude": 37.1836111},
    {"name": "평창군", "region": "강원", "longitude": 128.3900000, "latitude": 37.3702778},
    {"name": "정선군", "region": "강원", "longitude": 128.6580556, "latitude": 37.3802778},
    {"name": "철원군", "region": "강원", "longitude": 127.3133333, "latitude": 38.1466667},
    {"name": "화천군", "region": "강원", "longitude": 127.7080556, "latitude": 38.1063889},
    {"name": "양구군", "region": "강원", "longitude": 127.9897222, "latitude": 38.1097222},
    {"name": "인제군", "region": "강원", "longitude": 128.1705556, "latitude": 38.0697222},
    {"name": "고성군", "region": "강원", "longitude": 128.4672222, "latitude": 38.3800000},
    {"name": "양양군", "region": "강원", "longitude": 128.6191667, "latitude": 38.0752778},
]

# 충청북도 주요 시/군 (11개)
CHUNGBUK_CITIES = [
    {"name": "청주시", "region": "충북", "longitude": 127.4891667, "latitude": 36.6372222},
    {"name": "충주시", "region": "충북", "longitude": 127.9261111, "latitude": 36.9911111},
    {"name": "제천시", "region": "충북", "longitude": 128.1911111, "latitude": 37.1325},
    {"name": "보은군", "region": "충북", "longitude": 127.7294444, "latitude": 36.4891667},
    {"name": "옥천군", "region": "충북", "longitude": 127.5719444, "latitude": 36.3011111},
    {"name": "영동군", "region": "충북", "longitude": 127.7836111, "latitude": 36.1750000},
    {"name": "증평군", "region": "충북", "longitude": 127.5825, "latitude": 36.7855556},
    {"name": "진천군", "region": "충북", "longitude": 127.4361111, "latitude": 36.8550000},
    {"name": "괴산군", "region": "충북", "longitude": 127.7872222, "latitude": 36.8152778},
    {"name": "음성군", "region": "충북", "longitude": 127.6913889, "latitude": 36.9402778},
    {"name": "단양군", "region": "충북", "longitude": 128.3658333, "latitude": 36.9844444},
]

# 충청남도 주요 시/군 (15개)
CHUNGNAM_CITIES = [
    {"name": "천안시", "region": "충남", "longitude": 127.1522222, "latitude": 36.8152778},
    {"name": "공주시", "region": "충남", "longitude": 127.1247222, "latitude": 36.4452778},
    {"name": "보령시", "region": "충남", "longitude": 126.6127778, "latitude": 36.3333333},
    {"name": "아산시", "region": "충남", "longitude": 127.0016667, "latitude": 36.7897222},
    {"name": "서산시", "region": "충남", "longitude": 126.4502778, "latitude": 36.7844444},
    {"name": "논산시", "region": "충남", "longitude": 127.0986111, "latitude": 36.1869444},
    {"name": "계룡시", "region": "충남", "longitude": 127.2480556, "latitude": 36.2744444},
    {"name": "당진시", "region": "충남", "longitude": 126.6469444, "latitude": 36.8930556},
    {"name": "금산군", "region": "충남", "longitude": 127.4883333, "latitude": 36.1086111},
    {"name": "부여군", "region": "충남", "longitude": 126.9097222, "latitude": 36.2752778},
    {"name": "서천군", "region": "충남", "longitude": 126.6916667, "latitude": 36.0797222},
    {"name": "청양군", "region": "충남", "longitude": 126.8022222, "latitude": 36.4591667},
    {"name": "홍성군", "region": "충남", "longitude": 126.6608333, "latitude": 36.6011111},
    {"name": "예산군", "region": "충남", "longitude": 126.8477778, "latitude": 36.6819444},
    {"name": "태안군", "region": "충남", "longitude": 126.2980556, "latitude": 36.7452778},
]

# 전라북도 주요 시/군 (14개)
JEONBUK_CITIES = [
    {"name": "전주시", "region": "전북", "longitude": 127.1480556, "latitude": 35.8244444},
    {"name": "군산시", "region": "전북", "longitude": 126.7372222, "latitude": 35.9677778},
    {"name": "익산시", "region": "전북", "longitude": 126.9544444, "latitude": 35.9483333},
    {"name": "정읍시", "region": "전북", "longitude": 126.8561111, "latitude": 35.5697222},
    {"name": "남원시", "region": "전북", "longitude": 127.3902778, "latitude": 35.4163889},
    {"name": "김제시", "region": "전북", "longitude": 126.8808333, "latitude": 35.8033333},
    {"name": "완주군", "region": "전북", "longitude": 127.1641667, "latitude": 35.9050000},
    {"name": "진안군", "region": "전북", "longitude": 127.4247222, "latitude": 35.7916667},
    {"name": "무주군", "region": "전북", "longitude": 127.6602778, "latitude": 36.0066667},
    {"name": "장수군", "region": "전북", "longitude": 127.5219444, "latitude": 35.6477778},
    {"name": "임실군", "region": "전북", "longitude": 127.2861111, "latitude": 35.6177778},
    {"name": "순창군", "region": "전북", "longitude": 127.1375, "latitude": 35.3744444},
    {"name": "고창군", "region": "전북", "longitude": 126.7025, "latitude": 35.4352778},
    {"name": "부안군", "region": "전북", "longitude": 126.7338889, "latitude": 35.7316667},
]

# 전라남도 주요 시/군 (22개)
JEONNAM_CITIES = [
    {"name": "목포시", "region": "전남", "longitude": 126.3922222, "latitude": 34.8116667},
    {"name": "여수시", "region": "전남", "longitude": 127.6622222, "latitude": 34.7605556},
    {"name": "순천시", "region": "전남", "longitude": 127.4877778, "latitude": 34.9508333},
    {"name": "나주시", "region": "전남", "longitude": 126.7108333, "latitude": 35.0163889},
    {"name": "광양시", "region": "전남", "longitude": 127.6955556, "latitude": 34.9405556},
    {"name": "담양군", "region": "전남", "longitude": 126.9880556, "latitude": 35.3208333},
    {"name": "곡성군", "region": "전남", "longitude": 127.2916667, "latitude": 35.2816667},
    {"name": "구례군", "region": "전남", "longitude": 127.4633333, "latitude": 35.2022222},
    {"name": "고흥군", "region": "전남", "longitude": 127.2752778, "latitude": 34.6111111},
    {"name": "보성군", "region": "전남", "longitude": 127.0800000, "latitude": 34.7713889},
    {"name": "화순군", "region": "전남", "longitude": 126.9858333, "latitude": 35.0641667},
    {"name": "장흥군", "region": "전남", "longitude": 126.9066667, "latitude": 34.6813889},
    {"name": "강진군", "region": "전남", "longitude": 126.7672222, "latitude": 34.6419444},
    {"name": "해남군", "region": "전남", "longitude": 126.5986111, "latitude": 34.5730556},
    {"name": "영암군", "region": "전남", "longitude": 126.6966667, "latitude": 34.8002778},
    {"name": "무안군", "region": "전남", "longitude": 126.4816667, "latitude": 34.9902778},
    {"name": "함평군", "region": "전남", "longitude": 126.5163889, "latitude": 35.0655556},
    {"name": "영광군", "region": "전남", "longitude": 126.5119444, "latitude": 35.2772222},
    {"name": "장성군", "region": "전남", "longitude": 126.7841667, "latitude": 35.3019444},
    {"name": "완도군", "region": "전남", "longitude": 126.7550000, "latitude": 34.3105556},
    {"name": "진도군", "region": "전남", "longitude": 126.2636111, "latitude": 34.4872222},
    {"name": "신안군", "region": "전남", "longitude": 126.1080556, "latitude": 34.8272222},
]

# 경상북도 주요 시/군 (23개)
GYEONGBUK_CITIES = [
    {"name": "포항시", "region": "경북", "longitude": 129.3650000, "latitude": 36.0191667},
    {"name": "경주시", "region": "경북", "longitude": 129.2247222, "latitude": 35.8563889},
    {"name": "김천시", "region": "경북", "longitude": 128.1138889, "latitude": 36.1397222},
    {"name": "안동시", "region": "경북", "longitude": 128.7294444, "latitude": 36.5683333},
    {"name": "구미시", "region": "경북", "longitude": 128.3444444, "latitude": 36.1194444},
    {"name": "영주시", "region": "경북", "longitude": 128.6238889, "latitude": 36.8058333},
    {"name": "영천시", "region": "경북", "longitude": 128.9386111, "latitude": 35.9730556},
    {"name": "상주시", "region": "경북", "longitude": 128.1591667, "latitude": 36.4108333},
    {"name": "문경시", "region": "경북", "longitude": 128.1872222, "latitude": 36.5863889},
    {"name": "경산시", "region": "경북", "longitude": 128.7413889, "latitude": 35.8252778},
    {"name": "군위군", "region": "경북", "longitude": 128.5727778, "latitude": 36.2427778},
    {"name": "의성군", "region": "경북", "longitude": 128.6972222, "latitude": 36.3527778},
    {"name": "청송군", "region": "경북", "longitude": 129.0572222, "latitude": 36.4363889},
    {"name": "영양군", "region": "경북", "longitude": 129.1125, "latitude": 36.6666667},
    {"name": "영덕군", "region": "경북", "longitude": 129.3655556, "latitude": 36.4147222},
    {"name": "청도군", "region": "경북", "longitude": 128.7352778, "latitude": 35.6463889},
    {"name": "고령군", "region": "경북", "longitude": 128.2633333, "latitude": 35.7269444},
    {"name": "성주군", "region": "경북", "longitude": 128.2827778, "latitude": 35.9194444},
    {"name": "칠곡군", "region": "경북", "longitude": 128.4019444, "latitude": 35.9947222},
    {"name": "예천군", "region": "경북", "longitude": 128.4519444, "latitude": 36.6555556},
    {"name": "봉화군", "region": "경북", "longitude": 128.7325, "latitude": 36.8930556},
    {"name": "울진군", "region": "경북", "longitude": 129.4002778, "latitude": 36.9930556},
    {"name": "울릉군", "region": "경북", "longitude": 130.9058333, "latitude": 37.4844444},
]

# 경상남도 주요 시/군 (18개)
GYEONGNAM_CITIES = [
    {"name": "창원시", "region": "경남", "longitude": 128.6811111, "latitude": 35.2280556},
    {"name": "진주시", "region": "경남", "longitude": 128.1086111, "latitude": 35.1800000},
    {"name": "통영시", "region": "경남", "longitude": 128.4333333, "latitude": 34.8544444},
    {"name": "사천시", "region": "경남", "longitude": 128.0641667, "latitude": 35.0036111},
    {"name": "김해시", "region": "경남", "longitude": 128.8894444, "latitude": 35.2283333},
    {"name": "밀양시", "region": "경남", "longitude": 128.7461111, "latitude": 35.5038889},
    {"name": "거제시", "region": "경남", "longitude": 128.6211111, "latitude": 34.8808333},
    {"name": "양산시", "region": "경남", "longitude": 129.0372222, "latitude": 35.3350000},
    {"name": "의령군", "region": "경남", "longitude": 128.2613889, "latitude": 35.3219444},
    {"name": "함안군", "region": "경남", "longitude": 128.4061111, "latitude": 35.2722222},
    {"name": "창녕군", "region": "경남", "longitude": 128.4922222, "latitude": 35.5444444},
    {"name": "고성군", "region": "경남", "longitude": 128.3230556, "latitude": 34.9730556},
    {"name": "남해군", "region": "경남", "longitude": 127.8922222, "latitude": 34.8375000},
    {"name": "하동군", "region": "경남", "longitude": 127.7511111, "latitude": 35.0672222},
    {"name": "산청군", "region": "경남", "longitude": 127.8736111, "latitude": 35.4152778},
    {"name": "함양군", "region": "경남", "longitude": 127.7252778, "latitude": 35.5202778},
    {"name": "거창군", "region": "경남", "longitude": 127.9097222, "latitude": 35.6863889},
    {"name": "합천군", "region": "경남", "longitude": 128.1658333, "latitude": 35.5663889},
]

# 제주도
JEJU_CITIES = [
    {"name": "제주시", "region": "제주", "longitude": 126.5219444, "latitude": 33.4997222},
    {"name": "서귀포시", "region": "제주", "longitude": 126.5622222, "latitude": 33.2541667},
]

# 전체 지역 통합
ALL_REGIONS = (
    SEOUL_DISTRICTS
    + BUSAN_DISTRICTS
    + INCHEON_DISTRICTS
    + DAEGU_DISTRICTS
    + DAEJEON_DISTRICTS
    + GWANGJU_DISTRICTS
    + ULSAN_DISTRICTS
    + SEJONG_DISTRICTS
    + GYEONGGI_CITIES
    + GANGWON_CITIES
    + CHUNGBUK_CITIES
    + CHUNGNAM_CITIES
    + JEONBUK_CITIES
    + JEONNAM_CITIES
    + GYEONGBUK_CITIES
    + GYEONGNAM_CITIES
    + JEJU_CITIES
)

# 카테고리 코드
CATEGORY_CODES = {
    "food": "FD6",  # 음식점
    "tourism": "AT4",  # 관광명소
    "cafe": "CE7",  # 카페
    "accommodation": "AD5",  # 숙박
    "culture": "CT1",  # 문화시설
}

# 지역별 그룹화
REGIONS_BY_AREA = {
    "서울": SEOUL_DISTRICTS,
    "부산": BUSAN_DISTRICTS,
    "인천": INCHEON_DISTRICTS,
    "대구": DAEGU_DISTRICTS,
    "대전": DAEJEON_DISTRICTS,
    "광주": GWANGJU_DISTRICTS,
    "울산": ULSAN_DISTRICTS,
    "세종": SEJONG_DISTRICTS,
    "경기": GYEONGGI_CITIES,
    "강원": GANGWON_CITIES,
    "충북": CHUNGBUK_CITIES,
    "충남": CHUNGNAM_CITIES,
    "전북": JEONBUK_CITIES,
    "전남": JEONNAM_CITIES,
    "경북": GYEONGBUK_CITIES,
    "경남": GYEONGNAM_CITIES,
    "제주": JEJU_CITIES,
}

print(f"전체 지역 수: {len(ALL_REGIONS)}개")
