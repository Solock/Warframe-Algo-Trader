import json
import logging
import math
import time

import requests

import config
import customLogger

# API v2 : https://docs.warframe.market/docs/api/overview/
# Le signin v2 est réservé aux clients first-party (Firebase App Check) ;
# le flow v1 reste supporté et ses tokens ont le scope "all" sur la v2.
WFM_API = "https://api.warframe.market/v2"
WFM_AUTH_API = "https://api.warframe.market/v1"

USER_AGENT = "WarframeAlgoTrader/2.0 (github.com/Solock/Warframe-Algo-Trader)"

# Limite publique : 3 req/s. On reste en dessous.
MIN_REQUEST_INTERVAL = 0.5
REQUEST_TIMEOUT = 15
MAX_ATTEMPTS = 3


def isDryRun():
    # Défaut True : sans le flag, on n'écrit rien sur le compte réel.
    try:
        with open("settings.json") as settingsFile:
            return bool(json.load(settingsFile).get("dryRun", True))
    except (FileNotFoundError, json.JSONDecodeError):
        return True


def _toBool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() == "true"
    return bool(value)


def _toRank(value):
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    return int(value)


class FakeResponse:
    """Réponse simulée renvoyée par les écritures en mode dry-run."""

    def __init__(self, payload, status_code=200):
        self.status_code = status_code
        self.ok = 200 <= status_code < 300
        self._payload = payload

    def json(self):
        return self._payload


class WarframeApi:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/json",
                "User-Agent": USER_AGENT,
                "Platform": config.platform or "pc",
                "Language": "en",
                "Authorization": f"Bearer {config.wfm_token}",
            }
        )
        self.lastRequestTime = 0.0

    def _waitForRateLimit(self):
        elapsed = time.time() - self.lastRequestTime
        if elapsed < MIN_REQUEST_INTERVAL:
            time.sleep(MIN_REQUEST_INTERVAL - elapsed)

    def request(self, method, url, json=None):
        lastError = None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            self._waitForRateLimit()
            self.lastRequestTime = time.time()
            try:
                r = self.session.request(method, url, json=json, timeout=REQUEST_TIMEOUT)
            except requests.RequestException as err:
                lastError = err
                customLogger.writeTo(
                    "wfmAPICalls.log",
                    f"{method}:{url}\tERREUR RESEAU (essai {attempt}/{MAX_ATTEMPTS}): {err}",
                )
                time.sleep(2 * attempt)
                continue

            customLogger.writeTo("wfmAPICalls.log", f"{method}:{url}\tResponse:{r.status_code}")

            if r.status_code == 429 or r.status_code >= 500:
                customLogger.writeTo(
                    "wfmAPICalls.log",
                    f"{method}:{url}\tRetry {attempt}/{MAX_ATTEMPTS} sur {r.status_code}",
                )
                time.sleep(2 * attempt)
                continue

            if not r.ok:
                customLogger.writeTo(
                    "wfmAPICalls.log", f"{method}:{url}\tBody:{r.text[:300]}"
                )
            return r

        raise requests.ConnectionError(
            f"{method} {url} en échec après {MAX_ATTEMPTS} essais ({lastError})"
        )

    def get(self, url):
        return self.request("GET", url)

    def post(self, url, json=None):
        return self.request("POST", url, json=json)

    def patch(self, url, json=None):
        return self.request("PATCH", url, json=json)

    def delete(self, url):
        return self.request("DELETE", url)


warframeApi = WarframeApi()


# --- Cache items (id <-> slug <-> nom affiché) ---------------------------------

_allItems = None


def getAllItems():
    global _allItems
    if _allItems is None:
        r = warframeApi.get(f"{WFM_API}/items")
        if r.status_code != 200:
            raise RuntimeError(f"GET /v2/items -> {r.status_code}")
        _allItems = r.json()["data"]
    return _allItems


def getSlugToId():
    return {item["slug"]: item["id"] for item in getAllItems()}


def getIdToSlug():
    return {item["id"]: item["slug"] for item in getAllItems()}


def getNameToSlug():
    return {
        item["i18n"]["en"]["name"]: item["slug"]
        for item in getAllItems()
        if item.get("i18n", {}).get("en")
    }


def getItemDetails(slug):
    """Item complet (contient maxRank pour les mods/arcanes)."""
    r = warframeApi.get(f"{WFM_API}/item/{slug}")
    if r.status_code != 200:
        return None
    return r.json()["data"]


# --- Auth -----------------------------------------------------------------------


def checkAuth():
    """Vérifie le token sans rien poster. Retourne (ok, ingameName|None)."""
    r = warframeApi.get(f"{WFM_API}/me")
    if r.status_code != 200:
        return False, None
    me = r.json()["data"]
    return True, me.get("ingameName")


def login(user_email: str, user_password: str, platform: str = "pc", language: str = "en"):
    """
    Connexion via l'API v1 (le signin v2 est first-party only).
    Retourne (ingame_name, jwt_token) ou (None, None).
    """
    headers = {
        "Content-Type": "application/json; utf-8",
        "Accept": "application/json",
        "Authorization": "JWT",
        "platform": platform,
        "language": language,
        "User-Agent": USER_AGENT,
    }
    content = {"email": user_email, "password": user_password, "auth_type": "header"}
    response = requests.post(
        f"{WFM_AUTH_API}/auth/signin",
        data=json.dumps(content),
        headers=headers,
        timeout=REQUEST_TIMEOUT,
    )
    customLogger.writeTo(
        "wfmAPICalls.log", f"POST:{WFM_AUTH_API}/auth/signin\tResponse:{response.status_code}"
    )
    if response.status_code != 200:
        return None, None
    return (
        response.json()["payload"]["user"]["ingame_name"],
        response.headers["Authorization"],
    )


# --- Ordres ----------------------------------------------------------------------


def _compactOrderToLegacy(order, idToSlug):
    """Traduit un Order v2 vers la forme attendue par LiveScraper/inventoryApi."""
    return {
        "id": order["id"],
        "platinum": order["platinum"],
        "quantity": order["quantity"],
        "visible": order["visible"],
        "mod_rank": order.get("rank"),
        "item": {
            "url_name": idToSlug.get(order["itemId"], order["itemId"]),
            "id": order["itemId"],
        },
    }


def getOrders():
    """Mes ordres, groupés {'buy_orders': [...], 'sell_orders': [...]}."""
    r = warframeApi.get(f"{WFM_API}/orders/my")
    if r.status_code != 200:
        raise RuntimeError(f"GET /v2/orders/my -> {r.status_code} : {r.text[:200]}")
    idToSlug = getIdToSlug()
    grouped = {"buy_orders": [], "sell_orders": []}
    for order in r.json()["data"]:
        grouped[f"{order['type']}_orders"].append(_compactOrderToLegacy(order, idToSlug))
    return grouped


def getPublicOrders(slug):
    """Ordres visibles sur un item (liste brute v2, avec user)."""
    r = warframeApi.get(f"{WFM_API}/orders/item/{slug}")
    if r.status_code != 200:
        return []
    return r.json()["data"]


def postOrder(item, order_type, platinum, quantity, visible, modRank, itemName):
    json_data = {
        "itemId": str(item),
        "type": str(order_type),
        "platinum": int(platinum),
        "quantity": int(quantity),
        "visible": _toBool(visible),
    }
    rank = _toRank(modRank)
    if rank is not None:
        json_data["rank"] = rank

    if isDryRun():
        customLogger.writeTo(
            "orderTracker.log",
            f"[DRY-RUN] POST\tItem:{itemName}\tOrder Type:{order_type}\tPlatinum:{platinum}\tQuantity:{quantity}\tVisible:{json_data['visible']}",
        )
        logging.debug(f"[DRY-RUN] postOrder {itemName} {json_data}")
        fakeOrder = {
            "id": f"dryrun-{itemName}-{order_type}",
            "type": str(order_type),
            "platinum": int(platinum),
            "quantity": int(quantity),
            "visible": json_data["visible"],
            "itemId": str(item),
        }
        if rank is not None:
            fakeOrder["rank"] = rank
        return FakeResponse({"apiVersion": "dry-run", "data": fakeOrder, "error": None})

    response = warframeApi.post(f"{WFM_API}/order", json=json_data)
    if response.status_code == 200:
        customLogger.writeTo(
            "orderTracker.log",
            f"POSTED\tItem:{itemName}\tOrder Type:{order_type}\tPlatinum:{platinum}\tQuantity:{quantity}\tVisible:{json_data['visible']}",
        )
    return response


def updateListing(listing_id, platinum, quantity, visibility, itemName, order_type):
    contents = {
        "platinum": int(platinum),
        "quantity": int(quantity),
        "visible": _toBool(visibility),
    }

    if isDryRun():
        customLogger.writeTo(
            "orderTracker.log",
            f"[DRY-RUN] UPDATE\tItem:{itemName}\tOrder Type:{order_type}\tPlatinum:{platinum}\tVisible:{contents['visible']}",
        )
        logging.debug(f"[DRY-RUN] updateListing {itemName} {contents}")
        return True

    try:
        response = warframeApi.patch(f"{WFM_API}/order/{listing_id}", json=contents)
        response.raise_for_status()
        customLogger.writeTo(
            "orderTracker.log",
            f"UPDATED\tItem:{itemName}\tOrder Type:{order_type}\tPlatinum:{platinum}\tVisible:{contents['visible']}",
        )
        return True
    except requests.exceptions.RequestException as e:
        logging.debug(f"update_listing: {e}")
        return False


def deleteOrder(orderID):
    if isDryRun():
        customLogger.writeTo("orderTracker.log", f"[DRY-RUN] DELETE\tOrder ID: {orderID}")
        logging.debug(f"[DRY-RUN] deleteOrder {orderID}")
        return FakeResponse({"apiVersion": "dry-run", "data": {"id": orderID}, "error": None})

    r = warframeApi.delete(f"{WFM_API}/order/{orderID}")
    if r.status_code == 200:
        customLogger.writeTo("orderTracker.log", f"DELETED\tOrder ID: {orderID}")
    return r


def closeOrder(orderID, quantity=1):
    """Clôture (totale ou partielle) d'un ordre -> transaction wfm."""
    if isDryRun():
        customLogger.writeTo(
            "orderTracker.log", f"[DRY-RUN] CLOSE\tOrder ID: {orderID}\tQuantity:{quantity}"
        )
        logging.debug(f"[DRY-RUN] closeOrder {orderID}")
        return FakeResponse({"apiVersion": "dry-run", "data": {"id": orderID}, "error": None})

    r = warframeApi.post(f"{WFM_API}/order/{orderID}/close", json={"quantity": int(quantity)})
    if r.status_code == 200:
        customLogger.writeTo(
            "orderTracker.log", f"CLOSED\tOrder ID: {orderID}\tQuantity:{quantity}"
        )
    return r
