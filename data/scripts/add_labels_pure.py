import csv

def load_mapping(filepath, key_col, val_col):
    mapping = {}
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter='\t')
            for row in reader:
                if key_col in row and val_col in row:
                    mapping[row[key_col]] = row[val_col]
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
    return mapping

country_map = load_mapping('CAMEO.country.txt', 'CODE', 'LABEL')
type_map = load_mapping('CAMEO.type.txt', 'CODE', 'LABEL')
event_map = load_mapping('CAMEO.eventcodes.txt', 'CAMEOEVENTCODE', 'EVENTDESCRIPTION')
quad_map = {
    '1': 'Verbal Cooperation',
    '2': 'Material Cooperation',
    '3': 'Verbal Conflict',
    '4': 'Material Conflict'
}

with open('copy_events_benin_2025.csv', 'r', encoding='utf-8') as fin, \
     open('copy_events_benin_2025_labeled.csv', 'w', encoding='utf-8', newline='') as fout:
    
    reader = csv.reader(fin)
    writer = csv.writer(fout)
    
    headers = next(reader)
    
    # Determine the inserts
    insertions = []
    def add_insertion(col_name, new_col_name, mapping):
        if col_name in headers:
            idx = headers.index(col_name)
            insertions.append((idx, new_col_name, mapping))
            
    add_insertion('Actor1CountryCode', 'Actor1CountryLabel', country_map)
    add_insertion('Actor1Type1Code', 'Actor1Type1Label', type_map)
    add_insertion('Actor2CountryCode', 'Actor2CountryLabel', country_map)
    add_insertion('Actor2Type1Code', 'Actor2Type1Label', type_map)
    add_insertion('EventCode', 'EventLabel', event_map)
    add_insertion('EventBaseCode', 'EventBaseLabel', event_map)
    add_insertion('EventRootCode', 'EventRootLabel', event_map)
    add_insertion('QuadClass', 'QuadClassLabel', quad_map)
    
    # Sort insertions backwards to not mess up indexes when inserting
    insertions.sort(key=lambda x: x[0], reverse=True)
    
    new_headers = headers[:]
    for idx, new_col_name, _ in insertions:
        new_headers.insert(idx + 1, new_col_name)
        
    writer.writerow(new_headers)
    
    for row in reader:
        new_row = row[:]
        for idx, new_col_name, mapping in insertions:
            val = new_row[idx]
            label = mapping.get(val, '')
            if new_col_name == 'EventRootLabel' and val and len(val) == 1:
                label = mapping.get('0' + val, '')
            new_row.insert(idx + 1, label)
        writer.writerow(new_row)

print("File successfully processed and saved as copy_events_benin_2025_labeled.csv")
