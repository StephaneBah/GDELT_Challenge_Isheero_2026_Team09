import csv

file_path = 'copy_events_benin_2025_labeled.csv'

total_events = 0
total_tone = 0.0
total_goldstein = 0.0

country_mentions = {}
biz_events_count = 0
biz_total_tone = 0.0

monthly_stats = {}

with open(file_path, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        total_events += 1
        
        try:
            tone = float(row.get('AvgTone', 0))
            goldstein = float(row.get('GoldsteinScale', 0))
        except ValueError:
            tone = 0.0
            goldstein = 0.0
            
        total_tone += tone
        total_goldstein += goldstein
        
        month = row.get('MonthYear', 'Unknown')
        if month not in monthly_stats:
            monthly_stats[month] = {'count': 0, 'tone': 0.0}
        monthly_stats[month]['count'] += 1
        monthly_stats[month]['tone'] += tone

        # Diplomacy (Other countries)
        a1 = row.get('Actor1CountryLabel', '').strip()
        if a1 and a1 != 'Benin':
            if a1 not in country_mentions:
                country_mentions[a1] = {'count': 0, 'tone': 0.0}
            country_mentions[a1]['count'] += 1
            country_mentions[a1]['tone'] += tone
            
        # Business / Investments (BUS, DEV, MNC, IGO)
        t1 = row.get('Actor1Type1Code', '')
        t2 = row.get('Actor2Type1Code', '')
        biz_labels = ['BUS', 'DEV', 'MNC']
        if t1 in biz_labels or t2 in biz_labels:
            biz_events_count += 1
            biz_total_tone += tone

print(f"--- INSIGHTS BÉNIN ---")
print(f"Total des évènements: {total_events}")
print(f"Tonalité Globale Moyenne: {total_tone/total_events:.2f} (Échelle de l'article)")
print(f"Score Goldstein Moyen: {total_goldstein/total_events:.2f} (Échelle de stabilité)")

print("\n--- TOP 5 PAYS S'INTERRESSANT AU BÉNIN ---")
top_countries = sorted(country_mentions.items(), key=lambda x: x[1]['count'], reverse=True)[:5]
for c, stats in top_countries:
    print(f"- {c}: {stats['count']} mentions (Tonalité moyenne: {stats['tone']/stats['count']:.2f})")

print("\n--- ANALYSE BUSINESS ET DÉVELOPPEMENT ---")
if biz_events_count > 0:
    print(f"Nombre d'évènements liés au Business/Investissements: {biz_events_count}")
    print(f"Tonalité moyenne des évènements Business: {biz_total_tone/biz_events_count:.2f}")

print("\n--- TENDANCE TEMPORELLE (TONALITÉ) ---")
for m in sorted(monthly_stats.keys()):
    if monthly_stats[m]['count'] > 0:
        print(f"- {m} : {monthly_stats[m]['count']} évènements, Tonalité moy: {monthly_stats[m]['tone']/monthly_stats[m]['count']:.2f}")
