import json

with open("config.json") as conf:
    configData = json.load(conf)


def getConfigStatus(key):
    with open("config.json") as f:
        return json.load(f)[key]


def setConfigStatus(key, value):
    with open("config.json") as f:
        data = json.load(f)
    data[key] = value
    with open("config.json", "w") as outfile:
        outfile.write(json.dumps(data, indent=4))


pb_token = configData.get("pushbutton_token", "")
pushbutton_device_iden = configData.get("pushbutton_device_iden", "")

# Le token peut être stocké avec ou sans préfixe "JWT " (héritage v1).
# L'API v2 attend "Authorization: Bearer <token brut>".
wfm_token = configData.get("wfm_jwt_token", "").split(" ")[-1]

inGameName = configData.get("inGameName", "")
platform = configData.get("platform", "pc").lower() or "pc"
webhookLink = configData.get("webhookLink", "")

with open("settings.json") as settings:
    data = json.load(settings)

blacklistedItems = data.get("blacklistedItems", [])
whitelistedItems = data.get("whitelistedItems", [])
strictWhitelist = data.get("strictWhitelist", False)
priceShiftThreshold = data.get("priceShiftThreshold", -1)
avgPriceCap = data.get("avgPriceCap", 600)
maxTotalPlatCap = data.get("maxTotalPlatCap", 1000)
volumeThreshold = data.get("volumeThreshold", 15)
rangeThreshold = data.get("rangeThreshold", 10)
pingOnNotif = data.get("pingOnNotif", False)
