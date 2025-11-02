import requests
import csv
import time
from datetime import datetime

api_key = "" # TODO : Use an environment variable here
puuid = "GfKGRvbQiyqPeH38NxkviMX5AH4nFgUc_q1o9naHzi0VQKBtDBJk6QcE3XHkKku64-tZVaJz7KKpuA"
region = "asia"

# ---------------------------
# 1️⃣ Récupération des IDs de matchs (avec pagination)
# ---------------------------
def get_match_ids(puuid, region, count=100):
    all_match_ids = []
    offset = 0

    print("🔍 Récupération de tous les match IDs...")

    while True:
        url = f"https://{region}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids"
        params = {
            "start": offset,
            "count": count,
            "api_key": api_key
        }

        response = requests.get(url, params=params)
        if response.status_code == 429:
            print("⏳ Rate limit atteint, pause 10 secondes...")
            time.sleep(10)
            continue

        if response.status_code != 200:
            print(f"⚠️ Erreur HTTP {response.status_code} à l’offset {offset}")
            break

        batch = response.json()
        if not batch:
            print("✅ Fin : plus de matchs à récupérer.")
            break

        all_match_ids.extend(batch)
        offset += count

        print(f"→ {len(batch)} nouveaux matchs récupérés (total = {len(all_match_ids)})")

        time.sleep(1.2)  # éviter le rate limit

    return all_match_ids


# ---------------------------
# 2️⃣ Récupération d’un match complet
# ---------------------------
def get_match_data(match_id, region):
    url = f"https://{region}.api.riotgames.com/lol/match/v5/matches/{match_id}"
    params = {"api_key": api_key}

    for attempt in range(3):
        try:
            response = requests.get(url, params=params)
            if response.status_code == 429:
                print("Rate limit atteint, pause 5s...")
                time.sleep(5)
                continue
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Erreur sur {match_id}: {e}")
            time.sleep(2)
    return None


# ---------------------------
# 3️⃣ Extraction des données du joueur
# ---------------------------
def extract_player_data(match, puuid):
    info = match.get("info", {})
    metadata = match.get("metadata", {})

    for p in info.get("participants", []):
        if p["puuid"] == puuid:
            ts = info.get("gameStartTimestamp")
            date = datetime.utcfromtimestamp(ts / 1000).strftime('%Y-%m-%d %H:%M:%S') if ts else ""

            return {
                "match_id": metadata.get("matchId"),
                "date": date,
                "game_mode": info.get("gameMode"),
                "queue_id": info.get("queueId"),
                "duration_sec": info.get("gameDuration"),
                "champion": p.get("championName"),
                "team_position": p.get("teamPosition"),
                "win": p.get("win"),
                "kills": p.get("kills"),
                "deaths": p.get("deaths"),
                "assists": p.get("assists"),
                "kda": round((p.get("kills") + p.get("assists")) / max(1, p.get("deaths")), 2),
                "level": p.get("champLevel"),
                "gold": p.get("goldEarned"),
                "damage": p.get("totalDamageDealtToChampions"),
                "damage_taken": p.get("totalDamageTaken"),
                "healing": p.get("totalHeal"),
                "vision_score": p.get("visionScore"),
                "cs": p.get("totalMinionsKilled") + p.get("neutralMinionsKilled"),
                "summoner1Id": p.get("summoner1Id"),
                "summoner2Id": p.get("summoner2Id"),
                "items": [p.get(f"item{i}") for i in range(7)],
                "perk_primary_style": p.get("perks", {}).get("styles", [{}])[0].get("style"),
                "perk_secondary_style": p.get("perks", {}).get("styles", [{}])[1].get("style") if len(p.get("perks", {}).get("styles", [])) > 1 else None,
            }
    return None


# ---------------------------
# 4️⃣ Écriture CSV
# ---------------------------
def write_csv(data, filename="faker_all_matches.csv"):
    if not data:
        print("⚠️ Aucune donnée à écrire.")
        return

    keys = list(data[0].keys())
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(data)
    print(f"✅ Fichier CSV créé : {filename} ({len(data)} matchs)")


# ---------------------------
# 5️⃣ MAIN
# ---------------------------
if __name__ == "__main__":
    all_data = []

    # Récupération de tous les match IDs avec pagination
    match_ids = get_match_ids(puuid, region, count=100)

    # Récupération détaillée de chaque match
    for i, match_id in enumerate(match_ids, 1):
        print(f"({i}/{len(match_ids)}) → Match {match_id}")
        match = get_match_data(match_id, region)
        if not match:
            print("⚠️ Échec récupération, on passe au suivant.")
            continue

        player_data = extract_player_data(match, puuid)
        if player_data:
            all_data.append(player_data)

        time.sleep(1.2)

    # Export CSV
    write_csv(all_data)
